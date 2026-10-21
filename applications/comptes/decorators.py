from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def personnel_requis(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "connexion")
        if not request.user.is_staff:
            return redirect("demandes:espace")
        return view(request, *args, **kwargs)

    return wrapper


def client_requis(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "connexion")
        if request.user.is_staff:
            return redirect("tableau_de_bord:accueil")
        return view(request, *args, **kwargs)

    return wrapper
