from django.test import SimpleTestCase
from .event_highlights import event_highlights


class EventHighlightsTests(SimpleTestCase):
    def test_direction_ties_and_overall_across_categories(self):
        tests = [dict(name='Carrera', unit='seg', higher=False),
                 dict(name='Salto', unit='cm', higher=True)]
        rows = [dict(bib=i, name=str(i), category=category, attendance='present',
                     completed=2, total=total, marks=[
                         dict(status='done', value=time), dict(status='done', value=jump)])
                for i, category, time, jump, total in [
                    (1, 'Femenil', 12, 45, 80), (2, 'Varonil', 10, 40, 90),
                    (3, 'Femenil', 10, 50, 90)]]
        rows.append(dict(rows[0], bib=4, attendance='disqualified', total=100))
        result = event_highlights(tests, rows)
        self.assertEqual([(r['title'], r['bib'], r['value']) for r in result], [
            ('Carrera', 2, 10), ('Carrera', 3, 10), ('Salto', 3, 50),
            ('Mayor puntaje acumulado', 2, 90), ('Mayor puntaje acumulado', 3, 90)])

    def test_missing_marks_and_judged_points(self):
        tests = [dict(name='Juez', unit='pts', scoring='judge', higher=False)]
        row = dict(bib=1, name='Uno', category='A', completed=0, total=0,
                   marks=[dict(status='absent', value=100, points=100)])
        self.assertEqual(event_highlights(tests, [row]), [])
        row.update(completed=1, total=8, marks=[dict(status='done', value=1, points=8)])
        result = event_highlights(tests, [row])
        self.assertEqual(result[0]['value'], 8)
        self.assertEqual(event_highlights(tests, []), [])
