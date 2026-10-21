from django import forms


class VenteForm(forms.Form):
    prix_vente = forms.DecimalField(
        label="Prix de vente", min_value=0, decimal_places=2
    )
