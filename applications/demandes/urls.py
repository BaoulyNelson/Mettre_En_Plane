from django.urls import path

from . import views

app_name = "demandes"
urlpatterns = [
    path("mon-espace/", views.espace, name="espace"),
    path("mise-en-gage/nouvelle/", views.creer, name="creer"),
    path("mon-espace/<str:reference>/", views.detail_client, name="detail"),
    path("gestion/demandes/", views.liste_personnel, name="liste_personnel"),
    path("gestion/demandes/<str:reference>/", views.traiter, name="traiter"),
]
