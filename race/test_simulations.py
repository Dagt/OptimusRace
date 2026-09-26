import json
import tempfile
import time
from pathlib import Path
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User, Group
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connections
from django.utils import timezone
from .models import Event, Participant, Registration, Result, EventStation, CoachAssignment
from .simulation_runtime import create, database, folder, metadata, cleanup


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SimulationTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.override=override_settings(SIMULATION_ROOT=Path(self.temp.name)/'simulations')
        self.override.enable();self.addCleanup(self.override.disable)
        self.admin=User.objects.create_superuser('owner','owner@example.test','secret')
        self.coach=User.objects.create_user('coach')
        self.coach.groups.add(Group.objects.get_or_create(name='Coach')[0])
        self.event=Event.objects.create(name='Real competition',status='live',date=timezone.now(),registration_end=timezone.now(),capacity=10,
            rules={'tests':[{'name':'Burpees','unit':'reps','capacity':'Resistencia','higher':True,'base':0,'elite':100}],
                   'categories':[{'name':'Abierta','sex':'F','min':0,'max':None}],'bar':0,'rounding':0,'round_mode':'none'})
        self.person=Participant.objects.create(name='Ana',sex='F')
        self.entry=Registration.objects.create(event=self.event,participant=self.person,name='Ana',sex='F',bib=7,weight=60,category='Abierta',amount=45000,method='cash')
        self.station=EventStation.objects.create(event=self.event,test=0,is_open=True,opened=True)
        CoachAssignment.objects.create(event=self.event,coach=self.coach,station=self.station)
        self.client.force_login(self.admin)

    def make(self):
        meta=create(self.event.pk,self.admin)
        self.prefix=meta['prefix']
        return meta

    def test_exact_copy_and_isolated_writes_with_connection_restored(self):
        Result.objects.create(registration=self.entry,test=0,value=15,points=15)
        original=connections['default']
        meta=self.make()
        with database(meta):
            self.assertEqual(Event.objects.get().rules['tests'],self.event.rules['tests'])
            self.assertEqual(Event.objects.get().rules['categories'],self.event.rules['categories'])
            self.assertEqual(Registration.objects.get().bib,7)
            self.assertEqual(Result.objects.get().value,15)
            self.assertEqual(CoachAssignment.objects.get().coach_id,self.coach.pk)
            Participant.objects.filter(pk=self.person.pk).update(name='Practice only')
            Event.objects.filter(pk=self.event.pk).update(capacity=20)
        self.assertIs(connections['default'],original)
        self.assertEqual(Event.objects.count(),1)
        self.person.refresh_from_db();self.event.refresh_from_db()
        self.assertEqual(self.person.name,'Ana');self.assertEqual(self.event.capacity,10)
        with self.assertRaises(RuntimeError):
            with database(meta):raise RuntimeError('failed view')
        self.assertIs(connections['default'],original)

    def test_admin_and_coach_share_real_capture_flow_but_public_cannot_enter(self):
        meta=self.make()
        path=self.prefix+f'/events/{self.event.pk}/operations/'
        response=self.client.get(path)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'SIMULACIÓN · COPIA TEMPORAL')
        self.assertContains(response,'href="/simulations/"')
        self.assertContains(response,self.prefix+f'/events/{self.event.pk}/tv/')
        visitor=Client().get(path)
        self.assertEqual(visitor.status_code,302)
        self.assertIn('no-store',visitor['Cache-Control'])
        self.client.force_login(self.coach)
        self.assertEqual(self.client.get(self.prefix+f'/events/{self.event.pk}/coach/').status_code,200)
        response=self.client.post(self.prefix+f'/events/{self.event.pk}/coach/',
            {'registration':self.entry.pk,'test':0,'value':'23','status':'done','revision':0,'assignment_revision':1})
        self.assertEqual(response.status_code,200,response.content)
        self.assertTrue(response.json()['ok'])
        with database(meta):self.assertEqual(Result.objects.get().value,23)
        self.assertFalse(Result.objects.exists())
        response=self.client.get(self.prefix+f'/events/{self.event.pk}/live/')
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(response['X-Robots-Tag'],'noindex, nofollow, noarchive')
        self.assertEqual(self.client.post(self.prefix+'/practice-control/',{'action':'finish'}).status_code,403)

    def test_reset_and_delete_only_snapshot_and_expiry(self):
        Result.objects.create(registration=self.entry,test=0,value=15,points=15)
        meta=self.make()
        response=self.client.post(self.prefix+'/practice-control/',{'action':'reset'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(response.url.startswith(self.prefix))
        with database(meta):
            self.assertFalse(Result.objects.exists())
            self.assertEqual(Event.objects.get().status,'open')
            self.assertEqual(Registration.objects.get().amount,45000)
        self.assertEqual(Result.objects.get().value,15)
        response=self.client.post(self.prefix+'/practice-control/',{'action':'finish'})
        self.assertEqual(response.url,'/simulations/')
        self.assertFalse(folder(meta['token']).exists())
        self.assertEqual(self.client.get(self.prefix+'/').status_code,410)
        self.assertEqual(Event.objects.count(),1)
        meta=self.make();meta['expires']=time.time()-1
        (folder(meta['token'])/'session.json').write_text(json.dumps(meta),encoding='utf-8')
        cleanup();self.assertFalse(folder(meta['token']).exists())

    def test_outbound_actions_blocked_and_media_disposable(self):
        meta=self.make()
        for path in ['/stripe/webhook/','/logout/','/reset/','/events/new/','/admin/']:
            self.assertEqual(self.client.post(self.prefix+path).status_code,403)
        with database(meta):
            name=default_storage.save('practice.txt',ContentFile(b'practice'))
            self.assertTrue(default_storage.url(name).startswith(self.prefix+'/practice-media/'))
        response=self.client.get(self.prefix+'/practice-media/'+name)
        self.assertEqual(response.content,b'practice')
        self.assertEqual(self.client.get('/practice-media/'+name).status_code,404)

    def test_csrf_and_removed_coach_access(self):
        meta=self.make()
        client=Client(enforce_csrf_checks=True);client.force_login(self.admin)
        self.assertEqual(client.post(self.prefix+'/practice-control/',{'action':'finish'}).status_code,403)
        self.assertTrue(folder(meta['token']).exists())
        self.client.force_login(self.coach)
        self.coach.groups.clear()
        self.assertEqual(self.client.get(self.prefix+'/').status_code,403)

    def test_thread_local_connection_does_not_leak_into_other_requests(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event as Signal
        meta=self.make()
        entered, release=Signal(),Signal()
        def worker():
            before=connections['default']
            try:
                with database(meta):
                    Event.objects.filter(pk=self.event.pk).update(name='Thread simulation')
                    entered.set()
                    release.wait(5)
                    return Event.objects.get().name
            finally:
                self.assertIs(connections['default'],before)
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(worker)
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(Event.objects.get().name,'Real competition')
            finally:release.set()
            self.assertEqual(future.result(),'Thread simulation')

    def test_original_photo_is_read_only_in_practice_and_reset_keeps_people(self):
        from django.core.files.storage import storages
        from unittest.mock import patch
        meta=self.make()
        original=storages['production_media']
        with database(meta), patch.object(original,'delete') as deletion, patch.object(original,'url',return_value='https://photos.example/old.jpg'):
            self.assertEqual(default_storage.url('old.jpg'),'https://photos.example/old.jpg')
            default_storage.delete('old.jpg')
            deletion.assert_not_called()
        with database(meta):
            from .simulation_runtime import reset_captures
            reset_captures(meta)
            self.assertEqual(Participant.objects.get().name,'Ana')
            self.assertEqual(Event.objects.get().rules['tests'],self.event.rules['tests'])
            self.assertEqual(Event.objects.get().rules['categories'],self.event.rules['categories'])

    def test_creation_endpoint_and_private_list_leave_public_event_count_unchanged(self):
        response=self.client.post(f'/events/{self.event.pk}/simulate/')
        self.assertEqual(response.status_code,302)
        self.assertTrue(response.url.startswith('/simulations/'))
        self.assertEqual(Event.objects.count(),1)
        self.assertContains(self.client.get('/simulations/'),'Real competition')
        anonymous=Client()
        self.assertEqual(anonymous.get('/simulations/').status_code,302)
        self.assertNotContains(anonymous.get('/'),'COPIA TEMPORAL')
        self.client.force_login(self.coach)
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/simulate/').status_code,403)

    def test_future_calendar_moves_to_now_without_modifying_real_event(self):
        from datetime import timedelta
        from .event_policy import validate_policies, instant
        from .stations import switch_station
        future=timezone.now()+timedelta(days=60)
        self.event.date=future
        self.event.registration_end=future-timedelta(hours=1)
        self.event.status='open'
        self.event.rules['schema_version']=2
        self.event.rules['tests'][0].update(max_points=100,scoring='relative',parameters={})
        self.event.rules.update(registration_start=(future-timedelta(days=30)).isoformat(),
            reception_start=future.isoformat(),reception_end=(future+timedelta(hours=2)).isoformat(),
            event_end=(future+timedelta(hours=4)).isoformat(),
            price_tiers=[{'name':'Early','amount':20000,'start':(future-timedelta(days=20)).isoformat(),'end':(future-timedelta(days=2)).isoformat()}])
        self.event.save()
        original_rules=json.loads(json.dumps(self.event.rules))
        meta=self.make()
        with database(meta):
            copied=Event.objects.get()
            self.assertLess(copied.date,timezone.now())
            self.assertGreater(instant(copied.rules['event_end']),timezone.now()+timedelta(hours=23))
            self.assertLess(instant(copied.rules['reception_start']),timezone.now())
            validate_policies(copied.rules,copied)
            switch_station(copied.pk,User.objects.get(pk=self.admin.pk),0,True,0)
            self.assertEqual(Event.objects.get().status,'live')
        self.event.refresh_from_db()
        self.assertEqual(self.event.date,future)
        self.assertEqual(self.event.rules,original_rules)
