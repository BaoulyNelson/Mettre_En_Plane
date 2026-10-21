from django import forms

from .models import Bien


class BienForm(forms.ModelForm):
    class Meta:
        model = Bien
        fields = [
            "client",
            "categorie",
            "marque",
            "modele",
            "numero_serie",
            "description",
            "accessoires",
            "appareil_deverrouille",
            "preuve_propriete",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "accessoires": forms.Textarea(attrs={"rows": 2}),
        }
