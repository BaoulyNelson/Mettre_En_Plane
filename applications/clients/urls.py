from django.urls import path

from . import views

app_name = "clients"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("nouveau/", views.creer, name="creer"),
    path(
        "<int:client_id>/associer-compte/",
        views.associer_compte,
        name="associer_compte",
    ),
    path("<int:client_id>/", views.detail, name="detail"),
]
