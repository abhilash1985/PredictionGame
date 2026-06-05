from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('', views.profile_view, name='profile'),
    path(
        'password/',
        login_required(PasswordChangeView.as_view(
            template_name='accounts/password_change.html',
            success_url='/profile/',
        )),
        name='password_change',
    ),
]
