from django.conf import settings
from django.db import models


class Client(models.Model):
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dossier_client",
        verbose_name="Compte client",
    )
    nom = models.CharField("Nom", max_length=100)
    prenom = models.CharField("Prénom", max_length=100)
    telephone = models.CharField("Téléphone", max_length=30)
    email = models.EmailField("Courriel", blank=True)
    numero_identite = models.CharField("NIF / CIN", max_length=40, blank=True)
    adresse = models.CharField("Adresse", max_length=240, blank=True)
    note_identite_verifiee = models.BooleanField("Identité vérifiée", default=False)
    cree_le = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        ordering = ["nom", "prenom"]
        verbose_name = "client"
        verbose_name_plural = "clients"

    def __str__(self):
        return f"{self.prenom} {self.nom}"
