from django.contrib import admin

from .models import Contrat


@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "client",
        "bien",
        "capital_restant",
        "devise",
        "date_echeance",
        "statut",
    )
    search_fields = (
        "numero",
        "client__nom",
        "client__prenom",
        "bien__marque",
        "bien__modele",
    )
    list_filter = ("statut", "devise")
