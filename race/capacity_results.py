"""Compatibility helpers: awards and tiebreaks belong only to overall categories."""
from .relative_scoring import tie_groups


def attach_capacity_results(event,rows):
    for row in rows:row.pop('capacity_results',None)


def capacity_boards(rows):
    return {}


def all_ties(rows):
    return tie_groups(rows)
