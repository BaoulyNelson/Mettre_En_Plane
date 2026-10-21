from django import forms

from applications.biens.models import Bien
from .models import Contrat


class ContratForm(forms.ModelForm):
    class Meta:
        model = Contrat
        fields = [
            "client",
            "bien",
            "capital_initial",
            "devise",
            "taux_mensuel",
            "duree_jours",
            "jours_de_grace",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].widget.attrs[
            "data-biens-url"
        ] = "/contrats/biens-disponibles/"
        self.fields["client"].help_text = (
            "Choisissez d’abord un client pour afficher ses biens disponibles."
        )
        self.fields["bien"].help_text = (
            "Seuls les biens disponibles de ce client sont proposés."
        )
        client_id = (
            self.data.get("client") if self.is_bound else self.initial.get("client")
        )
        if hasattr(client_id, "pk"):
            client_id = client_id.pk
        try:
            client_id = int(client_id)
        except (TypeError, ValueError):
            client_id = None
        self.fields["bien"].queryset = (
            Bien.objects.filter(client_id=client_id)
            if client_id
            else Bien.objects.none()
        )

    def clean(self):
        donnees = super().clean()
        client = donnees.get("client")
        bien = donnees.get("bien")
        capital = donnees.get("capital_initial")
        if capital is not None and capital <= 0:
            self.add_error(
                "capital_initial", "Le capital prêté doit être supérieur à zéro."
            )
        if client and (not client.numero_identite or not client.note_identite_verifiee):
            self.add_error(
                "client",
                "Renseignez et vérifiez le NIF / CIN avant d’ouvrir un contrat.",
            )
        if client and bien:
            if client.pk != bien.client_id:
                self.add_error(
                    "bien", "Ce bien n'appartient pas au client sélectionné."
                )
            elif bien.etat != Bien.Etat.DEPOSE:
                self.add_error(
                    "bien", "Ce bien n'est plus disponible pour un nouveau contrat."
                )
            elif bien.contrats.filter(statut=Contrat.Statut.ACTIF).exists():
                self.add_error("bien", "Ce bien est déjà associé à un contrat actif.")
            if not bien.preuve_propriete:
                self.add_error(
                    "bien", "Ajoutez une facture ou une déclaration de propriété."
                )
            if (
                bien.categorie == Bien.Categorie.INFORMATIQUE
                and not bien.appareil_deverrouille
            ):
                self.add_error(
                    "bien",
                    "Un ordinateur verrouillé ne peut pas être accepté en garantie.",
                )
        return donnees

    def save(self, commit=True):
        contrat = super().save(commit=False)
        contrat.capital_restant = contrat.capital_initial
        if commit:
            contrat.save()
        return contrat
