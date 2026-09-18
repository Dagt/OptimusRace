from copy import deepcopy
from datetime import datetime,date,timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth.models import User,Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event,Profile,Exercise,Registration,Result,Payment
from .event_policy import blank_rules,quote_price,current_price,validate_policies,validate_eligibility,registration_open
from .exercise_parameters import validate_parameters,load_for,validate_mark
from .management_forms import CatalogForm
from .services import validate_rules,cash_register,check_in,capture,board,change_phase,discipline,configure,checkout

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ConfigurationTests(TestCase):
    def setUp(self):
        self.scoring_coach=User.objects.create_user('scoring-coach')
        self.scoring_coach.groups.add(Group.objects.get_or_create(name='Coach')[0])
        self.admin=User.objects.create_superuser('owner','owner@example.test','test-password')
        self.user=User.objects.create_user('athlete','athlete@example.test','test-password')
        Profile.objects.create(user=self.user,sex='M',birth_date=date(1990,1,1))
        self.now=timezone.now()
        self.rules=blank_rules()
        self.rules.update(categories=[{'name':'Varonil','sex':'M','min':0,'max':None}],minimum_age=16,judging_standard='Criterio de prueba aislada')
        self.rules['tests']=[{'name':'Estación libre','unit':'reps','capacity':'Resistencia','higher':True,'base':10,'elite':20,'max_points':100,'scoring':'linear','parameters':{'metric':'repetitions','duration_seconds':60,'load_mode':'none'}}]
        self.event=Event.objects.create(name='Evento aislado',location='Local',date=self.now+timedelta(days=10),registration_end=self.now+timedelta(days=9),price=45000,capacity=10,rules=deepcopy(self.rules),status='open')
        self.client.force_login(self.admin)
    def athlete(self,name):
        user=User.objects.create_user(name,email=f'{name}@example.test')
        Profile.objects.create(user=user,sex='M',birth_date=date(1990,1,1));return user
    def test_new_event_starts_blank_without_preset(self):
        response=self.client.get('/events/new/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['rules']['tests'],[])
        self.assertEqual(response.context['rules']['categories'],[])
        self.assertNotContains(response,'APPEX')
        self.assertContains(response,'config-editor.js')
    def test_exercise_parameters_roundtrip_and_invalid_values(self):
        data={'name':'Prueba por tiempo','unit':'reps','capacity':'Resistencia','higher':'True','metric':'repetitions','duration_seconds':60,'load_mode':'body_percent','load_value':75,'round_mode':'nearest','load_step':2.5,'precision':0}
        form=CatalogForm(data);self.assertTrue(form.is_valid(),form.errors)
        exercise=form.save();self.assertEqual(exercise.parameters['duration_seconds'],60)
        self.assertEqual(load_for({'parameters':exercise.parameters},79),60)
        bad=CatalogForm({**data,'load_value':''});self.assertFalse(bad.is_valid())
        with self.assertRaises(ValidationError):validate_mark(2.5,{'unit':'reps','parameters':exercise.parameters})
        with self.assertRaises(ValidationError):validate_parameters({'metric':'time','precision':7})
    def test_arbitrary_station_count_weighted_score_and_snapshot(self):
        validate_rules(self.rules)
        self.event.status='live';self.event.save()
        r=Registration.objects.create(event=self.event,user=self.user,name='Atleta',sex='M',bib=1,state='confirmed',attendance='present',category='Varonil')
        capture(r.pk,self.scoring_coach,0,15,None,'done',0,'')
        row=board(self.event)[0]
        self.assertEqual(row['total'],75);self.assertEqual(row['test_count'],1)
        self.assertEqual(row['capacities']['Resistencia'],75)
        self.assertEqual(row['capacities']['Fuerza'],0)
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        self.assertEqual(board(self.event)[0]['total'],75)
        with self.assertRaises(ValidationError):capture(r.pk,self.scoring_coach,0,20,None,'done',1,'correction')
    def test_eight_station_points_are_summed_not_averaged(self):
        self.rules['tests']=[{**self.rules['tests'][0],'name':f'Estación {i}','max_points':12.5} for i in range(8)]
        self.event.rules=self.rules;self.event.status='live';self.event.save()
        r=Registration.objects.create(event=self.event,user=self.user,name='Atleta',sex='M',bib=1,state='confirmed',attendance='present',category='Varonil')
        for i in range(8):
            self.event.active_test=i;self.event.save()
            capture(r.pk,self.scoring_coach,i,20,None,'done',0,'')
        row=board(self.event)[0];self.assertEqual(row['total'],100)
        self.assertTrue(all(m['points']==12.5 for m in row['marks']))
    def test_judge_score_bounds_and_disqualification(self):
        self.event.rules['tests'][0]['scoring']='judge';self.event.status='live';self.event.save()
        r=Registration.objects.create(event=self.event,user=self.user,name='Atleta',sex='M',bib=1,state='confirmed',attendance='present',category='Varonil')
        with self.assertRaises(ValidationError):capture(r.pk,self.scoring_coach,0,20,None,'done',0,'',judged_points=101)
        capture(r.pk,self.scoring_coach,0,20,None,'done',0,'',judged_points=80)
        discipline(r.pk,self.admin,True,'Motivo registrado',0)
        self.assertIsNone(board(self.event)[0]['rank'])
        self.assertEqual(Result.objects.get(registration=r).points,80)
        with self.assertRaises(ValidationError):capture(r.pk,self.scoring_coach,0,20,None,'done',1,'correction',judged_points=90)
    def test_age_on_event_day_boundaries(self):
        self.event.date=datetime(2026,10,18,9,tzinfo=ZoneInfo('America/Mexico_City'))
        validate_eligibility(self.event,date(2010,10,18))
        with self.assertRaises(ValidationError):validate_eligibility(self.event,date(2010,10,19))
        self.event.rules['maximum_age']=30
        with self.assertRaises(ValidationError):validate_eligibility(self.event,date(1995,10,18))
        with self.assertRaises(ValidationError):validate_eligibility(self.event,None)
    def test_price_boundary_discount_rounding_and_overlap(self):
        boundary=self.now+timedelta(days=1)
        self.event.rules['price_tiers']=[{'name':'Anticipada','amount':40000,'start':(self.now-timedelta(days=1)).isoformat(),'end':boundary.isoformat()}]
        self.event.rules['discounts']=[{'code':'CLIENTE','kind':'percent','value':10,'limit':1}]
        self.assertEqual(current_price(self.event,at=boundary-timedelta(seconds=1)),40000)
        self.assertEqual(current_price(self.event,at=boundary),45000)
        self.assertEqual(quote_price(self.event,'cliente',at=self.now)['amount'],36000)
        validate_policies(self.event.rules,self.event)
        self.event.rules['price_tiers']*=2
        with self.assertRaises(ValidationError):validate_policies(self.event.rules,self.event)
    def test_discount_limits_wrong_amount_and_reserved_quote(self):
        self.event.rules['discounts']=[{'code':'LAST','kind':'fixed','value':5000,'limit':1}];self.event.save()
        with self.assertRaises(ValidationError):cash_register(self.event.pk,self.user,self.admin,45000,'LAST')
        self.assertFalse(Registration.objects.exists())
        r=cash_register(self.event.pk,self.user,self.admin,40000,'last')
        self.assertEqual(r.pricing_snapshot['discount_amount'],5000)
        with self.assertRaises(ValidationError):cash_register(self.event.pk,self.athlete('second'),self.admin,40000,'LAST')
        response=self.client.get(f'/events/{self.event.pk}/quote/',{'email':self.user.email})
        self.assertEqual(response.json()['amount'],45000);self.assertFalse(response.json()['locked'])
    def test_discount_expiry_and_no_negative_price(self):
        self.event.rules['discounts']=[{'code':'FREE','kind':'fixed','value':90000,'end':self.now.isoformat()}]
        self.assertEqual(quote_price(self.event,'FREE',at=self.now-timedelta(seconds=1))['amount'],0)
        with self.assertRaises(ValidationError):quote_price(self.event,'FREE',at=self.now)
    def test_registration_reception_schedule_and_order(self):
        self.event.rules['registration_start']=(self.now+timedelta(days=1)).isoformat();self.event.save()
        self.assertFalse(registration_open(self.event))
        with self.assertRaises(ValidationError):cash_register(self.event.pk,self.user,self.admin,45000)
        self.event.rules.pop('registration_start');self.event.rules['reception_start']=(self.now+timedelta(days=1)).isoformat();self.event.save()
        r=cash_register(self.event.pk,self.user,self.admin,45000)
        check_in(r.pk,self.admin,70,1,'present')  # Retired reception windows no longer block corrections.
        self.event.rules['ordered_stations']=True;self.event.save()
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'live',test=1)
    def test_event_and_catalog_render_with_parameters(self):
        for path in [f'/events/{self.event.pk}/',f'/events/{self.event.pk}/operations/',f'/events/{self.event.pk}/configure/','/catalog/new/']:
            self.assertEqual(self.client.get(path).status_code,200,path)
    def test_blank_draft_can_save_but_cannot_publish(self):
        rules=blank_rules();validate_rules(rules,False)
        with self.assertRaises(ValidationError):validate_rules(rules)
        data={'name':'Desde cero','location':'Sede','date':self.now+timedelta(days=20),'registration_end':self.now+timedelta(days=19),'price':'250','capacity':'','minimum_age':'0','rules':__import__('json').dumps(rules)}
        response=self.client.post('/events/new/',data)
        self.assertEqual(response.status_code,302)
        event=Event.objects.get(name='Desde cero');self.assertEqual(event.rules['tests'],[])
        self.assertEqual(self.client.get(f'/events/{event.pk}/operations/').status_code,200)
        with self.assertRaises(ValidationError):change_phase(event.pk,self.admin,'open')
    @override_settings(STRIPE_SECRET_KEY='sk_test_example',STRIPE_MODE='test')
    def test_checkout_cannot_create_reservations_with_discount(self):
        self.event.rules['online_payments']=True;self.event.save()
        with patch('race.services.stripe.checkout.Session.create') as create:
            with self.assertRaises(ValidationError):checkout(self.event.pk,self.user,'SAVE')
            create.assert_not_called()
        self.assertFalse(Payment.objects.exists())
    def test_published_event_does_not_follow_catalog_edits(self):
        exercise=Exercise.objects.create(name='Estación libre',unit='reps',capacity='Resistencia',parameters={'duration_seconds':60})
        exercise.parameters={'duration_seconds':120};exercise.save()
        self.event.refresh_from_db()
        self.assertEqual(self.event.rules['tests'][0]['parameters']['duration_seconds'],60)
        with self.assertRaises(ValidationError):configure(self.event.pk,self.admin,{'rules':self.rules})

    def test_judge_scale_can_be_entered_and_published_from_event_editor(self):
        import json
        rules=deepcopy(self.rules)
        rules['tests'][0]['scoring']='judge'
        rules.pop('judging_standard',None)
        response=self.client.get('/events/new/')
        self.assertContains(response,'name="judging_standard"')
        scale='Técnica: 0 a 40; ejecución: 0 a 60. Máximo 100.'
        data={'name':'Evento con jueces','location':'Sede','date':self.now+timedelta(days=20),
              'registration_end':self.now+timedelta(days=19),'price':'250','capacity':'10',
              'minimum_age':'16','rules':json.dumps(rules),'judging_standard':scale,'intent':'publish'}
        response=self.client.post('/events/new/',data)
        self.assertEqual(response.status_code,302)
        event=Event.objects.get(name='Evento con jueces')
        self.assertEqual(event.status,'open')
        self.assertEqual(event.rules['judging_standard'],scale)
        self.assertContains(self.client.get(f'/events/{event.pk}/configure/'),scale)

    def test_missing_judge_scale_still_prevents_publication(self):
        rules=deepcopy(self.rules);rules['tests'][0]['scoring']='judge';rules['judging_standard']=' '
        validate_rules(rules,False)
        with self.assertRaisesMessage(ValidationError,'Describe la escala'):
            validate_rules(rules)

    def test_catalog_time_choice_survives_save_and_edit(self):
        data={'name':'Tiempo configurable','capacity':'Velocidad','measurement':'time_minutes','load_mode':'none'}
        form=CatalogForm(data);self.assertTrue(form.is_valid(),form.errors)
        exercise=form.save();self.assertEqual(exercise.unit,'seg')
        self.assertEqual(exercise.parameters['time_entry'],'minutes_seconds_dot')
        self.assertEqual(CatalogForm(instance=exercise).initial['measurement'],'time_minutes')
        form=CatalogForm({**data,'measurement':'time'},instance=exercise);self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.save().parameters['time_entry'],'seconds')
