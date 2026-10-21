from django.db import models

from applications.clients.models import Client


class Bien(models.Model):
    class Etat(models.TextChoices):
        DEPOSE = "depose", "En garantie"
        SAISI = "saisi", "Saisi"
        A_VENDRE = "a_vendre", "En vente"
        VENDU = "vendu", "Vendu"
        RESTITUE = "restitue", "Restitué"

    class Categorie(models.TextChoices):
        INFORMATIQUE = "informatique", "Informatique"
        TELEPHONE = "telephone", "Téléphone"
        ELECTRONIQUE = "electronique", "Électronique"
        AUTRE = "autre", "Autre"

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="biens")
    categorie = models.CharField(
        "Catégorie",
        max_length=20,
        choices=Categorie.choices,
        default=Categorie.INFORMATIQUE,
    )
    marque = models.CharField("Marque", max_length=100)
    modele = models.CharField("Modèle", max_length=120)
    numero_serie = models.CharField("Numéro de série", max_length=120, blank=True)
    description = models.TextField("Description et état", blank=True)
    accessoires = models.TextField("Accessoires remis", blank=True)
    appareil_deverrouille = models.BooleanField("Appareil déverrouillé", default=False)
    preuve_propriete = models.CharField(
        "Preuve de propriété", max_length=180, blank=True
    )
    etat = models.CharField(
        "État", max_length=20, choices=Etat.choices, default=Etat.DEPOSE
    )
    cree_le = models.DateTimeField("Enregistré le", auto_now_add=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "bien"
        verbose_name_plural = "biens"

    def __str__(self):
        return f"{self.marque} {self.modele} · {self.client}"
