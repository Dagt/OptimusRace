"""Public event highlights, independent of category prize rankings."""


def event_highlights(tests, rows):
    eligible = [row for row in rows if row.get('attendance') != 'disqualified']
    highlights = []

    def add_best(candidates, title, unit, higher, kind):
        if not candidates:
            return
        best = (max if higher else min)(value for row, value in candidates)
        for row, value in sorted(candidates, key=lambda item: item[0]['bib']):
            if value == best:
                highlights.append({
                    'title': title, 'unit': unit, 'value': value, 'kind': kind,
                    'name': row['name'], 'bib': row['bib'], 'category': row['category'],
                    'profile_url': row.get('profile_url', ''),
                })

    for index, station in enumerate(tests):
        candidates = []
        judge = station.get('scoring') == 'judge'
        for row in eligible:
            marks = row.get('marks', [])
            mark = marks[index] if index < len(marks) else {}
            value = mark.get('points' if judge else 'value')
            if mark.get('status') == 'done' and value is not None:
                candidates.append((row, value))
        add_best(candidates, station['name'], 'pts' if judge else station['unit'],
                 True if judge else station.get('higher', True), 'station')

    add_best([(row, row['total']) for row in eligible if row.get('completed', 0) > 0],
             'Mayor puntaje acumulado', 'pts', True, 'overall')
    return highlights
