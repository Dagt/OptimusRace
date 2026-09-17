from copy import deepcopy
from django.test import TestCase,override_settings
from django.contrib.auth.models import User,Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event,Profile,Registration,Result,TieBreak
from .services import board,capture,change_phase,validate_rules,check_in,discipline
from .relative_scoring import relative_points,tie_groups,resolve_tie
from .progress import comparison_key

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RelativeScoringTests(TestCase):
    def setUp(self):
        self.scoring_coach=User.objects.create_user('scoring-coach')
        self.scoring_coach.groups.add(Group.objects.get_or_create(name='Coach')[0])
        self.admin=User.objects.create_superuser('admin','admin@example.test','test-only-password')
        self.rules={'schema_version':2,'tests':[{'name':'Repeticiones','unit':'reps','capacity':'Resistencia','higher':True,'base':None,'elite':None,'max_points':100,'scoring':'relative','parameters':{'metric':'repetitions','duration_seconds':60}}],
                    'categories':[{'name':'M','sex':'M','min':0,'max':None},{'name':'F','sex':'F','min':0,'max':None}]}
        self.event=Event.objects.create(name='Relativa',date=timezone.now(),registration_end=timezone.now()-timezone.timedelta(hours=1),status='live',rules=deepcopy(self.rules),capacity=20)
        self.a=self.entry('A',20);self.b=self.entry('B',30);self.c=self.entry('C',40)
    def entry(self,name,value=None,category='M'):
        user=User.objects.create_user(name,email=f'{name}@example.test');Profile.objects.create(user=user,sex=category)
        entry=Registration.objects.create(event=self.event,user=user,name=name,sex=category,category=category,bib=Registration.objects.count()+1,state='confirmed',attendance='present',weight=70)
        if value is not None:capture(entry.pk,self.scoring_coach,0,value,None,'done',0,'')
        return entry
    def scores(self):return {row['name']:row['total'] for row in board(self.event)}
    def decision(self,order=None):
        group=tie_groups(board(self.event))[0]
        order=order or [row['id'] for row in group['members']]
        return resolve_tie(self.event.pk,self.admin,group['category'],group['total'],order,group['fingerprint'],'Vencidas','Ganador verificado en pista','Juez de prueba')
    def test_minmax_direction_and_equal_results(self):
        self.assertEqual([relative_points(v,[20,30,40],12.5,True) for v in [20,30,40]],[0,6.25,12.5])
        self.assertEqual([relative_points(v,[10,20,30],12.5,False) for v in [10,20,30]],[12.5,6.25,0])
        self.assertEqual(relative_points(20,[20],12.5,True),12.5)
        self.assertEqual(relative_points(20,[20,20],12.5,True),12.5)
    def test_recalculation_and_category_isolation(self):
        self.assertEqual(self.scores(),{'C':100,'B':50,'A':0})
        self.entry('D',60)
        self.assertEqual(self.scores()['B'],25)
        self.entry('F',1000,category='F')
        self.assertEqual(self.scores()['B'],25);self.assertEqual(self.scores()['F'],100)
        self.assertIsNone(Result.objects.get(registration=self.b).points)
    def test_missing_results_excluded_but_zero_is_valid(self):
        pending=self.entry('Pending')
        capture(pending.pk,self.scoring_coach,0,None,None,'absent',0,'')
        self.assertEqual(self.scores()['B'],50)
        zero=self.entry('Zero',0)
        self.assertEqual(self.scores()['A'],50)
        row=next(row for row in board(self.event) if row['id']==zero.id)
        self.assertEqual(row['completed'],1);self.assertEqual(row['total'],0)
    def test_disqualification_and_category_change_recalculate(self):
        discipline(self.c.pk,self.admin,True,'Motivo',0)
        self.assertEqual(self.scores()['B'],100)
        row=next(row for row in board(self.event) if row['id']==self.c.pk)
        self.assertIsNone(row['rank']);self.assertIsNone(row['marks'][0]['points'])
        self.b.category='Otra categoría';self.b.save()
        self.assertEqual(self.scores()['A'],100)
    def test_relative_publish_requires_no_benchmarks_and_legacy_rejected(self):
        validate_rules(self.rules)
        legacy=deepcopy(self.rules);legacy.pop('schema_version')
        with self.assertRaises(ValidationError):validate_rules(legacy)
    def test_closing_freezes_points_and_chart_snapshot(self):
        before=board(self.event);self.assertTrue(before[0]['provisional'])
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        frozen=board(self.event)
        self.assertEqual(frozen[0]['name'],'C');self.assertTrue(frozen[0]['champion'])
        self.assertFalse(frozen[0]['provisional']);self.assertFalse(frozen[0]['marks'][0]['provisional'])
        self.assertEqual(Result.objects.get(registration=self.b).points,50)
        # Even a direct database mark change cannot change the closed snapshot.
        Result.objects.filter(registration=self.c).update(value=999)
        self.assertEqual(board(self.event),frozen)
    def test_tie_order_does_not_change_points_or_marks(self):
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Corregir marca')
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'closed')
        self.decision([self.c.pk,self.b.pk])
        rows={row['name']:row for row in board(self.event)}
        self.assertEqual(rows['C']['rank'],1);self.assertEqual(rows['B']['rank'],2)
        self.assertEqual(rows['C']['total'],100);self.assertEqual(rows['B']['total'],100)
        self.assertEqual(rows['B']['marks'][0]['value'],40)
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        self.assertEqual(sum(row['champion'] for row in board(self.event)),1)
        with self.assertRaises(ValidationError):self.decision([self.b.pk,self.c.pk])
    def test_stale_tie_is_invalidated_even_when_total_stays_equal(self):
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Corregir')
        group=tie_groups(board(self.event))[0];self.decision()
        capture(self.a.pk,self.scoring_coach,0,10,None,'done',1,'Corregir extremo')
        self.assertTrue(any(row['tie_pending'] for row in board(self.event)))
        with self.assertRaises(ValidationError):resolve_tie(self.event.pk,self.admin,'M',100,[self.b.pk,self.c.pk],group['fingerprint'],'Vencidas','Resultado','Juez')
        with self.assertRaises(ValidationError):change_phase(self.event.pk,self.admin,'closed')
    def test_tie_rejects_wrong_members_and_unauthorized_actor(self):
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Corregir')
        with self.assertRaises(ValidationError):self.decision([self.b.pk,self.a.pk])
        group=tie_groups(board(self.event))[0]
        with self.assertRaises(ValidationError):resolve_tie(self.event.pk,self.a.user,'M',100,[self.b.pk,self.c.pk],group['fingerprint'],'Vencidas','Resultado','Juez')
        self.assertEqual(TieBreak.objects.count(),0)
    def test_capture_response_is_provisional_and_does_not_lose_zero(self):
        self.client.force_login(self.scoring_coach)
        response=self.client.post(f'/events/{self.event.pk}/coach/',{'registration':self.a.pk,'test':0,'value':20,'status':'done','revision':1,'reason':'Verificar'})
        self.assertEqual(response.json()['points'],0);self.assertTrue(response.json()['provisional'])
        self.assertContains(self.client.get(f'/events/{self.event.pk}/coach/'),'provisional')
    def test_protocol_comparisons_are_separate_but_scoring_is_not_physical_protocol(self):
        test=self.rules['tests'][0];other=deepcopy(test)
        other['parameters']['duration_seconds']=120
        self.assertNotEqual(comparison_key(test),comparison_key(other))
        other=deepcopy(test);other['scoring']='linear';other['base']=20
        self.assertEqual(comparison_key(test),comparison_key(other))
    def test_views_show_relative_radar_and_tie_form(self):
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Corregir')
        self.client.force_login(self.admin)
        response=self.client.get(f'/events/{self.event.pk}/operations/')
        self.assertContains(response,'Guardar desempate');self.assertContains(response,'Primer lugar · por resolver')
        from .models import Participant
        person=Participant.objects.create(name=self.b.name,sex='M');self.b.participant=person;self.b.save()
        self.client.logout()
        response=self.client.get(f'/results/participants/{person.pk}/')
        self.assertContains(response,'Desempeño relativo en tu categoría.')
        self.assertContains(response,'comparison_key')

    def test_operations_tiebreak_and_close_http(self):
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Corregir')
        group=tie_groups(board(self.event))[0]
        self.client.force_login(self.admin)
        url=f'/events/{self.event.pk}/operations/'
        data={'action':'tiebreak','tab':'results','category':'M','total':'100','fingerprint':group['fingerprint'],
              'member':[self.b.pk,self.c.pk],'place':[1,1],'challenge':'Destreza','judge':'Juez','details':'C gana'}
        self.client.post(url,data)
        self.assertEqual(TieBreak.objects.count(),0)
        self.client.post(url,{'action':'phase','phase':'closed'})
        self.event.refresh_from_db();self.assertEqual(self.event.status,'live')
        data['place']=[2,1]
        response=self.client.post(url,data)
        self.assertEqual(response.status_code,302);self.assertEqual(TieBreak.objects.count(),1)
        self.client.post(url,{'action':'phase','phase':'closed'})
        self.event.refresh_from_db();self.assertEqual(self.event.status,'closed')
        rows={r['id']:r for r in board(self.event)}
        self.assertTrue(rows[self.c.pk]['champion']);self.assertFalse(rows[self.b.pk]['champion'])
        self.assertEqual(rows[self.b.pk]['total'],rows[self.c.pk]['total'])
        self.assertContains(self.client.get(url),'Campeón')

    def test_capacity_podium_accepts_missing_other_capacities_and_freezes(self):
        self.event.rules['capacity_podiums']=True
        first=self.event.rules['tests'][0];first['capacity']='Fuerza';first['max_points']=50
        second=deepcopy(first);second['capacity']='Velocidad';second['name']='Otra prueba'
        self.event.rules['tests'].append(second);self.event.save()
        rows=board(self.event)
        winner=next(r for r in rows if r['id']==self.c.pk)
        self.assertEqual(winner['capacity_results']['Fuerza']['rank'],1)
        self.assertIsNone(winner['capacity_results']['Velocidad']['rank'])
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        frozen=next(r for r in board(self.event) if r['id']==self.c.pk)
        self.assertTrue(frozen['capacity_results']['Fuerza']['winner'])
        self.assertFalse(frozen['capacity_results']['Fuerza']['provisional'])

    def test_capacity_tiebreak_is_independent_of_general(self):
        from .capacity_results import capacity_boards,all_ties
        self.event.rules['capacity_podiums']=True;self.event.save()
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Corregir')
        groups=all_ties(board(self.event));self.assertEqual(len(groups),2)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/operations/'),'Clasificación por capacidad')
        self.assertContains(self.client.get(f'/events/{self.event.pk}/'),'Clasificación por capacidad')
        self.assertContains(self.client.get(f'/events/{self.event.pk}/tv/'),'tv-scope')
        group=next(g for g in groups if g['scope']=='Resistencia')
        resolve_tie(self.event.pk,self.admin,'M',100,[self.c.pk,self.b.pk],group['fingerprint'],'Destreza','C gana','Juez',scope='Resistencia')
        rows=board(self.event)
        self.assertTrue(next(r for r in rows if r['id']==self.c.pk)['tie_pending'])
        self.assertEqual(next(r for r in capacity_boards(rows)['Resistencia'] if r['id']==self.c.pk)['rank'],1)
        self.decision([self.b.pk,self.c.pk])
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        rows=board(self.event)
        self.assertTrue(next(r for r in rows if r['id']==self.b.pk)['champion'])
        self.assertTrue(next(r for r in rows if r['id']==self.c.pk)['capacity_results']['Resistencia']['winner'])

    def test_ties_have_dedicated_tab_summary_alert_and_live_count(self):
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Empate de prueba')
        self.client.force_login(self.admin)
        path=f'/events/{self.event.pk}/operations/'
        response=self.client.get(path)
        self.assertContains(response,'data-tab="ties"')
        self.assertContains(response,'Resolver desempates →')
        self.assertEqual(response.context['pending_ties'],1)
        self.assertContains(response,'Lugar 1 en este desempate')
        self.assertNotContains(response,'class="tiebreak-entry panel" open')
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/live/').json()['pending_ties'],1)
        self.decision()
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/live/').json()['pending_ties'],0)

    def test_lower_place_ties_do_not_require_decision_or_block_close(self):
        capture(self.a.pk,self.scoring_coach,0,30,None,'done',1,'Empate en segundo')
        rows=board(self.event)
        self.assertEqual(tie_groups(rows),[])
        self.assertFalse(any(row['tie_pending'] for row in rows))
        with self.assertRaises(ValidationError):
            resolve_tie(self.event.pk,self.admin,'M',0,[self.a.pk,self.b.pk],'invalid','Prueba','Resultado','Juez')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/live/').json()['pending_ties'],0)
        change_phase(self.event.pk,self.admin,'closed')
        self.event.refresh_from_db();self.assertEqual(self.event.status,'closed')

    def test_capacity_lower_place_ties_are_not_offered(self):
        from .capacity_results import all_ties
        self.event.rules['capacity_podiums']=True;self.event.save()
        capture(self.a.pk,self.scoring_coach,0,30,None,'done',1,'Empate en segundo')
        self.assertEqual(all_ties(board(self.event)),[])
        change_phase(self.event.pk,self.admin,'closed')
