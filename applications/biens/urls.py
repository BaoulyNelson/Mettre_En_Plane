from django.urls import path

from . import views

app_name = "biens"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("nouveau/", views.creer, name="creer"),
]
