import os, secrets
import dj_database_url
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
if os.getenv('LOAD_DOTENV','1') == '1':
    load_dotenv(BASE_DIR / '.env', override=False)
DEBUG = os.getenv('DEBUG', '1') == '1'
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('Configura SECRET_KEY para producción')
    secret = BASE_DIR / '.local-secret'
    if not secret.exists(): secret.write_text(secrets.token_urlsafe(64))
    SECRET_KEY = secret.read_text()
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if h.strip()]
railway_domain=os.getenv('RAILWAY_PUBLIC_DOMAIN','').strip()
if railway_domain:ALLOWED_HOSTS.append(railway_domain)
if os.getenv('RAILWAY_ENVIRONMENT_ID'):ALLOWED_HOSTS.append('healthcheck.railway.app')
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'race']
MIDDLEWARE = ['optimus.proxy.WorkerProxyMiddleware','django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'optimus.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','race.context.navigation','race.context.site_brand']}}]
DATABASES = {'default':{'ENGINE':'django.db.backends.sqlite3','NAME':os.getenv('DATABASE_PATH',str(BASE_DIR/'db.sqlite3')),'OPTIONS':{'timeout':30,'transaction_mode':'IMMEDIATE'}}}
if os.getenv('DATABASE_URL'):
    DATABASES={'default':dj_database_url.parse(os.environ['DATABASE_URL'],conn_max_age=60,conn_health_checks=True)}
    if DATABASES['default']['ENGINE']!='django.db.backends.postgresql':
        raise ImproperlyConfigured('DATABASE_URL debe apuntar a PostgreSQL.')
    DATABASES['default'].setdefault('OPTIONS',{})['connect_timeout']=10
elif not DEBUG and os.getenv('ALLOW_SQLITE_PRODUCTION')!='1':
    raise ImproperlyConfigured('Configura DATABASE_URL para PostgreSQL en produccion.')
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR/'static']
STATIC_ROOT = BASE_DIR/'staticfiles'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(BASE_DIR/'media')))
MEDIA_URL = '/media/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
# Temporary provider hostnames are not our domains to submit for HSTS preload.
# Keep HSTS scoped to this host until the final domain/subdomain policy is defined.
SILENCED_SYSTEM_CHECKS = ['security.W005','security.W021']
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY','')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET','')
STRIPE_MODE = os.getenv('STRIPE_MODE','test')
ALLOW_LIVE_PAYMENTS = os.getenv('ALLOW_LIVE_PAYMENTS','0') == '1'
PUBLIC_URL = os.getenv('PUBLIC_URL','https://'+railway_domain if railway_domain else 'http://127.0.0.1:8000').rstrip('/')
if not DEBUG and urlparse(PUBLIC_URL).scheme!='https':raise ImproperlyConfigured('PUBLIC_URL debe usar HTTPS.')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST','localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT','587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL','Optimus Race <noreply@example.com>')
CSRF_TRUSTED_ORIGINS = [v for v in os.getenv('CSRF_TRUSTED_ORIGINS','').split(',') if v]
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS','1') == '1'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL','0') == '1'
SESSION_COOKIE_AGE = 60*60*12
DATA_UPLOAD_MAX_MEMORY_SIZE = 6*1024*1024
BACKUP_DIR = Path(os.getenv('BACKUP_DIR', str(BASE_DIR/'backups')))
STORAGES = {'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedStaticFilesStorage'}}

# Enable only behind a trusted proxy that replaces this header.
if os.getenv("TRUST_PROXY_SSL", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Private R2 bucket: signed URLs work before purchasing a public domain.
MEDIA_STORAGE=os.getenv('MEDIA_STORAGE','local')
if MEDIA_STORAGE=='r2':
    required=['R2_ENDPOINT_URL','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET_NAME']
    if any(not os.getenv(k) for k in required):raise ImproperlyConfigured('Faltan variables de almacenamiento R2.')
    STORAGES['default']={'BACKEND':'storages.backends.s3.S3Storage','OPTIONS':{
        'endpoint_url':os.environ['R2_ENDPOINT_URL'],'access_key':os.environ['R2_ACCESS_KEY_ID'],
        'secret_key':os.environ['R2_SECRET_ACCESS_KEY'],'bucket_name':os.environ['R2_BUCKET_NAME'],
        'region_name':'auto','signature_version':'s3v4','default_acl':None,
        'file_overwrite':False,'querystring_auth':True,'querystring_expire':3600,
        'object_parameters':{'CacheControl':'private, max-age=300'},
    }}
elif MEDIA_STORAGE!='local':raise ImproperlyConfigured('MEDIA_STORAGE debe ser local o r2.')
elif not DEBUG and os.getenv('ALLOW_LOCAL_MEDIA_PRODUCTION')!='1':
    raise ImproperlyConfigured('Configura MEDIA_STORAGE=r2 para conservar las fotos en produccion.')
if urlparse(PUBLIC_URL).hostname:
    ALLOWED_HOSTS.append(urlparse(PUBLIC_URL).hostname)
    if PUBLIC_URL.startswith('https://'):CSRF_TRUSTED_ORIGINS.append(PUBLIC_URL)
if railway_domain:CSRF_TRUSTED_ORIGINS.append('https://'+railway_domain)
SECURE_REDIRECT_EXEMPT=[r'^healthz/$']
WORKER_PROXY_SECRET=os.getenv('WORKER_PROXY_SECRET','')
WORKER_PUBLIC_HOST=os.getenv('WORKER_PUBLIC_HOST','')
if WORKER_PUBLIC_HOST:
    if len(WORKER_PROXY_SECRET)<32:raise ImproperlyConfigured('WORKER_PROXY_SECRET requiere al menos 32 caracteres.')
    if '/' in WORKER_PUBLIC_HOST or ':' in WORKER_PUBLIC_HOST:raise ImproperlyConfigured('WORKER_PUBLIC_HOST debe ser solo un hostname.')
    ALLOWED_HOSTS.append(WORKER_PUBLIC_HOST)
    CSRF_TRUSTED_ORIGINS.append('https://'+WORKER_PUBLIC_HOST)
PORTRAIT_MODEL_PATH=Path(os.getenv('PORTRAIT_MODEL_PATH',str(BASE_DIR/'.models'/'modnet.onnx')))
