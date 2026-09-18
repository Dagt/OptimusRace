from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from race import views as v
from race import participant_views as people
urlpatterns=[path('',v.home,name='home'),path('login/',v.signin,name='login'),path('signup/',people.retired,name='signup'),path('logout/',v.signout,name='logout'),path('profile/',v.profile,name='profile'),path('events/new/',v.event_edit,name='new_event'),path('events/<int:pk>/',v.event_detail,name='event'),path('events/<int:pk>/enroll/',people.retired,name='enroll'),path('events/<int:pk>/configure/',v.event_edit,name='configure'),path('events/<int:pk>/operations/',v.operations,name='operations'),path('events/<int:pk>/coach/',v.coach,name='coach'),path('events/<int:pk>/tv/',v.tv,name='tv'),path('events/<int:pk>/live/',v.live_data,name='live_data'),path('stripe/webhook/',v.webhook),path('admin/',admin.site.urls),path('reset/',v.RecoveryView.as_view(),name='password_reset'),path('reset/sent/',auth.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),name='password_reset_done'),path('reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),name='password_reset_confirm'),path('reset/complete/',auth.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),name='password_reset_complete')]
if settings.DEBUG: urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
urlpatterns += [path('participants/lookup/',people.retired,name='participant_lookup'),path('events/<int:pk>/status/',v.registration_status,name='registration_status'),path('events/<int:pk>/cancel-payment/',people.retired,name='cancel_payment')]
handler404='race.views.not_found'
handler500='race.views.server_error'

from race import management_views as management
urlpatterns += [path("team/",management.team,name="team"),path("team/new/",management.team_edit,name="team_new"),path("team/<int:pk>/",management.team_edit,name="team_edit"),path("catalog/",management.catalog,name="catalog"),path("catalog/new/",management.catalog_edit,name="catalog_new"),path("catalog/<int:pk>/",management.catalog_edit,name="catalog_edit")]

urlpatterns += [path('events/<int:pk>/quote/',v.price_quote,name='price_quote')]

urlpatterns += [path('events/<int:pk>/availability/',v.event_availability,name='event_availability'),path('participants/<int:pk>/photo/',people.edit_person,name='participant_photo')]

urlpatterns += [path('participants/',people.participants,name='participants'),path('participants/new/',people.participants,name='participant_new'),path('participants/<int:pk>/edit/',people.edit_person,name='participant_edit')]

urlpatterns += [path('profile/portrait-preview/',v.portrait_preview,name='portrait_preview')]

urlpatterns += [path('results/',people.public_search,name='public_search'),path('results/participants/<int:pk>/',people.public_profile,name='public_participant'),path('events/<int:pk>/register/',people.desk_register,name='desk_register')]

urlpatterns += [path('events/<int:pk>/tiebreaks/',v.coach_tiebreaks,name='coach_tiebreaks')]
