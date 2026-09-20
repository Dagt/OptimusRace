from django.db import connection, DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_safe
from django.views.decorators.cache import never_cache


@never_cache
@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM race_event LIMIT 1')
        return JsonResponse({'status': 'ok'})
    except DatabaseError:
        return JsonResponse({'status': 'unavailable'}, status=503)
