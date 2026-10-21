from django.contrib import admin

from .models import Paiement


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = (
        "contrat",
        "type",
        "montant",
        "montant_interet",
        "montant_capital",
        "recu_le",
    )
    list_filter = ("type", "recu_le")
    search_fields = ("contrat__numero", "contrat__client__nom")
