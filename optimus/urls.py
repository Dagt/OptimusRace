from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from race import views as v
urlpatterns=[path('',v.home,name='home'),path('login/',v.signin,name='login'),path('signup/',v.signup,name='signup'),path('logout/',v.signout,name='logout'),path('profile/',v.profile,name='profile'),path('events/new/',v.event_edit,name='new_event'),path('events/<int:pk>/',v.event_detail,name='event'),path('events/<int:pk>/enroll/',v.enroll,name='enroll'),path('events/<int:pk>/configure/',v.event_edit,name='configure'),path('events/<int:pk>/operations/',v.operations,name='operations'),path('events/<int:pk>/coach/',v.coach,name='coach'),path('events/<int:pk>/tv/',v.tv,name='tv'),path('events/<int:pk>/live/',v.live_data,name='live_data'),path('stripe/webhook/',v.webhook),path('admin/',admin.site.urls),path('reset/',v.RecoveryView.as_view(),name='password_reset'),path('reset/sent/',auth.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),name='password_reset_done'),path('reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),name='password_reset_confirm'),path('reset/complete/',auth.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),name='password_reset_complete')]
if settings.DEBUG: urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
urlpatterns += [path('participants/lookup/',v.participant_lookup,name='participant_lookup'),path('events/<int:pk>/status/',v.registration_status,name='registration_status'),path('events/<int:pk>/cancel-payment/',v.cancel_payment,name='cancel_payment')]
handler404='race.views.not_found'
handler500='race.views.server_error'

from race import management_views as management
urlpatterns += [path("team/",management.team,name="team"),path("team/new/",management.team_edit,name="team_new"),path("team/<int:pk>/",management.team_edit,name="team_edit"),path("catalog/",management.catalog,name="catalog"),path("catalog/new/",management.catalog_edit,name="catalog_new"),path("catalog/<int:pk>/",management.catalog_edit,name="catalog_edit")]

urlpatterns += [path('events/<int:pk>/quote/',v.price_quote,name='price_quote')]
