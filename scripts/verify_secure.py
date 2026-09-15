"""Validate secure Django settings and WhiteNoise locally; no external services."""
import os,secrets,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
env=os.environ.copy();env.update(DEBUG='0',SECRET_KEY=secrets.token_urlsafe(64),ALLOWED_HOSTS='testserver',STRIPE_MODE='test',ALLOW_LIVE_PAYMENTS='0',STRIPE_SECRET_KEY='',STRIPE_WEBHOOK_SECRET='')
code='''from django.test import Client
c=Client()
for path in ['/','/login/','/static/design.css','/static/vendor/chart.umd.min.js','/static/images/campaign.png']:
    r=c.get(path,secure=True)
    assert r.status_code==200,(path,r.status_code)
    r.close()
assert c.get('/missing-validation-page/',secure=True).status_code==404
assert c.get('/').status_code==301
print('PASS secure pages, friendly 404, HTTPS redirect and local static assets.')
'''
result=subprocess.run([sys.executable,'manage.py','shell','-c',code],cwd=root,env=env,capture_output=True,text=True)
print(result.stdout);print(result.stderr);sys.exit(result.returncode)
