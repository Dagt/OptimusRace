"""Smoke test of installation/startup with isolated data and an ephemeral port."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from urllib.error import URLError

root = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='optimus-startup-') as temporary:
    env = os.environ.copy()
    env.update(DATABASE_PATH=str(Path(temporary)/'startup.sqlite3'), DEBUG='1',
               SECRET_KEY='isolated-startup-check-not-for-production',
               STRIPE_SECRET_KEY='', STRIPE_WEBHOOK_SECRET='', ALLOWED_HOSTS='127.0.0.1,localhost')
    def run(*args):
        result = subprocess.run([sys.executable, str(root/'manage.py'), *args],
                                env=env, cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout
    run('migrate', '--noinput')
    run('seed_catalog')
    check_code = (
        'from django.core.management import call_command; '
        'from django.contrib.auth.models import User,Group; '
        'from race.models import Event,Registration,Exercise; '
        'call_command("seed_catalog"); call_command("seed_catalog"); '
        'assert (User.objects.count(),Event.objects.count(),Registration.objects.count())==(0,0,0); '
        'assert Group.objects.filter(name="Coach").count()==1; '
        'assert Exercise.objects.get(name="Press banca").base is None; '
        'print("PASS clean bootstrap: no users, events or entries; Coach group available")'
    )
    print(run('shell','-c',check_code).strip())
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1',0))
        port = reserve.getsockname()[1]
    with (Path(temporary)/'server.log').open('w+') as log:
        process = subprocess.Popen([sys.executable,str(root/'manage.py'),'runserver',f'127.0.0.1:{port}','--noreload'],cwd=root,env=env,stdout=log,stderr=log)
        try:
            for _ in range(50):
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(log.read())
                try:
                    with urlopen(f'http://127.0.0.1:{port}/',timeout=2) as response:
                        html = response.read().decode()
                        assert response.status == 200
                        assert 'Los eventos estarán aquí cuando se publiquen.' in html
                        break
                except URLError:
                    time.sleep(.2)
            else:
                raise RuntimeError('El servidor temporal no inició dentro del tiempo esperado.')
            print('PASS: clean migrations, idempotent technical catalog and empty-state HTTP 200.')
        finally:
            process.terminate()
            process.wait(timeout=10)
