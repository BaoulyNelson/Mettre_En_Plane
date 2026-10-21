from django.urls import path

from . import views

app_name = "inventaire"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("<int:article_id>/vendre/", views.vendre, name="vendre"),
]
