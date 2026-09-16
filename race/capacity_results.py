"""Independent capacity standings, using the existing station points."""
from copy import deepcopy
from .relative_scoring import apply_tiebreaks,tie_groups

def attach_capacity_results(event,rows):
    if not event.rules.get('capacity_podiums'):return
    capacities=list(dict.fromkeys(t['capacity'] for t in event.rules['tests']))
    for row in rows:row['capacity_results']={}
    for capacity in capacities:
        entries=[]
        for row in rows:
            marks=[deepcopy(m) for m in row['marks'] if m['capacity']==capacity]
            complete=bool(marks) and all(m['status']=='done' and m['points'] is not None for m in marks)
            entry={key:row[key] for key in ['id','name','bib','category','attendance']}
            entry.update(marks=marks,total=round(sum(m['points'] or 0 for m in marks),4),maximum=sum(m['max_points'] for m in marks),
                         completed=sum(m['status']=='done' for m in marks),test_count=len(marks),eligible=complete and row['attendance']!='disqualified' and row['category']!='Sin pesaje',
                         rank=None,tie_pending=False,provisional=True,winner=False)
            entries.append(entry)
        for entry in entries:
            if entry['eligible']:entry['rank']=1+sum(other['eligible'] and other['category']==entry['category'] and other['total']>entry['total'] for other in entries)
        apply_tiebreaks(event,entries,capacity)
        for row,entry in zip(rows,entries):row['capacity_results'][capacity]=entry

def capacity_boards(rows):
    boards={}
    for row in rows:
        for capacity,entry in row.get('capacity_results',{}).items():boards.setdefault(capacity,[]).append(entry)
    for entries in boards.values():entries.sort(key=lambda r:(r['rank'] is None,r['category'],r['rank'] or 0,r['bib']))
    return boards

def all_ties(rows):
    groups=tie_groups(rows)
    for capacity,entries in capacity_boards(rows).items():groups.extend(tie_groups(entries,capacity))
    return groups
