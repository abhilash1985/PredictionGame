from django.urls import path

from apps.matches import views

urlpatterns = [
    path('', views.match_list_view, name='match_list'),
    path('<int:pk>/squad/', views.match_squad_view, name='match_squad'),
    path('<int:pk>/predict/', views.predict_view, name='match_predict'),
    path('<int:pk>/admin-score/', views.admin_score_match_view, name='admin_score_match'),
    path('<int:pk>/admin-predict/<int:user_id>/', views.admin_predict_for_user_view, name='admin_predict_for_user'),
]
