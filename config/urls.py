from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('apps.tournaments.urls')),
    path('matches/', include('apps.matches.urls')),
    path('profile/', include('apps.accounts.urls')),
    path('leaderboard/', include('apps.leaderboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
