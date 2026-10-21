from django import forms

from .models import DemandeMiseEnGage


class DemandeMiseEnGageForm(forms.ModelForm):
    class Meta:
        model = DemandeMiseEnGage
        fields = [
            "telephone_contact",
            "categorie",
            "marque",
            "modele",
            "numero_serie",
            "description",
            "accessoires",
            "appareil_deverrouille",
            "preuve_propriete",
            "montant_souhaite",
            "devise",
            "photo_bien",
            "accepte_conditions",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "accessoires": forms.Textarea(attrs={"rows": 2}),
        }


class TraitementDemandeForm(forms.ModelForm):
    class Meta:
        model = DemandeMiseEnGage
        fields = ["statut", "note_interne"]
        widgets = {"note_interne": forms.Textarea(attrs={"rows": 4})}
