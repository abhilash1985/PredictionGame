from django.urls import path

from apps.leaderboard import views

urlpatterns = [
    path('', views.leaderboard_view, name='leaderboard'),
    path('teams/', views.team_points_view, name='team_points'),
    path('match-points/', views.match_points_view, name='match_points'),
    path('graphs/', views.prediction_graph_view, name='prediction_graph'),
]
