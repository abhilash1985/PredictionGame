from django.contrib.auth.decorators import login_required
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('', views.profile_view, name='profile'),
    path(
        'password/',
        login_required(views.CustomPasswordChangeView.as_view()),
        name='password_change',
    ),
]
