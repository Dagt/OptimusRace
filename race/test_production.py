from unittest.mock import patch
from django.db import DatabaseError
from django.test import TestCase, SimpleTestCase, RequestFactory, override_settings
from django.http import HttpResponse
from django.core.management import call_command
from django.core.management.base import CommandError
from optimus.proxy import WorkerProxyMiddleware
from django.test import TransactionTestCase
from django.db import connection, connections, close_old_connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from . import test_parallel_stations as station_fixtures
from .models import Result
from .services import capture


class HealthTests(TestCase):
    def test_health_checks_database_without_exposing_data(self):
        response=self.client.get('/healthz/')
        self.assertEqual(response.json(),{'status':'ok'})
        self.assertIn('no-store',response['Cache-Control'])
        with patch('optimus.health.connection.cursor',side_effect=DatabaseError('private failure')):
            response=self.client.get('/healthz/')
        self.assertEqual(response.status_code,503)
        self.assertNotIn('private',response.content.decode())


@override_settings(WORKER_PUBLIC_HOST='race.example.test',WORKER_PROXY_SECRET='x'*40)
class WorkerTrustTests(SimpleTestCase):
    def test_only_authenticated_worker_changes_host(self):
        middleware=WorkerProxyMiddleware(lambda request:HttpResponse(request.META['HTTP_HOST']))
        for token,expected in [('', 'origin.up.railway.app'),('bad','origin.up.railway.app'),('x'*40,'race.example.test')]:
            request=RequestFactory().get('/',HTTP_HOST='origin.up.railway.app',HTTP_X_OPTIMUS_PROXY_TOKEN=token,HTTP_X_FORWARDED_HOST='attacker.test')
            self.assertEqual(middleware(request).content.decode(),expected)
            self.assertNotIn('HTTP_X_OPTIMUS_PROXY_TOKEN',request.META)

    @override_settings(MEDIA_STORAGE='r2')
    def test_local_backup_refuses_to_claim_remote_photos_are_backed_up(self):
        with self.assertRaises(CommandError):call_command('backup_data')


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
class PostgreSQLCaptureTests(TransactionTestCase):
    entry=station_fixtures.ParallelStationTests.entry
    setUp=station_fixtures.ParallelStationTests.setUp

    def test_two_coaches_save_same_participant_at_different_stations(self):
        barrier=Barrier(2)
        def save(actor,station,value,revision):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                capture(self.a.pk,actor,station,value,None,'done',revision,'Corrección',assignment_revision=1)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(save,self.scoring_coach,0,22,1),pool.submit(save,self.other,1,33,0)]
            for job in jobs:job.result(timeout=30)
        self.assertEqual(dict(Result.objects.filter(registration=self.a).values_list('test','value')),{0:22,1:33})
