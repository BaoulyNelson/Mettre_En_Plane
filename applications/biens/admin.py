from django.contrib import admin

from .models import Bien


@admin.register(Bien)
class BienAdmin(admin.ModelAdmin):
    list_display = ("marque", "modele", "client", "categorie", "etat", "cree_le")
    search_fields = (
        "marque",
        "modele",
        "numero_serie",
        "client__nom",
        "client__prenom",
    )
    list_filter = ("categorie", "etat")
