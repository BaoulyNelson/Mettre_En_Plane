from django.urls import path

from . import views

app_name = "contrats"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("nouveau/", views.creer, name="creer"),
    path("biens-disponibles/", views.biens_disponibles, name="biens_disponibles"),
    path("<int:contrat_id>/", views.detail, name="detail"),
    path(
        "<int:contrat_id>/document.pdf",
        views.telecharger_document_contrat,
        name="document",
    ),
    path(
        "<int:contrat_id>/document.pdf",
        views.telecharger_document_contrat,
        name="document",
    ),
    path(
        "<int:contrat_id>/paiements/<int:paiement_id>/recu.pdf",
        views.telecharger_recu,
        name="recu",
    ),
    path("<int:contrat_id>/paiement/", views.payer, name="payer"),
    path("<int:contrat_id>/saisir/", views.saisir, name="saisir"),
]
