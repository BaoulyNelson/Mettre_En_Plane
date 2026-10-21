from uuid import uuid4

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

from applications.comptes.validators import verifier_taille_image


class DemandeMiseEnGage(models.Model):
    class Statut(models.TextChoices):
        A_ETUDIER = "a_etudier", "À étudier"
        EN_COURS = "en_cours", "En cours d’étude"
        ACCEPTEE = "acceptee", "Acceptée, rendez-vous à confirmer"
        REFUSEE = "refusee", "Non retenue"
        CLOTUREE = "cloturee", "Clôturée"

    class Categorie(models.TextChoices):
        INFORMATIQUE = "informatique", "Informatique"
        TELEPHONE = "telephone", "Téléphone"
        ELECTRONIQUE = "electronique", "Électronique"
        AUTRE = "autre", "Autre"

    reference = models.CharField("Référence", max_length=16, unique=True, blank=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes_mise_en_gage",
    )
    telephone_contact = models.CharField("Téléphone de contact", max_length=30)
    categorie = models.CharField("Catégorie", max_length=20, choices=Categorie.choices)
    marque = models.CharField("Marque", max_length=100)
    modele = models.CharField("Modèle", max_length=120)
    numero_serie = models.CharField("Numéro de série", max_length=120, blank=True)
    description = models.TextField("État et description", max_length=1500)
    accessoires = models.CharField("Accessoires inclus", max_length=500, blank=True)
    appareil_deverrouille = models.BooleanField("Appareil déverrouillé", default=False)
    preuve_propriete = models.CharField(
        "Preuve de propriété disponible", max_length=180
    )
    montant_souhaite = models.DecimalField(
        "Montant souhaité",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    devise = models.CharField(
        "Devise",
        max_length=3,
        choices=[("HTG", "HTG"), ("USD", "USD")],
        default="HTG",
    )
    photo_bien = models.ImageField(
        "Photo du bien",
        upload_to="demandes/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            verifier_taille_image,
        ],
    )
    accepte_conditions = models.BooleanField(
        "J’accepte les conditions de traitement", default=False
    )
    statut = models.CharField(
        "Statut", max_length=12, choices=Statut.choices, default=Statut.A_ETUDIER
    )
    note_interne = models.TextField("Note de suivi interne", blank=True)
    cree_le = models.DateTimeField("Soumise le", auto_now_add=True)
    modifie_le = models.DateTimeField("Mise à jour le", auto_now=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "demande de mise en gage"
        verbose_name_plural = "demandes de mise en gage"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"DM-{uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} · {self.marque} {self.modele}"
