from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import models
from django.utils import timezone

from applications.biens.models import Bien
from applications.clients.models import Client


class Contrat(models.Model):
    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        SOLDE = "solde", "Racheté"
        SAISI = "saisi", "Saisi"

    numero = models.CharField("Numéro", max_length=24, unique=True, blank=True)
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="contrats"
    )
    bien = models.ForeignKey(Bien, on_delete=models.PROTECT, related_name="contrats")
    capital_initial = models.DecimalField(
        "Capital prêté", max_digits=12, decimal_places=2
    )
    capital_restant = models.DecimalField(
        "Capital restant", max_digits=12, decimal_places=2
    )
    devise = models.CharField(
        "Devise", max_length=3, choices=[("HTG", "HTG"), ("USD", "USD")], default="HTG"
    )
    taux_mensuel = models.DecimalField(
        "Taux mensuel (%)", max_digits=5, decimal_places=2, default=15
    )
    duree_jours = models.PositiveSmallIntegerField("Durée initiale (jours)", default=30)
    jours_de_grace = models.PositiveSmallIntegerField(
        "Délai de grâce (jours)", default=5
    )
    date_debut = models.DateField("Date de début", default=timezone.localdate)
    date_echeance = models.DateField("Échéance", blank=True, null=True)
    statut = models.CharField(
        "Statut", max_length=12, choices=Statut.choices, default=Statut.ACTIF
    )
    cree_le = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        ordering = ["date_echeance", "-cree_le"]
        verbose_name = "contrat"
        verbose_name_plural = "contrats"

    def save(self, *args, **kwargs):
        if not self.date_echeance:
            self.date_echeance = self.date_debut + timedelta(days=self.duree_jours)
        if self._state.adding and not self.capital_restant:
            self.capital_restant = self.capital_initial
        if not self.numero:
            self.numero = f"PL-{timezone.localdate():%y%m%d}-{uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    @property
    def interet_mensuel(self):
        return (self.capital_restant * self.taux_mensuel / 100).quantize(
            Decimal("0.01")
        )

    @property
    def montant_rachat_estime(self):
        if self.statut != self.Statut.ACTIF:
            return Decimal("0.00")
        return self.capital_restant + self.interet_mensuel

    @property
    def en_retard(self):
        return (
            self.statut == self.Statut.ACTIF
            and timezone.localdate()
            > self.date_echeance + timedelta(days=self.jours_de_grace)
        )

    @property
    def echeance_proche(self):
        aujourd_hui = timezone.localdate()
        return (
            self.statut == self.Statut.ACTIF
            and aujourd_hui <= self.date_echeance <= aujourd_hui + timedelta(days=3)
        )

    def __str__(self):
        return self.numero


class RappelContrat(models.Model):
    class Type(models.TextChoices):
        ECHEANCE_PROCHE = "echeance_proche", "Échéance dans trois jours"
        FIN_GRACE = "fin_grace", "Fin du délai de grâce"

    contrat = models.ForeignKey(
        Contrat,
        on_delete=models.CASCADE,
        related_name="rappels",
    )
    type = models.CharField("Type de rappel", max_length=20, choices=Type.choices)
    date_echeance = models.DateField("Échéance du contrat")
    destinataire = models.EmailField("Adresse destinataire")
    envoye_le = models.DateTimeField("Envoyé le", auto_now_add=True)

    class Meta:
        ordering = ["-envoye_le"]
        verbose_name = "rappel de contrat"
        verbose_name_plural = "rappels de contrat"
        constraints = [
            models.UniqueConstraint(
                fields=["contrat", "type", "date_echeance"],
                name="uniq_rappel_contrat_type_echeance",
            )
        ]
