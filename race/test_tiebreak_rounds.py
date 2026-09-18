from copy import deepcopy
from django.test import TestCase
from django.core.exceptions import ValidationError
from . import test_relative as fixtures
from .models import Exercise, Result, TieBreak, TieBreakMark
from .services import board, capture
from .relative_scoring import tie_groups
from .tiebreak_rounds import start_round, save_mark, finish_round

class CatalogPlayoffTests(TestCase):
    def setUp(self):
        fixtures.RelativeScoringTests.setUp(self)
        capture(self.b.pk,self.scoring_coach,0,40,None,'done',1,'Empate de prueba')
        self.exercise=Exercise.objects.create(name='Sprint',unit='seg',capacity='Velocidad',higher=False,parameters={'metric':'time','time_entry':'seconds'})
    entry=fixtures.RelativeScoringTests.entry
    def start(self):
        group=tie_groups(board(self.event))[0]
        return start_round(self.event.pk,self.admin,group['category'],group['fingerprint'],self.exercise.pk)
    def test_separate_marks_and_first_place_only(self):
        before=list(Result.objects.values())
        prior={r['id']:(r['total'],r['marks'],r.get('capacities')) for r in board(self.event)}
        rnd=self.start()
        save_mark(rnd.pk,self.scoring_coach,self.b.pk,'15.25')
        save_mark(rnd.pk,self.scoring_coach,self.c.pk,'16.15')
        finish_round(rnd.pk,self.scoring_coach)
        self.assertEqual(before,list(Result.objects.values()))
        after=board(self.event)
        self.assertEqual(prior,{r['id']:(r['total'],r['marks'],r.get('capacities')) for r in after})
        self.assertEqual(next(r for r in after if r['id']==self.b.pk)['rank'],1)
        self.assertFalse(any(r.get('tie_pending') for r in after))
    def test_repeat_only_equal_best_and_snapshot(self):
        capture(self.a.pk,self.scoring_coach,0,40,None,'done',1,'Empate')
        rnd=self.start()
        self.exercise.higher=True;self.exercise.save()
        for entry,value in [(self.a,20),(self.b,15),(self.c,15)]:save_mark(rnd.pk,self.scoring_coach,entry.pk,value)
        finish_round(rnd.pk,self.scoring_coach)
        rnd.refresh_from_db();self.assertEqual(rnd.status,'tied')
        self.assertEqual(set(rnd.finalists),{self.b.pk,self.c.pk})
        next_round=self.start();self.assertEqual(set(next_round.contenders),{self.b.pk,self.c.pk})
        save_mark(next_round.pk,self.scoring_coach,self.b.pk,25)
        save_mark(next_round.pk,self.scoring_coach,self.c.pk,20)
        finish_round(next_round.pk,self.scoring_coach)
        ranks={r['id']:r['rank'] for r in board(self.event)}
        self.assertEqual(ranks,{self.b.pk:1,self.c.pk:2,self.a.pk:2})
    def test_permissions_duplicates_and_revision(self):
        rnd=self.start()
        with self.assertRaises(ValidationError):self.start()
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.admin,self.b.pk,15)
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.a.pk,15)
        with self.assertRaises(ValidationError):finish_round(rnd.pk,self.scoring_coach)
        save_mark(rnd.pk,self.scoring_coach,self.b.pk,15)
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,20)
        self.assertEqual(TieBreakMark.objects.get(round=rnd).value,15)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/tiebreaks/').status_code,403)
        self.client.force_login(self.scoring_coach)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/tiebreaks/'),'Guardar marca')
        group=tie_groups(board(self.event))[0]
        with self.assertRaises(ValidationError):start_round(self.event.pk,self.scoring_coach,group['category'],group['fingerprint'],self.exercise.pk)
    def test_stale_evidence_and_invalid_values(self):
        rnd=self.start()
        for value in ['nan','inf','-1','abc','0']:
            with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,value)
        capture(self.b.pk,self.scoring_coach,0,39,None,'done',2,'Cambio')
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,15)
        with self.assertRaises(ValidationError):finish_round(rnd.pk,self.scoring_coach)
    def test_minutes_and_closed_round(self):
        self.exercise.parameters['time_entry']='minutes_seconds_dot';self.exercise.save()
        rnd=self.start()
        self.assertEqual(save_mark(rnd.pk,self.scoring_coach,self.b.pk,'5.15').value,315)
        save_mark(rnd.pk,self.scoring_coach,self.c.pk,'6.01')
        finish_round(rnd.pk,self.scoring_coach)
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,'4.15',revision=1)
    def test_admin_catalog_form_and_legacy_route_disabled(self):
        self.client.force_login(self.admin)
        response=self.client.get(f'/events/{self.event.pk}/operations/?tab=ties')
        self.assertContains(response,'Prueba del catálogo')
        self.assertNotContains(response,'Resultado observado')
        self.client.post(f'/events/{self.event.pk}/operations/',{'action':'tiebreak','tab':'ties'})
        self.assertEqual(TieBreak.objects.count(),0)

    def test_load_rule_and_minutes_page_rendering(self):
        self.exercise.parameters={'metric':'repetitions','load_mode':'body_percent','load_value':75}
        self.exercise.unit='reps';self.exercise.save()
        rnd=self.start()
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,'15.5',52.5)
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,15,50)
        mark=save_mark(rnd.pk,self.scoring_coach,self.b.pk,15,52.5)
        self.assertEqual(mark.load,52.5)
        rnd.test['unit']='seg';rnd.test['parameters']={'metric':'time','time_entry':'minutes_seconds_dot'};rnd.save()
        self.client.force_login(self.scoring_coach)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/tiebreaks/'),'min.seg')

    def test_finished_event_rejects_changes(self):
        rnd=self.start()
        self.event.status='closed';self.event.save()
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,15)
        with self.assertRaises(ValidationError):finish_round(rnd.pk,self.scoring_coach)

    def duel(self,target=2):
        self.exercise.parameters={'metric':'duel','wins_required':target};self.exercise.unit='victorias';self.exercise.higher=True;self.exercise.save()
        return self.start()

    def test_configurable_duel_and_no_score_changes(self):
        from .tiebreak_rounds import record_victory
        before=list(Result.objects.values())
        rnd=self.duel(3);match=rnd.matches.get()
        for i,winner in enumerate([self.b.pk,self.c.pk,self.b.pk,self.b.pk]):record_victory(rnd.pk,self.scoring_coach,match.pk,i,winner)
        with self.assertRaises(ValidationError):record_victory(rnd.pk,self.scoring_coach,match.pk,4,self.c.pk)
        with self.assertRaises(ValidationError):save_mark(rnd.pk,self.scoring_coach,self.b.pk,100)
        finish_round(rnd.pk,self.scoring_coach)
        self.assertEqual(before,list(Result.objects.values()))
        self.assertEqual(TieBreak.objects.get().order[0],self.b.pk)
        self.client.force_login(self.scoring_coach)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/tiebreaks/'),'Primero en llegar a 3 victorias')

    def test_victory_revision_undo_permissions_and_snapshot(self):
        from .tiebreak_rounds import record_victory
        rnd=self.duel();match=rnd.matches.get()
        self.exercise.parameters['wins_required']=5;self.exercise.save()
        with self.assertRaises(ValidationError):record_victory(rnd.pk,self.admin,match.pk,0,self.b.pk)
        with self.assertRaises(ValidationError):record_victory(rnd.pk,self.scoring_coach,match.pk,0,self.a.pk)
        record_victory(rnd.pk,self.scoring_coach,match.pk,0,self.b.pk)
        with self.assertRaises(ValidationError):record_victory(rnd.pk,self.scoring_coach,match.pk,0,self.c.pk)
        record_victory(rnd.pk,self.scoring_coach,match.pk,1,None)
        match.refresh_from_db();self.assertEqual(match.games,[])
        with self.assertRaises(ValidationError):finish_round(rnd.pk,self.scoring_coach)
        record_victory(rnd.pk,self.scoring_coach,match.pk,2,self.c.pk)
        record_victory(rnd.pk,self.scoring_coach,match.pk,3,self.c.pk)
        finish_round(rnd.pk,self.scoring_coach)
        with self.assertRaises(ValidationError):record_victory(rnd.pk,self.scoring_coach,match.pk,4,None)

    def test_three_contenders_round_robin_can_tie_again(self):
        from .tiebreak_rounds import record_victory
        capture(self.a.pk,self.scoring_coach,0,40,None,'done',1,'Empate')
        rnd=self.duel(1)
        self.assertEqual(rnd.matches.count(),3)
        for match in rnd.matches.all():
            pair={match.first_id,match.second_id}
            winner=self.a.pk if pair=={self.a.pk,self.b.pk} else self.b.pk if pair=={self.b.pk,self.c.pk} else self.c.pk
            record_victory(rnd.pk,self.scoring_coach,match.pk,0,winner)
        finish_round(rnd.pk,self.scoring_coach)
        rnd.refresh_from_db();self.assertEqual(rnd.status,'tied');self.assertEqual(len(rnd.finalists),3)
        self.assertEqual(len(self.start().contenders),3)

    def test_catalog_duel_target_required_and_editor_roundtrip(self):
        from .management_forms import CatalogForm
        data={'name':'Vencidas','capacity':'Fuerza','measurement':'duel','wins_required':4,'load_mode':'none','round_mode':'none'}
        form=CatalogForm(data);self.assertTrue(form.is_valid(),form.errors)
        exercise=form.save();self.assertEqual(exercise.parameters['wins_required'],4)
        self.assertEqual(CatalogForm(instance=exercise).initial['measurement'],'duel')
        for invalid in ['',0,1.5,100]:
            form=CatalogForm({**data,'wins_required':invalid},instance=exercise)
            self.assertFalse(form.is_valid())

    def test_frozen_winner_remains_visible_after_event_closes(self):
        from .tiebreak_rounds import rounds_for
        from .services import change_phase
        rnd=self.start()
        save_mark(rnd.pk,self.scoring_coach,self.b.pk,10)
        save_mark(rnd.pk,self.scoring_coach,self.c.pk,20)
        finish_round(rnd.pk,self.scoring_coach)
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        self.assertFalse(rounds_for(self.event)[0].stale)

    def test_public_broadcast_shows_pending_live_and_resolved_without_private_data(self):
        from .tiebreak_rounds import broadcast_playoffs,record_victory
        pending=broadcast_playoffs(self.event,board(self.event))
        self.assertEqual(pending[0]['status'],'pending')
        rnd=self.duel();match=rnd.matches.get()
        record_victory(rnd.pk,self.scoring_coach,match.pk,0,self.b.pk)
        live=self.client.get(f'/events/{self.event.pk}/live/').json()['playoffs']
        self.assertEqual(live[0]['target'],2)
        self.assertEqual(live[0]['players'][0]['value'],1)
        self.assertEqual(set(live[0]['players'][0]),{'id','name','bib','photo_url','value'})
        record_victory(rnd.pk,self.scoring_coach,match.pk,1,self.b.pk)
        finish_round(rnd.pk,self.scoring_coach)
        resolved=broadcast_playoffs(self.event,board(self.event))
        self.assertEqual(resolved[0]['winner'],self.b.pk)
        self.assertEqual(resolved[0]['status'],'resolved')

    def test_broadcast_ignores_stale_round_and_formats_minutes(self):
        from .tiebreak_rounds import broadcast_playoffs
        self.exercise.parameters['time_entry']='minutes_seconds_dot';self.exercise.save()
        rnd=self.start();save_mark(rnd.pk,self.scoring_coach,self.b.pk,'2.15')
        data=broadcast_playoffs(self.event,board(self.event))
        self.assertEqual(data[0]['players'][0]['value'],'2.15')
        capture(self.b.pk,self.scoring_coach,0,39,None,'done',2,'Cambio')
        self.assertEqual(broadcast_playoffs(self.event,board(self.event)),[])
