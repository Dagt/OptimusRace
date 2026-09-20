from copy import deepcopy
from django.test import TestCase,override_settings
from django.contrib.auth.models import User,Group
from django.urls import reverse
from django.utils import timezone
from .models import Event,Registration,Audit

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class EventInformationTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('owner','owner@example.test','test-password')
        self.coach=User.objects.create_user('coach')
        self.coach.groups.add(Group.objects.get_or_create(name='Coach')[0])
        self.event=Event.objects.create(name='Publicado',date=timezone.now(),registration_end=timezone.now(),
            status='open',capacity=10,price=45000,description='Original',
            rules={'tests':[],'categories':[],'benefits':'Agua','regulations':'Texto','judging_standard':'Escala fija'},
            final_board=[{'total':99}])
        self.registration=Registration.objects.create(event=self.event,name='Participante',sex='F',bib=1,state='confirmed')
        self.url=reverse('event_information',args=[self.event.pk])
        self.data={'description':'Descripción nueva','benefits':'Agua y playera','regulations':'Llegar temprano'}
        self.client.force_login(self.admin)

    def test_texts_editable_with_registration_in_every_phase_without_changing_competition(self):
        for status in ['draft','open','live','closed']:
            self.event.status=status;self.event.save()
            original=deepcopy(Event.objects.values().get(pk=self.event.pk))
            response=self.client.post(self.url,{**self.data,'rules':'{"tests":["tampered"]}',
                'price':1,'capacity':999,'status':'draft','judging_standard':'Changed'})
            self.assertRedirects(response,reverse('operations',args=[self.event.pk]),fetch_redirect_response=False)
            current=Event.objects.values().get(pk=self.event.pk)
            expected=deepcopy(original);expected['description']=self.data['description']
            expected['rules'].update({key:self.data[key] for key in ['benefits','regulations']})
            self.assertEqual(current,expected)
        self.assertEqual(Audit.objects.filter(event=self.event,action='information_updated').count(),4)
        self.assertTrue(Registration.objects.filter(pk=self.registration.pk,state='confirmed').exists())

    def test_editor_prefills_and_public_page_displays_saved_text(self):
        response=self.client.get(self.url)
        self.assertContains(response,'Original');self.assertContains(response,'Agua')
        self.client.post(self.url,self.data)
        self.client.logout()
        response=self.client.get(reverse('event',args=[self.event.pk]))
        for value in self.data.values():self.assertContains(response,value)

    def test_only_administrators_can_edit(self):
        self.client.force_login(self.coach)
        self.assertEqual(self.client.post(self.url,self.data).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.post(self.url,self.data).status_code,302)
        self.event.refresh_from_db();self.assertEqual(self.event.description,'Original')
