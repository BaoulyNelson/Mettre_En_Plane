from django.core.exceptions import ValidationError


def verifier_taille_image(fichier):
    if fichier.size > 5 * 1024 * 1024:
        raise ValidationError("L’image ne doit pas dépasser 5 Mo.")
