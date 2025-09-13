from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("validate/", views.validate_flag, name="validate_flag"),
    path("support/", views.support, name="support"),
    path("toggledark/", views.dark_mode, name="toggledark"),
    path("move-challenge-up/", views.move_challenge_up, name="move_challenge_up"),
    path("move-challenge-down/", views.move_challenge_down, name="move_challenge_down"),
]
