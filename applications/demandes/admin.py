from django.contrib import admin

from .models import DemandeMiseEnGage


@admin.register(DemandeMiseEnGage)
class DemandeMiseEnGageAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "utilisateur",
        "marque",
        "modele",
        "montant_souhaite",
        "devise",
        "statut",
        "cree_le",
    )
    search_fields = ("reference", "utilisateur__username", "marque", "modele")
    list_filter = ("statut", "devise", "cree_le")
    readonly_fields = ("reference", "cree_le", "modifie_le")
