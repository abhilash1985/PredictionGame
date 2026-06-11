from django.urls import path

from apps.tournaments import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('privacy/', views.privacy_policy_view, name='privacy'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
]
