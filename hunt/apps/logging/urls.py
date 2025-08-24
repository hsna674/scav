from django.urls import path
from . import views

app_name = "logging"

urlpatterns = [
    path("dashboard/", views.activity_dashboard, name="dashboard"),
    path("submissions/", views.flag_submissions, name="flag_submissions"),
    path(
        "challenge/<int:challenge_id>/submissions/",
        views.challenge_submissions,
        name="challenge_submissions",
    ),
    path("user/<int:user_id>/activity/", views.user_activity, name="user_activity"),
    path("leaderboard/", views.class_leaderboard, name="class_leaderboard"),
    path("realtime/", views.real_time_activity, name="real_time_activity"),
]
