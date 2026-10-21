from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from .validators import verifier_taille_image


class ProfilUtilisateur(models.Model):
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profil",
    )
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    photo = models.ImageField(
        "Photo de profil",
        upload_to="profils/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            verifier_taille_image,
        ],
    )

    class Meta:
        verbose_name = "profil utilisateur"
        verbose_name_plural = "profils utilisateurs"

    def __str__(self):
        return f"Profil de {self.utilisateur.get_username()}"


class ConfigurationSite(models.Model):
    nom = models.CharField("Nom du site", max_length=100, default="Mete nan plàn")
    slogan = models.CharField("Slogan", max_length=180, blank=True)
    logo = models.ImageField(
        "Logo",
        upload_to="identite/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            verifier_taille_image,
        ],
    )
    adresse = models.CharField("Adresse", max_length=240, blank=True)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    email = models.EmailField("Adresse courriel", blank=True)
    modifie_le = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        verbose_name = "identité du site"
        verbose_name_plural = "identité du site"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom
