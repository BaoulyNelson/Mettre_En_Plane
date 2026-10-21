from django.db import models

from applications.biens.models import Bien
from applications.contrats.models import Contrat


class ArticleRevente(models.Model):
    bien = models.OneToOneField(
        Bien, on_delete=models.PROTECT, related_name="article_revente"
    )
    contrat = models.ForeignKey(
        Contrat, on_delete=models.PROTECT, related_name="articles_revente"
    )
    prix_liquidation = models.DecimalField(
        "Prix de liquidation", max_digits=12, decimal_places=2
    )
    prix_vente = models.DecimalField(
        "Prix de vente", max_digits=12, decimal_places=2, blank=True, null=True
    )
    transfert_le = models.DateTimeField("Transféré le", auto_now_add=True)
    vendu_le = models.DateTimeField("Vendu le", blank=True, null=True)

    class Meta:
        ordering = ["-transfert_le"]
        verbose_name = "article à revendre"
        verbose_name_plural = "inventaire de revente"

    @property
    def vendu(self):
        return self.vendu_le is not None

    def __str__(self):
        return str(self.bien)
