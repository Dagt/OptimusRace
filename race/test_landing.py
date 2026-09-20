from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from .models import Event

class LandingNavigationTests(TestCase):
    def event(self,name,status,days):
        return Event.objects.create(name=name,status=status,date=timezone.now()+timedelta(days=days),registration_end=timezone.now(),capacity=10,rules={})

    def test_live_event_has_priority_and_destinations_are_direct(self):
        live=self.event('Live unique','live',0)
        future=self.event('Future unique','open',10)
        closed=self.event('Closed unique','closed',-10)
        self.event('Private unique','draft',20)
        response=self.client.get('/')
        self.assertEqual(response.context['featured'],live)
        self.assertContains(response,live.name,count=1)
        self.assertContains(response,f'/events/{live.pk}/?tab=results')
        self.assertContains(response,f'/events/{future.pk}/')
        self.assertContains(response,f'/events/{closed.pk}/?tab=results')
        self.assertNotContains(response,'Private unique')
        self.assertNotContains(response,'href="#events"')
        self.assertNotContains(response,'href="#optimus-profile"')
        self.assertContains(response,'action="/results/"')

    def test_next_event_is_featured_once_with_countdown(self):
        event=self.event('Next unique','open',1)
        response=self.client.get('/')
        self.assertEqual(response.context['featured'],event)
        self.assertContains(response,event.name,count=1)
        self.assertContains(response,'data-countdown=')

    def test_finished_event_links_to_final_results_and_profile_search_stays_available(self):
        event=self.event('Finished unique','closed',-1)
        response=self.client.get('/')
        self.assertEqual(response.context['featured'],event)
        self.assertContains(response,'Ver resultados finales')
        self.assertContains(response,'id="profile-query"')
        self.assertNotContains(response,'data-countdown=')
