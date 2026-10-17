"""Production server entry point. Migrations run once in Railway pre-deploy."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'optimus.settings')
os.environ.setdefault('DEBUG', '0')
from optimus.wsgi import application
from waitress import serve

if __name__ == '__main__':
    from race.simulation_runtime import start_cleanup_worker
    start_cleanup_worker()
    serve(application, host='0.0.0.0', port=int(os.getenv('PORT', '8000')),
          threads=int(os.getenv('WEB_THREADS', '4')),
          # Gallery batches allow 100 MiB of files plus multipart form overhead.
          max_request_body_size=101 * 1024 * 1024,
          trusted_proxy='*', trusted_proxy_count=1,
          trusted_proxy_headers={'x-forwarded-proto'})
