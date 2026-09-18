from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from . import test_cash_participants as fixtures
from .models import Registration, Result
from .services import capture, change_phase


class CaptureFlowTests(TestCase):
    data=fixtures.CashParticipantTests.data

    def setUp(self):
        fixtures.CashParticipantTests.setUp(self)
        self.client.post(self.url,self.data())
        self.entry=Registration.objects.get()
        self.coach=User.objects.create_user('mobile-coach',password='test-password')
        self.coach.groups.add(Group.objects.get_or_create(name='Coach')[0])
        change_phase(self.event.pk,self.admin,'live')
        self.path=f'/events/{self.event.pk}/coach/'
        self.feed=f'/events/{self.event.pk}/live/'
        self.client.force_login(self.coach)

    def payload(self,**changes):
        return {'registration':self.entry.pk,'test':0,'revision':0,'value':'42','status':'done',**changes}

    def test_two_coaches_cannot_overwrite_each_other_and_feed_matches_saved_revision(self):
        first=self.client.post(self.path,self.payload()).json()
        self.assertEqual(first['revision'],1)
        other_coach=User.objects.create_user('second-coach',password='test-password')
        other_coach.groups.add(Group.objects.get(name='Coach'))
        self.client.force_login(other_coach)
        second=self.client.post(self.path,self.payload(value='99'))
        self.assertEqual(second.status_code,400)
        self.assertEqual(Result.objects.get().value,42)
        feed=self.client.get(self.feed)
        self.assertEqual(feed['Cache-Control'],'no-store')
        mark=feed.json()['board'][0]['marks'][0]
        self.assertEqual((mark['value'],mark['revision'],mark['points']),(42,1,first['points']))
        self.assertEqual(self.client.post(self.path,self.payload(revision=1,value='43',reason='Error de dedo')).status_code,200)
        self.assertEqual(self.client.get(self.feed).json()['board'][0]['marks'][0]['revision'],2)

    def test_relative_score_recalculates_for_everyone_after_second_capture(self):
        capture(self.entry.pk,self.coach,0,42,None,'done',0,'')
        self.client.force_login(self.admin)
        self.event.allow_onsite=True;self.event.save(update_fields=['allow_onsite'])
        data=self.data();data['name']='Otro participante'
        self.client.post(self.url,data)
        other=Registration.objects.exclude(pk=self.entry.pk).get()
        capture(other.pk,self.coach,0,60,None,'done',0,'')
        rows=self.client.get(self.feed).json()['board']
        points={r['id']:r['marks'][0]['points'] for r in rows}
        self.assertEqual(points,{self.entry.pk:0,other.pk:100})

    def test_final_results_are_public_but_cannot_be_edited(self):
        self.client.post(self.path,self.payload())
        change_phase(self.event.pk,self.admin,'closed')
        self.assertEqual(self.client.post(self.path,self.payload(revision=1,reason='Intento tardío')).status_code,400)
        self.client.logout()
        feed=self.client.get(self.feed).json()
        self.assertEqual(feed['phase'],'closed')
        self.assertEqual(feed['board'][0]['marks'][0]['value'],42)
        fragment=self.client.get(self.feed,{'view':'standings'})
        self.assertContains(fragment,self.entry.name)
        self.assertNotContains(fragment,'private@example.test')

    def test_only_active_staff_can_capture_even_through_service(self):
        outsider=User.objects.create_user('outsider',password='test-password')
        with self.assertRaises(ValidationError):capture(self.entry.pk,outsider,0,42,None,'done',0,'')
        self.client.force_login(outsider)
        self.assertEqual(self.client.post(self.path,self.payload()).status_code,403)
        self.coach.is_active=False;self.coach.save()
        with self.assertRaises(ValidationError):capture(self.entry.pk,self.coach,0,42,None,'done',0,'')
        self.assertFalse(Result.objects.exists())

    def test_administrator_cannot_capture_or_correct_even_with_coach_group(self):
        capture(self.entry.pk,self.coach,0,42,None,'done',0,'')
        self.admin.groups.add(Group.objects.get(name='Coach'))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.path).status_code,403)
        self.assertEqual(self.client.post(self.path,self.payload(revision=1,reason='Cambio')).status_code,403)
        for administrative in [False,True]:
            with self.assertRaises(ValidationError):
                capture(self.entry.pk,self.admin,0,99,None,'done',1,'Cambio',administrative=administrative)
        path=f'/events/{self.event.pk}/operations/'
        response=self.client.post(path,{'action':'correct',**self.payload(revision=1,value='99',reason='Cambio')})
        self.assertEqual(response.status_code,403)
        response=self.client.get(path)
        self.assertNotContains(response,f'href="{self.path}"')
        self.assertNotContains(response,'event-day-flow')
        self.assertNotContains(response,'name="judged_points"')
        self.assertEqual(Result.objects.get().value,42)

    def test_invalid_numbers_and_wrong_station_do_not_create_marks(self):
        for fields in [{'value':'NaN'},{'value':'Infinity'},{'value':'-1'},{'test':999},{'status':'invented'}]:
            with self.subTest(fields=fields):self.assertEqual(self.client.post(self.path,self.payload(**fields)).status_code,400)
        self.assertFalse(Result.objects.exists())

    def test_missing_status_does_not_retain_measurement_or_points(self):
        self.client.post(self.path,self.payload())
        response=self.client.post(self.path,self.payload(revision=1,status='absent',reason='No realizó la prueba'))
        self.assertEqual(response.status_code,200)
        mark=self.client.get(self.feed).json()['board'][0]['marks'][0]
        self.assertEqual((mark['status'],mark['value'],mark['points']),('absent',None,None))

    def test_operations_guides_start_capture_progress_and_close(self):
        self.client.force_login(self.admin)
        self.event.status='open';self.event.save(update_fields=['status'])
        path=f'/events/{self.event.pk}/operations/'
        response=self.client.get(path)
        self.assertContains(response,'Estación para comenzar')
        self.assertNotContains(response,'Recibe a los participantes')
        self.assertNotContains(response,'href="?tab=reception"')
        self.assertNotContains(response,'Abrir captura de marcas')
        response=self.client.post(path,{'action':'phase','phase':'live','test':0},follow=True)
        self.assertContains(response,'Competencia iniciada.')
        self.assertNotContains(response,'Abrir captura de marcas')
        capture(self.entry.pk,self.coach,0,42,None,'done',0,'')
        self.assertContains(self.client.get(path),'1 / 1 pruebas realizadas')
        response=self.client.post(path,{'action':'phase','phase':'closed'},follow=True)
        self.assertContains(response,'Evento finalizado')
        self.assertNotContains(response,'Activar estación seleccionada')

    def test_capture_workspace_starts_with_hidden_cards_and_bounded_selector(self):
        response=self.client.get(self.path)
        self.assertContains(response,'id="capture-options"')
        self.assertContains(response,'id="capture-next-pending"')
        self.assertContains(response,'data-filter="drafts"')
        self.assertContains(response,'<form class="capture-card" hidden')

    def test_different_coaches_save_different_participants_in_same_station(self):
        self.client.force_login(self.admin)
        self.event.allow_onsite=True;self.event.save(update_fields=['allow_onsite'])
        data=self.data();data['name']='Segundo atleta'
        self.client.post(self.url,data)
        other=Registration.objects.exclude(pk=self.entry.pk).get()
        second_coach=User.objects.create_user('second-coach',password='test-password')
        second_coach.groups.add(Group.objects.get(name='Coach'))
        self.client.force_login(self.coach)
        self.assertEqual(self.client.post(self.path,self.payload()).status_code,200)
        self.client.force_login(second_coach)
        self.assertEqual(self.client.post(self.path,self.payload(registration=other.pk,value='60')).status_code,200)
        marks={r['id']:r['marks'][0] for r in self.client.get(self.feed).json()['board']}
        self.assertEqual(marks[self.entry.pk]['value'],42)
        self.assertEqual(marks[other.pk]['value'],60)
        self.assertEqual(Result.objects.count(),2)

    def test_station_stays_active_and_repeat_activation_preserves_marks(self):
        from .models import Audit
        capture(self.entry.pk,self.coach,0,42,None,'done',0,'')
        self.client.force_login(self.admin)
        path=f'/events/{self.event.pk}/operations/'
        before=Audit.objects.filter(action='phase').count()
        for tab in ['overview','results','reception']:
            response=self.client.get(path,{'tab':tab})
            self.assertContains(response,'data-station-submit disabled')
        response=self.client.post(path,{'action':'phase','phase':'live','test':0,'expected_test':0},follow=True)
        self.assertContains(response,'La estación ya está activa. Las marcas se conservan.')
        self.assertEqual(Audit.objects.filter(action='phase').count(),before)
        self.assertEqual(Result.objects.get().value,42)
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'live',0,expected_test=99)

    def test_time_formats_persist_normalized_marks_in_response_and_live_feed(self):
        station=self.event.rules['tests'][0]
        station.update(unit='seg',higher=False)
        station['parameters']['metric']='time'
        self.event.save(update_fields=['rules'])
        self.assertNotContains(self.client.get(self.path),'name="time_format"')
        response=self.client.post(self.path,self.payload(value='5.365',time_format='minutes'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['value'],321.9)
        self.assertEqual(Result.objects.get().value,321.9)
        self.assertEqual(self.client.get(self.feed).json()['board'][0]['marks'][0]['value'],321.9)
        response=self.client.post(self.path,self.payload(value='5:36.5',time_format='minutes_seconds',revision=1,reason='Correccion'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(Result.objects.get().value,336.5)
        response=self.client.post(self.path,self.payload(value='5:70',time_format='minutes_seconds',revision=2,reason='Correccion'))
        self.assertEqual(response.status_code,400)
        self.assertEqual(Result.objects.get().value,336.5)

    def test_catalog_minutes_are_used_without_coach_format_choice(self):
        station=self.event.rules['tests'][0];station.update(unit='seg',higher=False)
        station['parameters'].update(metric='time',time_entry='minutes_seconds_dot')
        self.event.save(update_fields=['rules'])
        response=self.client.post(self.path,self.payload(value='25.15'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(Result.objects.get().value,1515)
        self.assertContains(self.client.get(self.path),'value="25.15"')
        response=self.client.post(self.path,self.payload(value='25.70',revision=1,reason='Correccion'))
        self.assertEqual(response.status_code,400)
        self.assertEqual(Result.objects.get().value,1515)
