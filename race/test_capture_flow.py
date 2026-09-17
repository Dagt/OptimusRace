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
        self.assertContains(response,'Abrir captura de marcas')
        capture(self.entry.pk,self.coach,0,42,None,'done',0,'')
        self.assertContains(self.client.get(path),'1 de 1 participantes con esta prueba realizada')
        response=self.client.post(path,{'action':'phase','phase':'closed'},follow=True)
        self.assertContains(response,'Evento finalizado')
        self.assertNotContains(response,'Activar estación seleccionada')
