"""Integration check against a disposable file database, never the user's DB."""
import os, tempfile, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
with tempfile.TemporaryDirectory(prefix='optimus-concurrency-') as tmp:
    os.environ['DATABASE_PATH']=str(Path(tmp)/'test.sqlite3')
    os.environ['DJANGO_SETTINGS_MODULE']='optimus.settings'
    subprocess.run([sys.executable,str(root/'manage.py'),'migrate','--noinput'],check=True,capture_output=True)
    import django
    django.setup()
    from concurrent.futures import ThreadPoolExecutor
    from django.db import connections,close_old_connections
    from django.utils import timezone
    from django.contrib.auth.models import User
    from django.core.exceptions import ValidationError
    from race.models import Event,Profile,Registration
    from race.services import cash_register
    admin=User.objects.create(username='admin',is_superuser=True)
    users=[]
    for i in range(8):
        u=User.objects.create(username=f'atleta{i}',first_name=f'Atleta {i}');Profile.objects.create(user=u,sex='M');users.append(u.id)
    e=Event.objects.create(name='Concurrent test',date=timezone.now(),registration_end=timezone.now()+timezone.timedelta(days=1),capacity=1,price=50000,status='open')
    def compete(uid):
        close_old_connections()
        try:
            cash_register(e.id,User.objects.get(pk=uid),User.objects.get(pk=admin.id),50000)
            return 'confirmed'
        except ValidationError: return 'full'
        finally: connections.close_all()
    with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(compete,users))
    assert results.count('confirmed')==1,results
    assert Registration.objects.count()==1
    connections.close_all()
    print('PASS: 8 concurrent registrations, 1 seat, exactly 1 confirmed.')
