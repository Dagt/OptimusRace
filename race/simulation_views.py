import mimetypes
from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .views import administrator
from .simulation_runtime import create, sessions, current, reset_captures, folder


@never_cache
@login_required
def index(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Coach').exists()):
        return HttpResponse(status=403)
    return render(request,'simulations.html',{'simulations':sessions(request.user)})


@require_POST
@administrator
def start(request, pk):
    try:
        meta=create(pk,request.user)
    except ValidationError as exc:
        messages.error(request,' '.join(exc.messages))
        return redirect('operations',pk=pk)
    return redirect(meta['prefix']+f'/events/{pk}/operations/')


@require_POST
@administrator
def control(request):
    meta=current.get()
    if not meta:raise Http404
    action=request.POST.get('action')
    if action=='finish':
        request.end_simulation=True
        return HttpResponse(status=204)
    if action=='reset':
        reset_captures(meta)
        messages.success(request,'Capturas reiniciadas en la copia. Puedes abrir las estaciones para practicar desde cero.')
        return redirect('operations',pk=meta['event'])
    return HttpResponse(status=400)


def media(request, name):
    meta=current.get()
    if not meta:raise Http404
    base=(folder(meta['token'])/'media').resolve()
    path=(base/name).resolve()
    if not path.is_relative_to(base) or not path.is_file():raise Http404
    return HttpResponse(path.read_bytes(),content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
