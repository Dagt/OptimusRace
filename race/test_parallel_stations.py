from copy import deepcopy
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User,Group
from . import test_relative as fixtures
from .models import Result,CoachAssignment
from .stations import ensure_stations,assign_coach,switch_station
from .services import capture,change_phase,station_pending

class ParallelStationTests(TestCase):
    entry=fixtures.RelativeScoringTests.entry
    def setUp(self):
        fixtures.RelativeScoringTests.setUp(self)
        self.event.rules['tests'][0]['max_points']=50
        second=deepcopy(self.event.rules['tests'][0]);second['name']='Otra estación'
        self.event.rules['tests'].append(second);self.event.save()
        ensure_stations(self.event)
        self.other=User.objects.create_user('coach-two');self.other.groups.add(Group.objects.get(name='Coach'))
        self.assignment=assign_coach(self.event.pk,self.admin,self.scoring_coach.pk,0,0)
        assign_coach(self.event.pk,self.admin,self.other.pk,1,0)
        switch_station(self.event.pk,self.admin,1,True,0)
    def test_two_stations_capture_independently_and_close_separately(self):
        capture(self.a.pk,self.scoring_coach,0,22,None,'done',1,'Corrección',assignment_revision=1)
        capture(self.a.pk,self.other,1,33,None,'done',0,'',assignment_revision=1)
        self.assertEqual(Result.objects.get(registration=self.a,test=0).value,22)
        self.assertEqual(Result.objects.get(registration=self.a,test=1).value,33)
        switch_station(self.event.pk,self.admin,0,False,0)
        self.assertTrue(self.event.stations.get(test=1).is_open)
        with self.assertRaises(ValidationError):capture(self.b.pk,self.scoring_coach,0,22,None,'done',1,'Corrección',assignment_revision=1)
        capture(self.b.pk,self.other,1,34,None,'done',0,'',assignment_revision=1)
    def test_assignment_changes_block_stale_and_cross_station_posts(self):
        with self.assertRaises(ValidationError):capture(self.a.pk,self.scoring_coach,1,30,None,'done',0,'',assignment_revision=1)
        assign_coach(self.event.pk,self.admin,self.scoring_coach.pk,1,1)
        with self.assertRaises(ValidationError):capture(self.a.pk,self.scoring_coach,0,30,None,'done',1,'Correction',assignment_revision=1)
        capture(self.a.pk,self.scoring_coach,1,30,None,'done',0,'',assignment_revision=2)
        assign_coach(self.event.pk,self.admin,self.scoring_coach.pk,0,2)
        with self.assertRaises(ValidationError):capture(self.a.pk,self.scoring_coach,0,30,None,'done',1,'Correction',assignment_revision=1)
    def test_assignment_permissions_stale_updates_and_unassigned(self):
        with self.assertRaises(ValidationError):assign_coach(self.event.pk,self.other,self.scoring_coach.pk,1,1)
        with self.assertRaises(ValidationError):assign_coach(self.event.pk,self.admin,self.admin.pk,1,0)
        with self.assertRaises(ValidationError):assign_coach(self.event.pk,self.admin,self.scoring_coach.pk,1,0)
        assign_coach(self.event.pk,self.admin,self.scoring_coach.pk,None,1)
        self.client.force_login(self.scoring_coach)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/coach/'),'Esperando asignación')
        self.assertTrue(self.client.get(f'/events/{self.event.pk}/coach/feed/').json()['unassigned'])
    def test_coach_view_and_feed_use_assignment_not_legacy_active_test(self):
        self.client.force_login(self.other)
        response=self.client.get(f'/events/{self.event.pk}/coach/')
        self.assertEqual(response.context['test']['name'],'Otra estación')
        feed=self.client.get(f'/events/{self.event.pk}/coach/feed/').json()
        self.assertEqual(feed['test_index'],1);self.assertEqual(feed['assignment_revision'],1)
        self.assertFalse(feed['station_closed'])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/coach/feed/').status_code,403)
    def test_close_event_requires_all_stations_complete_and_closed(self):
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'closed')
        switch_station(self.event.pk,self.admin,1,False,1)
        self.assertEqual(station_pending(self.event,1).count(),3)
        self.assertEqual(self.a.attendance,'present')
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'closed')
    def test_admin_controls_and_public_feed(self):
        self.client.force_login(self.admin)
        response=self.client.get(f'/events/{self.event.pk}/operations/')
        self.assertContains(response,'role="switch"',count=2)
        self.assertContains(response,'data-assign-station="1"')
        feed=self.client.get(f'/events/{self.event.pk}/live/').json()
        self.assertEqual([x['index'] for x in feed['active_stations']],[0,1])
        self.assertNotIn('coach',str(feed['active_stations']))

    def test_many_coaches_share_station_and_stale_toggle_is_rejected(self):
        assign_coach(self.event.pk,self.admin,self.other.pk,0,1)
        capture(self.a.pk,self.scoring_coach,0,22,None,'done',1,'Correction',assignment_revision=1)
        capture(self.b.pk,self.other,0,33,None,'done',1,'Correction',assignment_revision=2)
        switch_station(self.event.pk,self.admin,0,False,0)
        with self.assertRaises(ValidationError):switch_station(self.event.pk,self.admin,0,True,0)
        with self.assertRaises(ValidationError):switch_station(self.event.pk,self.other,1,False,1)
    def test_all_finished_stations_allow_final_close(self):
        for entry,value in [(self.a,21),(self.b,32),(self.c,43)]:
            capture(entry.pk,self.other,1,value,None,'done',0,'',assignment_revision=1)
        switch_station(self.event.pk,self.admin,0,False,0)
        switch_station(self.event.pk,self.admin,1,False,1)
        change_phase(self.event.pk,self.admin,'closed')
        self.event.refresh_from_db();self.assertEqual(self.event.status,'closed')
