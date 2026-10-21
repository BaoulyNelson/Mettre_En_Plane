from django import forms
from django.contrib.auth.models import User

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "prenom",
            "nom",
            "telephone",
            "email",
            "numero_identite",
            "adresse",
            "note_identite_verifiee",
        ]
        widgets = {"adresse": forms.Textarea(attrs={"rows": 2})}


class AssocierCompteClientForm(forms.Form):
    utilisateur = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Compte utilisateur",
        empty_label="Choisir un compte client",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["utilisateur"].queryset = User.objects.filter(
            is_active=True,
            is_staff=False,
            dossier_client__isnull=True,
        ).order_by("username")
