from django import forms

from .models import Paiement


class PaiementForm(forms.Form):
    type = forms.ChoiceField(label="Opération", choices=Paiement.Type.choices)
    capital_verse = forms.DecimalField(
        label="Acompte sur le capital", required=False, min_value=0, decimal_places=2
    )
    devise_recue = forms.ChoiceField(
        label="Devise reçue", choices=[("HTG", "HTG"), ("USD", "USD")]
    )
    taux_change = forms.DecimalField(
        label="Taux HTG par USD",
        required=False,
        min_value=0,
        decimal_places=4,
        help_text="Obligatoire si la devise reçue diffère de celle du contrat.",
    )
    note = forms.CharField(label="Note", required=False, max_length=200)


class SaisieForm(forms.Form):
    prix_liquidation = forms.DecimalField(
        label="Prix de liquidation", required=False, min_value=0, decimal_places=2
    )
