import json,time,hmac,hashlib
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace
from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User,Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import *
from .services import *
from .test_catalog_fixture import seed_catalog
from .views import default_rules

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RaceTests(TestCase):
    def setUp(self):
        seed_catalog()
        self.admin=User.objects.create_superuser('admin@test.com','admin@test.com','good-password-821')
        self.coach=User.objects.create_user('coach@test.com',password='good-password-821')
        group=Group.objects.create(name='Coach');self.coach.groups.add(group)
        self.user=self.person('one@test.com')
        self.rules=default_rules();self.rules['tests'][1].update(base=20,elite=40)
        self.event=Event.objects.create(name='Test Race',date=timezone.now()+timedelta(days=20),registration_end=timezone.now()+timedelta(days=10),location='Test',rules=self.rules,status='open',price=50000,capacity=2)
    def person(self,email):
        u=User.objects.create_user(email,email,'good-password-821',first_name=email.split('@')[0]);Profile.objects.create(user=u,sex='M');return u
    def entry(self): return cash_register(self.event.id,self.user,self.admin,50000)
    def live(self):
        r=self.entry();check_in(r.id,self.admin,80,1,'present');change_phase(self.event.id,self.admin,'live');return r
    def payload(self,p,kind='checkout.session.completed',**kwargs):
        obj={'id':'cs_test_1','metadata':{'payment_id':str(p.id)},'client_reference_id':str(p.registration_id),'payment_status':'paid','currency':'mxn','amount_total':p.amount,'livemode':False};obj.update(kwargs)
        return {'id':'evt_1','type':kind,'data':{'object':obj}}
    def payment(self):
        with transaction.atomic(): r=reserve_locked(self.event,self.user)
        return Payment.objects.create(registration=r,key='unique',amount=50000,expires_at=timezone.now()+timedelta(minutes=40),session_id='cs_test_1',state='pending')
    def test_linear_clamping_and_time_direction(self):
        t=self.rules['tests'][0]
        self.assertEqual([score(x,t) for x in [0,30,45,60,90]],[0,50,75,100,100])
        t=self.rules['tests'][2]
        self.assertEqual([score(x,t) for x in [400,300,255,210,100]],[0,50,75,100,100])
        for v in [float('nan'),float('inf'),-1]:
            with self.assertRaises(ValidationError): score(v,t)
    def test_missing_press_benchmark_not_dominadas(self):
        rules=default_rules()
        self.assertIsNone(rules['tests'][1]['base'])
        with self.assertRaises(ValidationError):validate_rules(rules)
        validate_rules(rules,False)
    def test_category_boundaries_and_overlap(self):
        rules=deepcopy(self.rules);rules['categories']=[{'name':'M <70','sex':'M','min':0,'max':70},{'name':'M 70+','sex':'M','min':70,'max':None},{'name':'F','sex':'F','min':0,'max':None}]
        validate_rules(rules);self.assertEqual(category(rules,'M',70),'M 70+');self.assertEqual(category(rules,'M',69.99),'M <70')
        rules['categories'][1]['min']=69
        with self.assertRaises(ValidationError):validate_rules(rules)
    def test_wrong_capacity_counts_rejected(self):
        self.rules['tests'][0]['capacity']='Potencia'
        with self.assertRaises(ValidationError):validate_rules(self.rules)
    def test_total_does_not_renormalize_missing(self):
        r=self.live();capture(r.id,self.coach,0,60,60,'done',0,'')
        self.event.refresh_from_db();row=board(self.event)[0]
        self.assertEqual(row['total'],12.5);self.assertEqual(row['completed'],1);self.assertEqual(row['capacities']['Fuerza'],50)
        self.assertIsNone(row['marks'][1]['points']);self.assertEqual(row['rank'],1)
    def test_absent_and_zero_differ(self):
        r=self.live();capture(r.id,self.coach,0,None,None,'absent',0,'')
        self.event.refresh_from_db();self.assertEqual(board(self.event)[0]['completed'],0)
        capture(r.id,self.coach,0,0,60,'done',1,'Corrección de asistencia')
        self.assertEqual(board(self.event)[0]['completed'],1);self.assertEqual(board(self.event)[0]['marks'][0]['points'],0)
    def test_revision_conflict_and_reason(self):
        r=self.live();capture(r.id,self.coach,0,30,60,'done',0,'')
        for rev,reason in [(0,'Error'),(1,'')]:
            with self.assertRaises(ValidationError):capture(r.id,self.coach,0,40,60,'done',rev,reason)
        m=capture(r.id,self.coach,0,40,60,'done',1,'Error de dedo')
        self.assertEqual(m.revision,2);self.assertEqual(Result.objects.count(),1)
        self.assertEqual(Audit.objects.filter(action='correction').get().details['before']['value'],30)
    def test_stale_active_test_and_missing_load(self):
        r=self.live()
        with self.assertRaises(ValidationError):capture(r.id,self.coach,1,20,60,'done',0,'')
        with self.assertRaises(ValidationError):capture(r.id,self.coach,0,20,None,'done',0,'')
    def test_duplicate_cash_no_double_payment(self):
        self.entry()
        with self.assertRaises(ValidationError):self.entry()
        self.assertEqual(Registration.objects.count(),1);self.assertEqual(Audit.objects.filter(action='cash').count(),1)
    def test_capacity_includes_reservations(self):
        self.event.capacity=1;self.event.save();self.payment()
        with self.assertRaises(ValidationError):cash_register(self.event.id,self.person('two@test.com'),self.admin,50000)
    def test_pending_stripe_cannot_be_paid_cash(self):
        self.payment()
        with self.assertRaises(ValidationError):self.entry()
    def test_cash_amount_must_match(self):
        with self.assertRaises(ValidationError):cash_register(self.event.id,self.user,self.admin,40000)
        self.assertEqual(Registration.objects.count(),0)
    def test_webhook_idempotency_and_no_downgrade(self):
        p=self.payment();payload=self.payload(p);fulfill(payload);fulfill(payload)
        self.assertEqual(Webhook.objects.count(),1)
        p.refresh_from_db();self.assertEqual(p.state,'paid')
        expired=self.payload(p,'checkout.session.expired');expired['id']='evt_2';fulfill(expired)
        p.refresh_from_db();self.assertEqual(p.state,'paid');self.assertEqual(p.registration.state,'confirmed')
    def test_wrong_amount_currency_or_identity_rejected(self):
        p=self.payment()
        for bad in [{'amount_total':1},{'currency':'usd'},{'client_reference_id':'999'},{'id':'cs_wrong'},{'livemode':True}]:
            with self.assertRaises(ValidationError):fulfill(self.payload(p,**bad))
        p.refresh_from_db();self.assertEqual(p.state,'pending');self.assertEqual(Webhook.objects.count(),0)
    def test_unpaid_checkout_does_not_confirm(self):
        p=self.payment();fulfill(self.payload(p,payment_status='unpaid'))
        p.refresh_from_db();self.assertEqual(p.registration.state,'reserved')
    def test_verified_expiration_releases_capacity(self):
        p=self.payment();fulfill(self.payload(p,'checkout.session.expired',payment_status='unpaid'))
        p.refresh_from_db();self.assertEqual(p.registration.state,'expired')
    def test_old_expiration_does_not_cancel_new_reservation(self):
        p=self.payment();fulfill(self.payload(p,'checkout.session.expired',payment_status='unpaid'))
        with transaction.atomic(): r=reserve_locked(self.event,self.user)
        fresh=Payment.objects.create(registration=r,key='fresh',amount=50000,expires_at=timezone.now()+timedelta(minutes=40),state='pending')
        late=self.payload(p,'checkout.session.expired',payment_status='unpaid');late['id']='evt_late';fulfill(late)
        r.refresh_from_db();self.assertEqual(r.state,'reserved');fresh.refresh_from_db();self.assertEqual(fresh.state,'pending')
    @override_settings(STRIPE_SECRET_KEY='')
    def test_no_credentials_never_fake_payment(self):
        with self.assertRaises(ValidationError):checkout(self.event.id,self.user)
        self.assertEqual(Registration.objects.count(),0)
    @override_settings(STRIPE_SECRET_KEY='sk_test_fake')
    @patch('race.services.stripe.checkout.Session.create')
    def test_checkout_retry_reuses_idempotency_and_capacity(self,create):
        create.side_effect=[stripe.APIConnectionError('timeout'),SimpleNamespace(id='cs_test_1',url='https://checkout.stripe.com/test')]
        with self.assertRaises(stripe.APIConnectionError):checkout(self.event.id,self.user)
        url=checkout(self.event.id,self.user)
        self.assertEqual(url,'https://checkout.stripe.com/test');self.assertEqual(Payment.objects.count(),1);self.assertEqual(Registration.objects.count(),1)
        self.assertEqual(create.call_args_list[0].kwargs,create.call_args_list[1].kwargs)
        self.assertEqual(checkout(self.event.id,self.user),url);self.assertEqual(create.call_count,2)
    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_testing')
    def test_real_signature_verification(self):
        p=self.payment();raw=json.dumps(self.payload(p)).encode();stamp=str(int(time.time()));sig=hmac.new(b'whsec_testing',stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        self.assertEqual(self.client.post('/stripe/webhook/',data=raw,content_type='application/json',HTTP_STRIPE_SIGNATURE='invalid').status_code,400)
        self.assertEqual(self.client.post('/stripe/webhook/',data=raw,content_type='application/json',HTTP_STRIPE_SIGNATURE=f't={stamp},v1={sig}').status_code,200)
        self.assertEqual(Registration.objects.get().state,'confirmed')
    def test_historical_freeze_and_rules_lock(self):
        r=self.live();capture(r.id,self.coach,0,60,60,'done',0,'');change_phase(self.event.id,self.admin,'closed');self.event.refresh_from_db();before=deepcopy(board(self.event))
        with self.assertRaises(ValidationError):capture(r.id,self.coach,0,30,60,'done',1,'Error')
        with self.assertRaises(ValidationError):configure(self.event.id,self.admin,{})
        Exercise.objects.filter(name='Sentadilla').update(base=999)
        self.assertEqual(board(Event.objects.get(pk=self.event.id)),before)
    def test_weight_locked_after_capture(self):
        r=self.live();capture(r.id,self.coach,0,30,60,'done',0,'')
        with self.assertRaises(ValidationError):check_in(r.id,self.admin,90,1,'present')
    def test_authorization_and_csrf(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/events/{self.event.id}/operations/').status_code,403)
        self.assertEqual(self.client.get(f'/events/{self.event.id}/coach/').status_code,403)
        self.client.force_login(self.coach)
        self.assertEqual(self.client.get(f'/events/{self.event.id}/coach/').status_code,200)
        self.assertEqual(self.client.get(f'/events/{self.event.id}/operations/').status_code,403)
        c=Client(enforce_csrf_checks=True);c.force_login(self.admin)
        self.assertEqual(c.post(f'/events/{self.event.id}/operations/',{'action':'phase','phase':'live'}).status_code,403)
    def test_views_render_all_roles(self):
        self.live()
        self.client.force_login(self.admin)
        for path in ['/',f'/events/{self.event.id}/',f'/events/{self.event.id}/operations/',f'/events/{self.event.id}/coach/',f'/events/{self.event.id}/configure/',f'/events/{self.event.id}/tv/','/events/new/','/profile/','/login/','/signup/','/reset/']:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
        self.client.force_login(self.user);self.assertEqual(self.client.get('/profile/').status_code,200)
    def test_recurrent_account_and_history(self):
        self.entry();clone=Event.objects.create(name='Next',date=self.event.date,registration_end=self.event.registration_end,location='Test',rules=deepcopy(self.rules),status='open')
        cash_register(clone.id,self.user,self.admin,50000)
        self.assertEqual(self.user.registration_set.count(),2);self.assertEqual(Profile.objects.filter(user=self.user).count(),1)
    def test_registration_closed_by_date(self):
        self.event.registration_end=timezone.now()-timedelta(seconds=1);self.event.save()
        with self.assertRaises(ValidationError):self.entry()
    def test_capture_mobile_endpoint(self):
        r=self.live();self.client.force_login(self.coach)
        response=self.client.post(f'/events/{self.event.id}/coach/',{'registration':r.id,'test':0,'value':45,'load':60,'status':'done','revision':0})
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['points'],75)
    def test_load_rounding_is_explicit(self):
        self.assertEqual(suggested_load(self.event,79),59.25)
        self.event.rules.update(bar=20,rounding=2.5,round_mode='nearest')
        self.assertEqual(suggested_load(self.event,79),60)
    def test_login_throttled(self):
        for _ in range(11):response=self.client.post('/login/',{'email':'one@test.com','password':'bad'})
        self.assertContains(response,'Demasiados intentos')

    def test_onsite_live_opt_in_and_capacity(self):
        self.live(); other=self.person('two@test.com')
        with self.assertRaises(ValidationError):cash_register(self.event.id,other,self.admin,50000)
        Event.objects.filter(pk=self.event.pk).update(allow_onsite=True)
        self.assertEqual(cash_register(self.event.id,other,self.admin,50000).state,'confirmed')
        with self.assertRaises(ValidationError):cash_register(self.event.id,self.person('three@test.com'),self.admin,50000)
        self.event.refresh_from_db()
        with self.assertRaises(ValidationError):reserve_locked(self.event,self.person('four@test.com'))

    def test_weight_correction_preserves_load_and_detects_stale_reception(self):
        r=self.live();capture(r.id,self.coach,0,45,60,'done',0,'')
        r.refresh_from_db();version=r.revision
        with self.assertRaises(ValidationError):check_in(r.id,self.coach,95,1,'present','correction',version)
        check_in(r.id,self.admin,95,1,'present','Báscula verificada',version)
        r.refresh_from_db();self.assertEqual(r.weight,95);self.assertEqual(r.result_set.get().load,60)
        self.assertEqual(r.category,category(self.rules,'M',95))
        self.assertTrue(Audit.objects.filter(action='weight_correction').exists())
        with self.assertRaises(ValidationError):check_in(r.id,self.admin,95,2,'present','',version)
        change_phase(self.event.id,self.admin,'closed')
        with self.assertRaises(ValidationError):check_in(r.id,self.admin,90,1,'present','Báscula',r.revision)

    def test_admin_corrects_prior_test_with_reason_and_revision_only(self):
        r=self.live();capture(r.id,self.coach,0,45,60,'done',0,'')
        change_phase(self.event.id,self.admin,'live',2,2)
        with self.assertRaises(ValidationError):capture(r.id,self.coach,0,46,60,'done',1,'Error',True)
        with self.assertRaises(ValidationError):capture(r.id,self.admin,0,46,60,'done',1,'',True)
        mark=capture(r.id,self.admin,0,46,60,'done',1,'Error de digitación',True)
        self.assertEqual(mark.value,46);self.assertEqual(mark.revision,2)
        with self.assertRaises(ValidationError):capture(r.id,self.admin,0,47,60,'done',1,'Error',True)
        with self.assertRaises(ValidationError):capture(r.id,self.admin,1,24,60,'done',0,'Nueva',True)

    @override_settings(STRIPE_MODE='live',STRIPE_SECRET_KEY='sk_live_fake',ALLOW_LIVE_PAYMENTS=True,DEBUG=False,PUBLIC_URL='https://example.test',STRIPE_WEBHOOK_SECRET='whsec_fake')
    def test_live_mode_requires_all_guards_and_excludes_demo(self):
        self.assertTrue(payment_mode())
        for config in [{'ALLOW_LIVE_PAYMENTS':False},{'DEBUG':True},{'PUBLIC_URL':'http://example.test'},{'STRIPE_WEBHOOK_SECRET':''},{'STRIPE_SECRET_KEY':'sk_test_fake'}]:
            with self.subTest(config=config),override_settings(**config),self.assertRaises(ValidationError):payment_mode()
        self.event.demo=True;self.event.save()
        with self.assertRaises(ValidationError):checkout(self.event.id,self.user)
        self.assertFalse(Payment.objects.exists())

    def test_webhook_live_identity_and_duplicate(self):
        p=self.payment();p.livemode=True;p.save()
        with self.assertRaises(ValidationError):fulfill(self.payload(p))
        payload=self.payload(p,livemode=True);fulfill(payload);fulfill(payload)
        p.refresh_from_db();self.assertEqual(p.state,'paid');self.assertEqual(Webhook.objects.count(),1)

    @override_settings(STRIPE_MODE='test',STRIPE_SECRET_KEY='sk_test_fake')
    def test_owner_cancel_waits_for_stripe_and_releases_slot(self):
        import stripe
        p=self.payment()
        with self.assertRaises(ValidationError):cancel_checkout(p.registration_id,self.person('other@test.com'))
        with patch('race.services.stripe.checkout.Session.expire',side_effect=stripe.APIConnectionError('offline')):
            with self.assertRaises(stripe.APIConnectionError):cancel_checkout(p.registration_id,self.user)
        p.refresh_from_db();self.assertEqual(p.state,'pending')
        obj=stripe.StripeObject.construct_from({'id':p.session_id,'status':'expired','metadata':{'payment_id':str(p.id)},'client_reference_id':str(p.registration_id),'livemode':False},None)
        with patch('race.services.stripe.checkout.Session.expire',return_value=obj):cancel_checkout(p.registration_id,self.user)
        p.refresh_from_db();self.assertEqual(p.state,'expired');self.assertEqual(p.registration.state,'expired')

    def test_private_status_and_lookup(self):
        self.entry();self.client.force_login(self.person('other@test.com'))
        self.assertIsNone(self.client.get(f'/events/{self.event.id}/status/').json()['state'])
        self.assertEqual(self.client.get('/participants/lookup/?email=one@test.com').status_code,403)
        self.client.force_login(self.admin)
        self.assertTrue(self.client.get('/participants/lookup/?email=one@test.com').json()['found'])
        self.client.force_login(self.user)
        response=self.client.get(f'/events/{self.event.id}/status/')
        self.assertEqual(response.json()['state'],'confirmed');self.assertEqual(response['Cache-Control'],'no-store')

    def test_safe_login_return_and_decimal_price(self):
        from .forms import EventForm
        response=self.client.post('/login/',{'email':self.user.username,'password':'good-password-821','next':'https://evil.example/path'})
        self.assertEqual(response.url,'/')
        response=self.client.post('/login/',{'email':self.user.username,'password':'good-password-821','next':f'/events/{self.event.id}/'})
        self.assertEqual(response.url,f'/events/{self.event.id}/')
        form=EventForm({'name':'Decimal','location':'Test','date':self.event.date,'registration_end':self.event.registration_end,'price':'500.75','capacity':3})
        self.assertTrue(form.is_valid(),form.errors);self.assertEqual(form.save().price,50075)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recovery_delivers_once_per_request_and_throttles_without_leaking_accounts(self):
        from django.core import mail
        for _ in range(4):self.assertRedirects(self.client.post('/reset/',{'email':self.user.email}),'/reset/sent/')
        self.assertEqual(len(mail.outbox),3)
        self.assertIn('/reset/',mail.outbox[0].body)
        self.assertRedirects(self.client.post('/reset/',{'email':'missing@test.com'}),'/reset/sent/')
        self.assertEqual(len(mail.outbox),3)

    def test_recovery_mail_failure_is_generic(self):
        from smtplib import SMTPException
        with patch('django.contrib.auth.forms.PasswordResetForm.send_mail',side_effect=SMTPException('offline')):
            self.assertRedirects(self.client.post('/reset/',{'email':self.user.email}),'/reset/sent/')

    def test_photo_is_reencoded_and_owned(self):
        import tempfile
        from pathlib import Path
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buffer=BytesIO();Image.new('RGB',(1200,600),'gold').save(buffer,'PNG')
        self.client.force_login(self.user)
        with tempfile.TemporaryDirectory() as tmp,override_settings(MEDIA_ROOT=Path(tmp)):
            response=self.client.post('/profile/',{'sex':'F','photo':SimpleUploadedFile('portrait.png',buffer.getvalue(),content_type='image/png')})
            self.assertEqual(response.status_code,302);self.user.profile.refresh_from_db()
            self.assertTrue(self.user.profile.photo.name.endswith('.jpg'))
            with Image.open(self.user.profile.photo.path) as picture:self.assertEqual(picture.size,(1000,500));self.assertEqual(picture.format,'JPEG')
            self.assertEqual(self.user.profile.sex,'F')

from django.test import SimpleTestCase
class BackupTests(SimpleTestCase):
    def test_roundtrip_media_integrity_and_no_overwrite(self):
        import tempfile,sqlite3
        from contextlib import closing
        from pathlib import Path
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from io import StringIO
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.sqlite3';media=root/'media';media.mkdir();(media/'photo.jpg').write_bytes(b'test-image')
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE evidence (value TEXT)');db.execute("INSERT INTO evidence VALUES ('preserved')");db.commit()
            archive=root/'backup.zip';out=StringIO()
            with override_settings(DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':str(source)}},MEDIA_ROOT=media):
                call_command('backup_data',output=str(archive),stdout=out)
                with self.assertRaises(CommandError):call_command('backup_data',output=str(archive),stdout=out)
            dest=root/'restored';call_command('restore_data',str(archive),destination=str(dest),stdout=out)
            self.assertEqual((dest/'media/photo.jpg').read_bytes(),b'test-image')
            with closing(sqlite3.connect(dest/'db.sqlite3')) as db:self.assertEqual(db.execute('SELECT value FROM evidence').fetchone()[0],'preserved')
            with self.assertRaises(CommandError):call_command('restore_data',str(archive),destination=str(dest),stdout=out)
            self.assertTrue(source.exists())

    def test_restore_rejects_tampering_and_path_escape(self):
        import tempfile,zipfile
        from pathlib import Path
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for index,name in enumerate(['db.sqlite3','media/../../escape','media/C:/escape']):
                archive=root/f'bad{index}.zip';dest=root/f'out{index}'
                files={'db.sqlite3':hashlib.sha256(b'bad').hexdigest(),name:'wrong-hash'}
                with zipfile.ZipFile(archive,'w') as z:
                    z.writestr('manifest.json',json.dumps({'format':1,'files':files}));z.writestr('db.sqlite3',b'bad')
                with self.assertRaises(CommandError):call_command('restore_data',str(archive),destination=str(dest))
                self.assertFalse(dest.exists())

class CleanInstallTests(TestCase):
    def test_bootstrap_is_idempotent_and_has_no_operational_data(self):
        from django.core.management import call_command
        from io import StringIO
        from django.core.management import get_commands
        for _ in range(2):call_command('seed_catalog',stdout=StringIO())
        self.assertEqual(User.objects.count(),0)
        self.assertEqual(Event.objects.count(),0)
        self.assertEqual(Registration.objects.count(),0)
        self.assertEqual(Group.objects.filter(name='Coach').count(),1)
        self.assertEqual(Exercise.objects.count(),0)
        self.assertNotIn('seed_demo',get_commands())
        self.assertContains(self.client.get('/'),'Los eventos estarán aquí cuando se publiquen.')

    def test_empty_account_has_no_synthetic_chart_or_photo(self):
        user=User.objects.create_user('fresh@example.test',password='new-test-only-password',first_name='Nuevo')
        self.client.force_login(user)
        response=self.client.get('/profile/')
        self.assertContains(response,'La primera marca')
        self.assertContains(response,'Sin foto de perfil')
        self.assertNotContains(response,'id="capacity-chart"')
        self.assertNotContains(response,'images/campaign.png')
        user.is_superuser=True;user.is_staff=True;user.save()
        self.assertContains(self.client.get('/'),'Crear evento')
        self.assertEqual(Registration.objects.count(),0)

class EmailLoginTests(TestCase):
    def test_admin_with_distinct_mixed_case_username_can_login_by_email(self):
        user=User.objects.create_superuser('MixedCaseAdmin','owner@example.test','valid-secret-for-test')
        response=self.client.post('/login/',{'email':'OWNER@example.test','password':'valid-secret-for-test'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(int(self.client.session['_auth_user_id']),user.pk)

    def test_ambiguous_email_is_not_used_to_select_account(self):
        User.objects.create_user('first','shared@example.test','valid-secret-for-test')
        User.objects.create_user('second','shared@example.test','another-secret-for-test')
        response=self.client.post('/login/',{'email':'shared@example.test','password':'valid-secret-for-test'})
        self.assertContains(response,'Correo o contraseña incorrectos')
        self.assertNotIn('_auth_user_id',self.client.session)

class PlatformManagementTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('manager','manager@example.test','test-password-valid')
        self.client.force_login(self.admin)
    def test_native_navigation_and_access_control(self):
        for path in ['/team/','team/new/','/catalog/','/catalog/new/']:
            self.assertEqual(self.client.get('/'+path.lstrip('/')).status_code,200)
        response=self.client.get('/')
        self.assertContains(response,'href="/team/"')
        self.assertNotContains(response,'href="/admin/auth/user/"')
        user=User.objects.create_user('athlete',password='test-password-valid')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/team/').status_code,403)
        self.assertEqual(self.client.post('/catalog/new/',{}).status_code,403)
    def test_roles_password_and_self_protection(self):
        data={'name':'Coach New','email':'coach@example.test','role':'coach','sex':'F','active':'on','password':'a-unique-pass-321','password_confirm':'a-unique-pass-321'}
        self.assertEqual(self.client.post('/team/new/',data).status_code,302)
        account=User.objects.get(email=data['email']);self.assertTrue(account.check_password(data['password']))
        self.assertTrue(account.groups.filter(name='Coach').exists());self.assertFalse(account.is_superuser)
        data.update(role='admin',password='',password_confirm='');self.client.post(f'/team/{account.pk}/',data)
        account.refresh_from_db();self.assertTrue(account.is_superuser);self.assertTrue(account.is_staff);self.assertFalse(account.groups.filter(name='Coach').exists())
        data.update(email=self.admin.email,role='athlete')
        self.assertContains(self.client.post(f'/team/{self.admin.pk}/',data),'No puedes desactivar')
        self.admin.refresh_from_db();self.assertTrue(self.admin.is_superuser)
    def test_duplicate_email_and_catalog_direction(self):
        response=self.client.post('/team/new/',{'name':'Duplicate','email':self.admin.email.upper(),'role':'admin','sex':'M','active':'on','password':'a-unique-pass-321','password_confirm':'a-unique-pass-321'})
        self.assertContains(response,'ya pertenece')
        data={'metric':'time','load_mode':'none','round_mode':'none','name':'Carrera corta','unit':'seg','capacity':'Velocidad','higher':'False','base':10,'elite':5}
        self.assertEqual(self.client.post('/catalog/new/',data).status_code,302)
        exercise=Exercise.objects.get(name='Carrera corta')
        data.update(elite=20)
        self.assertContains(self.client.post(f'/catalog/{exercise.pk}/',data),'élite debe ser mejor')
        exercise.refresh_from_db();self.assertEqual(exercise.elite,5)
    def test_renamed_catalog_keeps_eight_default_slots(self):
        seed_catalog()
        Exercise.objects.filter(name='Sentadilla').update(name='Sentadilla nueva')
        rules=default_rules()
        self.assertEqual(len(rules['tests']),8)
        self.assertIn('Sentadilla nueva',[t['name'] for t in rules['tests']])


class AccountFieldTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('owner','owner@example.test','existing-password-329')
        self.client.force_login(self.admin)
        self.data={'name':'New Account','email':'new@example.test','role':'admin',
                   'password':'unique-account-password-429','password_confirm':'unique-account-password-429'}

    def test_staff_accounts_need_no_competition_profile(self):
        for role in ['admin','coach']:
            with self.subTest(role=role):
                data={**self.data,'role':role,'email':f'{role}@example.test'}
                self.assertRedirects(self.client.post('/team/new/',data),'/team/')
                user=User.objects.get(email=data['email'])
                self.assertTrue(user.is_active)
                self.assertFalse(Profile.objects.filter(user=user).exists())
                response=self.client.get(f'/team/{user.pk}/')
                self.assertContains(response,'data-participant-field hidden')
                self.assertContains(response,'name="password_confirm"')

    def test_participant_requires_category_and_staff_promotion_preserves_it(self):
        data={**self.data,'role':'athlete'}
        response=self.client.post('/team/new/',data)
        self.assertIn('sex',response.context['form'].errors)
        self.assertFalse(User.objects.filter(email=data['email']).exists())
        data['sex']='F'
        self.assertRedirects(self.client.post('/team/new/',data),'/team/')
        user=User.objects.get(email=data['email'])
        self.assertEqual(user.profile.sex,'F')
        data.update(role='coach',active='on',password='',password_confirm='')
        data.pop('sex')
        self.assertRedirects(self.client.post(f'/team/{user.pk}/',data),'/team/')
        user.refresh_from_db()
        self.assertEqual(user.profile.sex,'F')
        self.assertTrue(user.check_password(self.data['password']))

    def test_confirmation_is_required_and_must_match_before_creation(self):
        for confirm in ['', 'mistyped-password-429']:
            response=self.client.post('/team/new/',{**self.data,'password_confirm':confirm})
            self.assertIn('password_confirm',response.context['form'].errors)
            self.assertFalse(User.objects.filter(email=self.data['email']).exists())

    def test_password_edit_rejects_mismatch_and_accepts_confirmed_change(self):
        data={**self.data,'email':self.admin.email,'active':'on','password_confirm':'different'}
        response=self.client.post(f'/team/{self.admin.pk}/',data)
        self.assertIn('password_confirm',response.context['form'].errors)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('existing-password-329'))
        data['password_confirm']=data['password']
        self.assertRedirects(self.client.post(f'/team/{self.admin.pk}/',data),'/team/')
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(data['password']))
        self.assertEqual(int(self.client.session['_auth_user_id']),self.admin.pk)

    def test_public_signup_requires_matching_confirmation(self):
        from .forms import SignupForm
        data={**self.data,'sex':'M'}
        for confirm in ['', 'wrong-password']:
            form=SignupForm({**data,'password_confirm':confirm})
            self.assertFalse(form.is_valid())
            self.assertIn('password_confirm',form.errors)
        self.assertTrue(SignupForm(data).is_valid())
