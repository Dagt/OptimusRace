from datetime import date,timedelta
from tempfile import TemporaryDirectory
from importlib import import_module
from django.apps import apps
from django.contrib.auth.models import User,Group
from django.test import TestCase,override_settings
from django.utils import timezone
from .models import Participant,Registration,Event,Profile,AccountName,Result
from .event_policy import blank_rules
from .test_portraits import picture
from .services import register_person_cash,capture,change_phase


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CashParticipantTests(TestCase):
    def setUp(self):
        from unittest.mock import patch
        from .test_portraits import picture
        processor=patch('race.portrait.sports_photo',side_effect=lambda upload:picture(size=(600,750)).read());processor.start();self.addCleanup(processor.stop)
        self.media=TemporaryDirectory();self.addCleanup(self.media.cleanup)
        self.settings_override=override_settings(MEDIA_ROOT=self.media.name);self.settings_override.enable();self.addCleanup(self.settings_override.disable)
        self.admin=User.objects.create_superuser('admin','admin@example.test','test-password')
        self.client.force_login(self.admin)
        rules=blank_rules();rules.update(minimum_age=16,categories=[{'name':'60–70','sex':'M','min':60,'max':70},{'name':'70–80','sex':'M','min':70,'max':80}],tests=[{'name':'Salto','unit':'cm','capacity':'Potencia','higher':True,'scoring':'relative','max_points':100,'base':None,'elite':None,'parameters':{'metric':'distance','load_mode':'none'}}])
        self.event=Event.objects.create(name='Evento caja',location='Local',date=timezone.now()+timedelta(days=10),registration_end=timezone.now()+timedelta(days=9),rules=rules,status='open',price=45000,capacity=2)
        self.url=f'/events/{self.event.pk}/register/'
    def data(self,**changes):
        token=self.client.get(self.url).context['request_token']
        return dict(name='Ana',paternal='López',maternal='Pérez',sex='M',birth_date='1990-01-01',email='private@example.test',photo=picture(),weight='70',amount='450',batch=1,request_token=token,**changes)
    def test_register_photo_weight_cash_without_account_and_repeat_safe(self):
        data=self.data();count=User.objects.count()
        response=self.client.post(self.url,data);self.assertEqual(response.status_code,302)
        entry=Registration.objects.get();person=entry.participant
        self.assertIsNone(entry.user_id);self.assertEqual(User.objects.count(),count)
        self.assertEqual((entry.weight,entry.category,entry.state,entry.method,entry.attendance),(70,'60–70','confirmed','cash','present'))
        self.assertTrue(person.photo);self.assertTrue(person.original_photo)
        self.assertEqual(entry.paid_by,self.admin)
        self.assertEqual(self.client.post(self.url,{'request_token':data['request_token']}).status_code,302)
        self.assertEqual(Registration.objects.count(),1);self.assertEqual(Participant.objects.count(),1)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/operations/'),'Participantes inscritos')
    def test_invalid_registration_rolls_back_person_and_files(self):
        from pathlib import Path
        for change in [{'weight':'90'},{'birth_date':'2020-01-01'},{'photo':''}]:
            data=self.data();data.update(change)
            response=self.client.post(self.url,data)
            self.assertEqual(response.status_code,200);self.assertTrue(response.context['form'].errors)
            self.assertEqual(Participant.objects.count(),0);self.assertEqual(Registration.objects.count(),0)
            self.assertEqual(list(Path(self.media.name).rglob('*.jpg')),[])
    def test_capacity_closed_dates_and_discount_limit(self):
        self.event.capacity=1;self.event.rules['discounts']=[{'code':'SAVE','kind':'percent','value':20,'limit':1}];self.event.save()
        data=self.data();data.update(discount_code='SAVE',amount='360')
        self.assertEqual(self.client.post(self.url,data).status_code,302)
        response=self.client.post(self.url,self.data());self.assertContains(response,'Cupo agotado')
        self.event.capacity=3;self.event.save()
        data=self.data();data.update(discount_code='SAVE',amount='360')
        self.assertContains(self.client.post(self.url,data),'agotó sus usos')
        self.event.registration_end=timezone.now()-timedelta(seconds=1);self.event.save()
        self.assertContains(self.client.post(self.url,self.data()),'inscripciones están cerradas')
        self.assertEqual(Participant.objects.count(),1)
    def test_price_and_group_are_calculated_despite_tampered_inputs(self):
        self.event.capacity=5
        self.event.rules.update(group_size=2,price_tiers=[{'name':'Preventa','start':(timezone.now()-timedelta(days=1)).isoformat(),'end':(timezone.now()+timedelta(days=1)).isoformat(),'amount':40000}],discounts=[{'code':'SAVE','kind':'percent','value':20}])
        self.event.save()
        page=self.client.get(self.url)
        self.assertNotContains(page,'name="amount"');self.assertNotContains(page,'name="batch"')
        for index in range(3):
            data=self.data();data.update(name=f'Persona {index}',amount='1',batch='999',discount_code='SAVE')
            self.assertEqual(self.client.post(self.url,data).status_code,302)
        entries=list(Registration.objects.order_by('bib'))
        self.assertEqual([entry.amount for entry in entries],[32000]*3)
        self.assertEqual([entry.batch for entry in entries],[1,1,1])
        self.assertEqual(entries[0].pricing_snapshot['base_amount'],40000)
    def test_reuse_person_public_history_privacy_and_private_drafts(self):
        self.client.post(self.url,self.data());person=Participant.objects.get()
        second=Event.objects.create(name='Segunda edición',location='Local',date=self.event.date,registration_end=self.event.registration_end,rules=self.event.rules,status='open',price=45000)
        register_person_cash(second.pk,person,self.admin,70.001)
        # Duplicate person in one event cannot be charged again.
        data=self.data();data.pop('photo');data['participant']=person.pk
        self.assertContains(self.client.post(self.url,data),'ya tiene una inscripción')
        self.assertEqual(Participant.objects.count(),1)
        self.client.logout()
        for query in ['Ana López',f'P{person.pk}','1']:
            self.assertContains(self.client.get('/results/',{'q':query,'event':second.pk}),person.full_name)
        response=self.client.get(f'/results/participants/{person.pk}/')
        self.assertContains(response,'Segunda edición');self.assertContains(response,'Evento caja')
        for private in ['private@example.test','1990-01-01','originals/']:self.assertNotContains(response,private)
        self.assertEqual(response.context['selected']['entry'].participant,person)
        for e in [self.event,second]:e.status='draft';e.save()
        self.assertEqual(self.client.get(f'/results/participants/{person.pk}/').status_code,404)
        self.assertNotContains(self.client.get('/results/',{'q':'Ana'}),person.full_name)
    def test_new_registration_ready_for_coach(self):
        self.client.post(self.url,self.data());entry=Registration.objects.get()
        change_phase(self.event.pk,self.admin,'live')
        mark=capture(entry.pk,self.admin,0,45,None,'done',0,'')
        self.assertEqual(mark.value,45)
        self.client.logout();self.assertContains(self.client.get(f'/results/participants/{entry.participant_id}/'),'45')
    def test_historical_batch_never_hides_or_blocks_a_participant(self):
        self.client.post(self.url,self.data());entry=Registration.objects.get()
        entry.batch=9;entry.save(update_fields=['batch'])
        change_phase(self.event.pk,self.admin,'live')
        self.assertContains(self.client.get(f'/events/{self.event.pk}/coach/'),entry.name)
        mark=capture(entry.pk,self.admin,0,45,None,'done',0,'')
        self.assertEqual(mark.value,45)
        page=self.client.get(f'/events/{self.event.pk}/operations/')
        self.assertNotContains(page,'Lote');self.assertNotContains(page,'name="batch"')
    def test_reprocess_saved_original_without_changing_participant_data(self):
        self.client.post(self.url,self.data());person=Participant.objects.get()
        previous_photo=person.photo.name;original=person.original_photo.name
        response=self.client.post(f'/participants/{person.pk}/edit/',{'action':'refresh_photo'})
        self.assertEqual(response.status_code,302);person.refresh_from_db()
        self.assertEqual(person.original_photo.name,original)
        self.assertNotEqual(person.photo.name,previous_photo)
        self.assertEqual(person.name,'Ana')
    def test_no_public_account_checkout_or_staff_write(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code,302)
        for url in ['/signup/',f'/events/{self.event.pk}/enroll/']:
            self.assertEqual(self.client.post(url,{}).status_code,410)
        user=User.objects.create_user('old',password='test-password')
        self.client.post('/login/',{'email':'old','password':'test-password'})
        self.assertNotIn('_auth_user_id',self.client.session)
        user.groups.add(Group.objects.get_or_create(name='Coach')[0]);self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code,403)
    def test_migration_preserves_identity_photos_results_and_staff_login(self):
        old=User.objects.create_user('old',first_name='Luis',last_name='Soto Paz',email='old@example.test')
        AccountName.objects.create(user=old,paternal='Soto',maternal='Paz')
        Profile.objects.create(user=old,sex='M',birth_date=date(1990,1,1),photo='athletes/old.jpg')
        entry=Registration.objects.create(user=old,event=self.event,name='Luis Soto Paz',sex='M',bib=7,state='confirmed',weight=70,category='60–70')
        mark=Result.objects.create(registration=entry,test=0,value=45,points=100)
        import_module('race.migrations.0012_migrate_participant_records').migrate_people(apps,None)
        entry.refresh_from_db();old.refresh_from_db();self.admin.refresh_from_db();mark.refresh_from_db()
        self.assertFalse(old.is_active);self.assertTrue(self.admin.is_active)
        self.assertEqual(entry.participant.full_name,'Luis Soto Paz');self.assertEqual(entry.participant.photo.name,'athletes/old.jpg')
        self.assertEqual(mark.registration_id,entry.pk);self.assertEqual(mark.value,45)
