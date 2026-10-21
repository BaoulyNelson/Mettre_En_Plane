from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "prenom",
        "nom",
        "telephone",
        "numero_identite",
        "note_identite_verifiee",
    )
    search_fields = ("prenom", "nom", "telephone", "numero_identite")
    list_filter = ("note_identite_verifiee",)
