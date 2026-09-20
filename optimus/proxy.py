from secrets import compare_digest
from django.conf import settings


class WorkerProxyMiddleware:
    """Accept only the configured public host, authenticated by our Worker."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.META.pop('HTTP_X_OPTIMUS_PROXY_TOKEN', '')
        if (settings.WORKER_PUBLIC_HOST and settings.WORKER_PROXY_SECRET
                and compare_digest(token, settings.WORKER_PROXY_SECRET)):
            request.META['HTTP_HOST'] = settings.WORKER_PUBLIC_HOST
            request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
        return self.get_response(request)
