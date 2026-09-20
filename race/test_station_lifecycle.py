from copy import deepcopy
from datetime import date
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError
from . import test_cash_participants as fixtures
from .models import Participant,Registration,Result
from .services import capture,change_phase,close_station,station_pending,register_person_cash

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class StationLifecycleTests(TestCase):
    def setUp(self):
        fixtures.CashParticipantTests.setUp(self)
        first=self.event.rules['tests'][0];first['max_points']=50
        second=deepcopy(first);second['name']='Segunda estación'
        self.event.rules['tests'].append(second);self.event.save()
        person=Participant.objects.create(name='Atleta',sex='M',birth_date=date(1990,1,1))
        self.entry=register_person_cash(self.event.pk,person,self.admin,65)
        change_phase(self.event.pk,self.admin,'live')
        self.event.refresh_from_db()

    def mark(self,status,value=None,revision=0,reason='',test=0):
        return capture(self.entry.pk,self.scoring_coach,test,value,None,status,revision,reason)

    def test_registration_is_paid_without_assuming_attendance(self):
        self.assertEqual(self.entry.state,'confirmed');self.assertIsNotNone(self.entry.paid_at)
        self.assertEqual(self.entry.attendance,'pending')
        self.mark('done',42);self.entry.refresh_from_db();self.assertEqual(self.entry.attendance,'present')

    def test_absent_at_one_station_can_participate_at_the_next(self):
        self.mark('absent');self.entry.refresh_from_db();self.assertEqual(self.entry.attendance,'pending')
        close_station(self.event.pk,self.admin,0)
        change_phase(self.event.pk,self.admin,'live',1)
        self.mark('done',30,test=1);self.entry.refresh_from_db()
        self.assertEqual(self.entry.attendance,'present');self.assertEqual(Result.objects.get(test=0).status,'absent')

    def test_only_admin_closes_after_all_participants_are_reviewed(self):
        with self.assertRaises(ValidationError):close_station(self.event.pk,self.scoring_coach,0)
        with self.assertRaises(ValidationError):close_station(self.event.pk,self.admin,0)
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'live',1)
        self.mark('done',42);close_station(self.event.pk,self.admin,0)
        with self.assertRaises(ValidationError):self.mark('done',50,1,'Corregir')
        close_station(self.event.pk,self.admin,0,reopen=True)
        self.mark('done',50,1,'Corregir');self.assertEqual(Result.objects.get().value,50)

    def test_withdrawal_removes_future_pending_without_fabricating_marks(self):
        self.mark('withdrawn');self.entry.refresh_from_db();self.assertEqual(self.entry.attendance,'withdrawn')
        close_station(self.event.pk,self.admin,0);change_phase(self.event.pk,self.admin,'live',1)
        self.event.refresh_from_db();self.assertFalse(station_pending(self.event).exists())
        self.assertEqual(Result.objects.count(),1)
        with self.assertRaises(ValidationError):self.mark('done',42,test=1)

    def test_late_registration_requires_review_before_advancing(self):
        self.mark('done',42);close_station(self.event.pk,self.admin,0)
        self.event.allow_onsite=True;self.event.save(update_fields=['allow_onsite'])
        person=Participant.objects.create(name='Nuevo',sex='M',birth_date=date(1990,1,1))
        register_person_cash(self.event.pk,person,self.admin,65)
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'live',1)
        close_station(self.event.pk,self.admin,0,reopen=True)
        self.event.refresh_from_db();self.assertEqual(station_pending(self.event).count(),1)

    def test_admin_can_close_and_reopen_from_operations(self):
        from django.urls import reverse
        self.mark('done',42)
        self.client.force_login(self.admin)
        url=reverse('operations',args=[self.event.pk])
        response=self.client.post(url,{'action':'close_station','test':0})
        self.assertEqual(response.status_code,302)
        self.event.refresh_from_db();self.assertTrue(self.event.station_capture_closed)
        data=self.client.get(reverse('live_data',args=[self.event.pk])).json()
        self.assertTrue(data['station_closed']);self.assertEqual(data['station_pending'],0)
        response=self.client.post(url,{'action':'reopen_station','test':0})
        self.assertEqual(response.status_code,302)
        self.event.refresh_from_db();self.assertFalse(self.event.station_capture_closed)

    def test_coach_reload_only_renders_marks_for_current_station(self):
        from django.urls import reverse
        self.mark('done',42)
        close_station(self.event.pk,self.admin,0)
        change_phase(self.event.pk,self.admin,'live',1)
        self.client.force_login(self.scoring_coach)
        response=self.client.get(reverse('coach',args=[self.event.pk]))
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(response.context['event'].active_test,1)
        self.assertIsNone(response.context['rows'][0]['mark'])
        self.assertContains(response,'name="test" value="1"')
        self.assertEqual(Result.objects.get(test=0).value,42)

    def test_closure_uses_current_marks_after_admin_opened_pending_screen(self):
        from django.urls import reverse
        self.client.force_login(self.admin)
        url=reverse('operations',args=[self.event.pk])
        response=self.client.get(url)
        self.assertEqual(response.context['station_pending_count'],1)
        self.assertContains(response,'data-station-toggle')
        from .stations import assign_coach
        a=assign_coach(self.event.pk,self.admin,self.scoring_coach.pk,0,0)
        capture(self.entry.pk,self.scoring_coach,0,42,None,'done',0,'',assignment_revision=a.revision)
        response=self.client.post(url,{'action':'close_station','test':0},follow=True)
        self.event.refresh_from_db()
        self.assertTrue(self.event.station_capture_closed)
        self.assertEqual(response.context['station_pending_count'],0)

    def test_capture_prefills_rule_load_but_keeps_saved_load(self):
        from django.urls import reverse
        self.event.rules['tests'][0]['parameters']={'load_mode':'body_percent','load_value':75,'round_mode':'down','load_step':2.5,'bar_weight':20}
        self.event.save()
        self.client.force_login(self.scoring_coach)
        url=reverse('coach',args=[self.event.pk])
        response=self.client.get(url)
        self.assertEqual(response.context['rows'][0]['suggested'],47.5)
        self.assertContains(response,'value="47.5" placeholder')
        capture(self.entry.pk,self.scoring_coach,0,42,50,'done',0,'')
        self.assertContains(self.client.get(url),'value="50.0" placeholder')
