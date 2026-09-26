"""Private event snapshots on disposable SQLite files, never on the production DB.

The synchronous request owns a thread-local connection for its entire view/render.
The production connection is restored before session middleware saves anything.
"""
import json
import shutil
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timedelta, timezone as datetime_timezone
from django.utils import timezone

from django.conf import settings
from django.core import serializers
from django.core.exceptions import ValidationError
from django.db import connections, transaction
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.migrations.executor import MigrationExecutor
from django.contrib.auth.models import User, Group
from . import models as m

current = ContextVar('simulation', default=None)
_locks = {}
_guard = threading.RLock()
_creation_lock = threading.Lock()


def root():
    path = Path(settings.SIMULATION_ROOT).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def folder(token):
    # Only UUID filenames under our own temporary root are accepted.
    return root() / str(uuid.UUID(str(token)))


def lock(token):
    with _guard:
        return _locks.setdefault(str(token), threading.RLock())


def metadata(token):
    try:
        return json.loads((folder(token) / 'session.json').read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return None


def remove(token):
    with lock(token):
        path = folder(token).resolve()
        if path.parent != root() or path.is_symlink():
            raise ValueError('Invalid simulation directory')
        if path.exists():
            shutil.rmtree(path)


def cleanup():
    for path in root().iterdir():
        if not path.is_dir():
            continue
        try:
            token = str(uuid.UUID(path.name))
        except ValueError:
            continue
        with lock(token):
            meta = metadata(token)
            if meta and meta['expires'] <= time.time():
                remove(token)


def sessions(user):
    cleanup()
    found = []
    for path in root().iterdir():
        try:
            meta = metadata(path.name)
        except ValueError:
            continue
        if meta and (user.is_superuser or user.pk in meta['users']):
            found.append(meta)
    return sorted(found, key=lambda item: item['created'], reverse=True)


@contextmanager
def database(meta):
    previous = connections['default']
    config = deepcopy(previous.settings_dict)
    config.update(ENGINE='django.db.backends.sqlite3', NAME=str(folder(meta['token']) / 'practice.sqlite3'),
                  OPTIONS={'timeout': 30, 'transaction_mode': 'IMMEDIATE'}, CONN_MAX_AGE=0,
                  USER='', PASSWORD='', HOST='', PORT='', ATOMIC_REQUESTS=False)
    connection = DatabaseWrapper(config, alias='default')
    context_token = current.set(meta)
    connections['default'] = connection
    try:
        yield connection
    finally:
        try:
            connection.close()
        finally:
            connections['default'] = previous
            current.reset(context_token)


def create(event_id, actor):
    if current.get() or not actor.is_superuser:
        raise ValidationError('Solo administración puede crear una simulación del evento original.')
    with _creation_lock:
        cleanup()
        if len(sessions(actor)) >= 8:
            raise ValidationError('Termina una simulación antes de crear otra (máximo 8 simultáneas).')
        token = str(uuid.uuid4())
        with transaction.atomic():
            event = m.Event.objects.select_for_update().get(pk=event_id)
            entries = list(m.Registration.objects.filter(event=event))
            people = list(m.Participant.objects.filter(pk__in=[r.participant_id for r in entries]))
            users = list(User.objects.all())
            allowed = [u.pk for u in users if u.is_active and (u.is_superuser or u.groups.filter(name='Coach').exists())]
            objects = [*Group.objects.all(), *users,
                       *m.Profile.objects.filter(user_id__in=[u.pk for u in users]),
                       *m.AccountName.objects.all(), *m.Exercise.objects.all(),
                       *people, event, *entries,
                       *m.Result.objects.filter(registration__event=event),
                       *m.Payment.objects.filter(registration__event=event),
                       *m.Audit.objects.filter(event=event), *m.TieBreak.objects.filter(event=event),
                       *m.TieBreakRound.objects.filter(event=event),
                       *m.TieBreakMark.objects.filter(round__event=event),
                       *m.TieBreakMatch.objects.filter(round__event=event),
                       *m.EventStation.objects.filter(event=event), *m.CoachAssignment.objects.filter(event=event)]
            data = json.loads(serializers.serialize('json', objects))
            for row in data:
                if row['model'] == 'auth.user':
                    row['fields']['password'] = '!simulation-no-login'
                    row['fields']['user_permissions'] = []
                if row['model'] == 'auth.group':
                    row['fields']['permissions'] = []
                if row['model'] == 'race.payment':
                    row['fields'].update(session_id=None, url='', livemode=False)
            meta = dict(token=token, event=event.pk, name=event.name, owner=actor.pk, users=allowed,
                        created=time.time(), expires=time.time()+24*3600,
                        prefix=f'/simulations/{token}', participants=len(entries))
        with lock(token):
            folder(token).mkdir()
            try:
                with database(meta) as connection:
                    executor = MigrationExecutor(connection)
                    executor.migrate(executor.loader.graph.leaf_nodes())
                    with connection.constraint_checks_disabled(), transaction.atomic():
                        for row in serializers.deserialize('json', json.dumps(data)):
                            row.save()
                    connection.check_constraints()
                    activate_calendar(meta)
                (folder(token)/'session.json').write_text(json.dumps(meta), encoding='utf-8')
            except Exception:
                remove(token)
                raise
        return meta


def activate_calendar(meta):
    """Move only the disposable calendar to now; retain relative price windows."""
    from .event_policy import instant
    event = m.Event.objects.get(pk=meta['event'])
    now = timezone.now()
    start = now - timedelta(minutes=1)
    offset = start - event.date
    rules = deepcopy(event.rules)
    for key in ['registration_start', 'reception_start', 'reception_end', 'event_end']:
        if rules.get(key):
            rules[key] = (instant(rules[key]) + offset).isoformat()
    for key in ['price_tiers', 'discounts']:
        for item in rules.get(key, []):
            for boundary in ['start', 'end']:
                if item.get(boundary):
                    item[boundary] = (instant(item[boundary]) + offset).isoformat()
    # Practice remains usable for the lifetime of the copy, even for a past event.
    expiry = datetime.fromtimestamp(meta['expires'], tz=datetime_timezone.utc)
    rules['reception_start'] = start.isoformat()
    rules['reception_end'] = expiry.isoformat()
    rules['event_end'] = expiry.isoformat()
    event.date = start
    event.registration_end += offset
    event.rules = rules
    event.save(update_fields=['date', 'registration_end', 'rules'])


def reset_captures(meta):
    """Restart only the snapshot. Rules, people and prices stay unchanged; refresh the practice calendar."""
    with transaction.atomic():
        m.TieBreakMark.objects.all().delete()
        m.TieBreakMatch.objects.all().delete()
        m.TieBreakRound.objects.all().delete()
        m.TieBreak.objects.all().delete()
        m.Result.objects.all().delete()
        m.Event.objects.filter(pk=meta['event']).update(status='open', final_board=[], closed_at=None,
            active_test=0, active_batch=1, station_capture_closed=False)
        m.EventStation.objects.all().update(is_open=False, opened=False, revision=0)
        m.Registration.objects.all().update(attendance='pending', revision=0)
        activate_calendar(meta)
        m.Audit.objects.create(event_id=meta['event'], actor_id=meta['owner'], action='simulation_reset', details={})


def start_cleanup_worker():
    # Single-process deployment; no persistent volume. New releases discard practice data.
    def run():
        while True:
            try:
                cleanup()
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Simulation cleanup failed')
            time.sleep(60)
    threading.Thread(target=run, name='simulation-cleanup', daemon=True).start()
