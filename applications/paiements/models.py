from django.db import models

from applications.contrats.models import Contrat


class Paiement(models.Model):
    class Type(models.TextChoices):
        INTERET = "interet", "Intérêts et prolongation"
        ACOMPTE = "acompte", "Intérêts + acompte capital"
        SOLDE = "solde", "Rachat complet"

    contrat = models.ForeignKey(
        Contrat, on_delete=models.PROTECT, related_name="paiements"
    )
    type = models.CharField("Type", max_length=10, choices=Type.choices)
    montant = models.DecimalField("Montant reçu", max_digits=12, decimal_places=2)
    devise_recue = models.CharField(
        "Devise reçue",
        max_length=3,
        choices=[("HTG", "HTG"), ("USD", "USD")],
        default="HTG",
    )
    taux_change = models.DecimalField(
        "Taux HTG par USD", max_digits=12, decimal_places=4, default=1
    )
    montant_interet = models.DecimalField(
        "Intérêts", max_digits=12, decimal_places=2, default=0
    )
    montant_capital = models.DecimalField(
        "Capital remboursé", max_digits=12, decimal_places=2, default=0
    )
    recu_le = models.DateTimeField("Reçu le", auto_now_add=True)
    note = models.CharField("Note", max_length=200, blank=True)

    class Meta:
        ordering = ["-recu_le"]
        verbose_name = "paiement"
        verbose_name_plural = "paiements"

    def __str__(self):
        return f"{self.contrat.numero} · {self.montant} {self.devise_recue}"
