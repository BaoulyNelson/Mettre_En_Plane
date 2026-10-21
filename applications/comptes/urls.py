from django.urls import path

from . import views

app_name = "comptes"
urlpatterns = [
    path("inscription/", views.inscription, name="inscription"),
    path("profil/", views.profil, name="profil"),
    path("site/", views.configurer_site, name="site"),
    path("nouveau/", views.creer, name="creer"),
]
