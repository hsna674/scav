from django.contrib.auth import logout
from django.shortcuts import redirect, render


def index_view(request):
    if request.user.is_authenticated:
        return redirect("main:index")
    else:
        return redirect("auth:login")


def login_view(request):
    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("auth:index")
