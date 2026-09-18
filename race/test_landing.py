from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from . import test_cash_participants as fixtures
from .models import Event

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class LandingTests(TestCase):
    def setUp(self):
        fixtures.CashParticipantTests.setUp(self)
        self.client.logout()

    def test_current_event_precedes_past_and_upcoming_is_chronological(self):
        live=Event.objects.create(name='Competencia actual',date=timezone.now(),status='live',rules=self.event.rules,registration_end=self.event.registration_end,price=45000,capacity=100)
        Event.objects.create(name='Edición cerrada',date=timezone.now()+timedelta(days=20),status='closed',rules=self.event.rules,registration_end=self.event.registration_end,price=45000,capacity=100)
        sooner=Event.objects.create(name='Próxima salida',date=timezone.now()+timedelta(days=2),status='open',rules=self.event.rules,registration_end=self.event.registration_end,price=45000,capacity=100)
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['selected_event'].pk,live.pk)
        self.assertEqual(response.context['upcoming'].pk,sooner.pk)
        self.assertEqual([e.pk for e in response.context['future_events']],[sooner.pk,self.event.pk])
        self.assertContains(response,'landing-countdown')
        self.assertContains(response,'Competencia actual')
        self.assertContains(response,'landing.css')

    def test_unpublished_events_are_not_promoted(self):
        self.event.status='draft';self.event.save()
        response=self.client.get('/')
        self.assertNotContains(response,self.event.name)
        self.assertNotContains(response,'data-countdown=')
        self.assertEqual(response.status_code,200)
