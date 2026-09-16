import json
from django.test import TestCase,override_settings
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from .models import Event,Registration
from .event_policy import blank_rules

class EventEditorFlowTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('owner','owner@example.test','owner-password-192')
        self.client.force_login(self.admin)
        self.rules=blank_rules()
        self.rules['tests']=[{'name':'Carrera','unit':'seg','capacity':'Velocidad','higher':False,'scoring':'relative','max_points':100,'parameters':{}}]
        self.rules['categories']=[{'name':'Varonil · 60–70 kg','sex':'M','min':60,'max':70}]
        now=timezone.localtime()
        self.data={'name':'Evento de revisión','location':'Sede','date':(now+timezone.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),'registration_end':(now+timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),'price':'0','capacity':10,'minimum_age':0,'rules':json.dumps(self.rules)}

    def test_save_and_publish_makes_event_visible(self):
        response=self.client.post('/events/new/',{**self.data,'intent':'publish'})
        event=Event.objects.get()
        self.assertRedirects(response,f'/events/{event.pk}/operations/')
        self.assertEqual(event.status,'open')
        self.client.logout()
        self.assertContains(self.client.get('/'),event.name)

    def test_incomplete_publication_retains_editable_draft(self):
        self.rules['tests']=[]
        response=self.client.post('/events/new/',{**self.data,'intent':'publish','rules':json.dumps(self.rules)})
        event=Event.objects.get()
        self.assertRedirects(response,f'/events/{event.pk}/configure/')
        self.assertEqual(event.status,'draft')
        self.assertContains(self.client.get(f'/events/{event.pk}/configure/'),'Guardar y publicar')

    def test_draft_does_not_publish_and_add_station_follows_list(self):
        self.client.post('/events/new/',{**self.data,'intent':'draft'})
        self.assertEqual(Event.objects.get().status,'draft')
        html=self.client.get('/events/new/').content.decode()
        self.assertLess(html.index('id="test-editor"'),html.index('id="add-test"'))
        self.assertIn('category-branches',html)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_onsite_account_can_request_first_password(self):
        self.client.post('/events/new/',{**self.data,'intent':'publish'})
        event=Event.objects.get()
        before=User.objects.count()
        self.client.post(f'/events/{event.pk}/operations/',{'action':'cash','email':'first@example.test','name':'Primera','sex':'M','amount':'0'})
        self.assertEqual(User.objects.count(),before)
        self.assertFalse(Registration.objects.exists())
        self.assertContains(self.client.get(f'/events/{event.pk}/register/'),'Foto, pesaje y efectivo')
