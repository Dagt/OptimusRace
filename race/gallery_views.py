from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .gallery import cleanup_files
from .gallery_forms import GalleryUploadForm
from .models import Audit, Event, EventPhoto
from .views import administrator


def visible_events(user):
    events = Event.objects.all()
    return events if user.is_superuser else events.exclude(status='draft')


@require_GET
def index(request):
    # One cover per album, rather than loading every full gallery into memory.
    covers = EventPhoto.objects.order_by('-created_at', '-pk')[:1]
    events = visible_events(request.user).annotate(photo_count=Count('gallery_photos'))
    if not request.user.is_superuser:
        events = events.filter(photo_count__gt=0)
    events = events.order_by('-date', '-pk').prefetch_related(
        Prefetch('gallery_photos', queryset=covers, to_attr='gallery_cover'))
    page = Paginator(events, 12).get_page(request.GET.get('page'))
    return render(request, 'gallery_index.html', {'page': page})


@require_GET
def album(request, pk):
    event = get_object_or_404(visible_events(request.user), pk=pk)
    page = Paginator(event.gallery_photos.all(), 24).get_page(request.GET.get('page'))
    return render(request, 'gallery_album.html', {'event': event, 'page': page})


@administrator
@require_http_methods(['GET', 'POST'])
def manage(request, pk):
    event = get_object_or_404(Event, pk=pk)
    form = GalleryUploadForm(request.POST if request.method == 'POST' else None,
                             request.FILES if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        stored = []
        try:
            with transaction.atomic():
                for upload in form.cleaned_data['photos']:
                    photo = EventPhoto.objects.create(event=event, image=upload,
                        caption=form.cleaned_data['caption'], uploaded_by=request.user)
                    stored.extend([(photo.image.storage, photo.image.name),
                                   (photo.thumbnail.storage, photo.thumbnail.name)])
                Audit.objects.create(event=event, actor=request.user, action='gallery_uploaded',
                                     details={'count': len(form.cleaned_data['photos'])})
        except (ValidationError, OSError) as exc:
            cleanup_files(stored)
            form.add_error(None, exc if isinstance(exc, ValidationError) else
                           'No se pudieron guardar las fotos. Intenta de nuevo.')
        except Exception:
            cleanup_files(stored)
            raise
        else:
            messages.success(request, 'Fotos guardadas con la marca de agua de Appex.')
            return redirect('gallery_manage', pk=event.pk)
    page = Paginator(event.gallery_photos.all(), 24).get_page(request.GET.get('page'))
    return render(request, 'gallery_manage.html', {'event': event, 'page': page, 'form': form})


@administrator
@require_POST
def delete(request, pk, photo_pk):
    with transaction.atomic():
        photo = get_object_or_404(EventPhoto.objects.select_for_update(), pk=photo_pk, event_id=pk)
        files = [(photo.image.storage, photo.image.name), (photo.thumbnail.storage, photo.thumbnail.name)]
        Audit.objects.create(event=photo.event, actor=request.user, action='gallery_deleted',
                             details={'photo': photo.pk, 'caption': photo.caption})
        photo.delete()
        transaction.on_commit(lambda: cleanup_files(files))
    messages.success(request, 'Foto eliminada de la galería.')
    return redirect('gallery_manage', pk=pk)
