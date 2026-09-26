import re
import time
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import get_script_prefix, set_script_prefix, resolve, Resolver404
from django.utils.cache import patch_cache_control
from .simulation_runtime import metadata, lock, database, remove

PREFIX = re.compile(r'^/simulations/([0-9a-f-]{36})(/.*)$')
ALLOWED = {'home','event','operations','configure','event_information','coach','tv','live_data',
           'participants','participant_new','participant_edit','participant_photo','event_availability',
           'price_quote','coach_tiebreaks','coach_feed','public_search','public_participant',
           'portrait_preview','team','catalog','catalog_new','catalog_edit','desk_register',
           'simulation_control','simulation_media'}


def scoped_url(url, prefix):
    if not url.startswith('/') or url.startswith(('//','/static/','/media/','/simulations/')):
        return url
    return prefix + url


class SimulationMiddleware:
    def __init__(self, get_response):self.get_response=get_response

    def __call__(self, request):
        match = PREFIX.match(request.path_info)
        if not match:return self.get_response(request)
        response = self.simulation_response(request, match)
        response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        patch_cache_control(response, private=True, no_store=True)
        return response

    def simulation_response(self, request, match):
        token, inner = match.groups()
        # Resolve real authentication before swapping the thread-local DB connection.
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not user.is_active or not (user.is_superuser or user.groups.filter(name='Coach').exists()):
            return HttpResponse('Simulación privada.', status=403)
        user_id, admin = user.pk, user.is_superuser
        with lock(token):
            meta = metadata(token)
            if not meta or meta['expires'] <= time.time():
                if meta:remove(token)
                return HttpResponse('Esta simulación terminó o caducó. Regresa al panel de simulaciones.', status=410)
            if not admin and user_id not in meta['users']:
                return HttpResponse('No tienes acceso a esta simulación.',status=403)
            try:route = resolve(inner)
            except Resolver404:return HttpResponse(status=404)
            if route.url_name not in ALLOWED:
                return HttpResponse('Esta acción no está disponible dentro de la simulación. Usa Salir de simulación para volver al sistema real.',status=403)
            if request.method == 'POST' and request.POST.get('action') == 'duplicate':
                return HttpResponse('Crea las simulaciones desde el evento original.',status=403)
            prefix = get_script_prefix()
            original_path = request.path_info
            request.simulation = meta
            request.path_info = inner
            set_script_prefix(meta['prefix'] + '/')
            try:
                with database(meta):
                    copied_user = User.objects.filter(pk=user_id).first()
                    if not copied_user:return HttpResponse('Crea otra simulación para incluir esta cuenta.',status=403)
                    request.user = copied_user
                    response = self.get_response(request)
                    if response.has_header('Location'):
                        response['Location'] = scoped_url(response['Location'],meta['prefix'])
                    if not response.streaming and response.get('Content-Type','').startswith('text/html'):
                        html = response.content.decode(response.charset)
                        # Legacy hard-coded internal URLs must remain inside the snapshot too.
                        html = re.sub(r'((?:href|action|data-[\w-]+)=["\'])(/[^"\']*)(["\'])',
                                      lambda m: m[1]+scoped_url(m[2],meta['prefix'])+m[3], html)
                        # Only this marked link can leave the snapshot.
                        html = html.replace('href="'+meta['prefix']+'/simulation-exit/"','href="/simulations/"')
                        response.content = html.encode(response.charset)
            finally:
                request.user = user
                request.path_info = original_path
                set_script_prefix(prefix)
            if getattr(request,'end_simulation',False):
                remove(token)
                return HttpResponseRedirect('/simulations/')
            return response
