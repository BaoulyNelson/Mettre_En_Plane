from django.contrib import admin

from .models import ArticleRevente


@admin.register(ArticleRevente)
class ArticleReventeAdmin(admin.ModelAdmin):
    list_display = (
        "bien",
        "contrat",
        "prix_liquidation",
        "prix_vente",
        "transfert_le",
        "vendu_le",
    )
    list_filter = ("vendu_le",)
    search_fields = ("bien__marque", "bien__modele", "contrat__numero")
