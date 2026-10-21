from django.urls import path

from . import views

app_name = "tableau_de_bord"
urlpatterns = [path("", views.accueil, name="accueil")]
