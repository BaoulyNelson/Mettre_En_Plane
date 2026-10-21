import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from applications.clients.models import Client
from .models import ConfigurationSite, ProfilUtilisateur


class ConnexionForm(AuthenticationForm):
    username = forms.CharField(
        label="Téléphone, nom d’utilisateur ou adresse courriel",
        max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )

    def clean(self):
        identifiant = self.cleaned_data.get("username", "").strip()
        if "@" in identifiant:
            utilisateurs = User.objects.filter(email__iexact=identifiant)
            if utilisateurs.count() != 1:
                self.add_error(
                    "username",
                    "Aucun compte unique ne correspond à cette adresse courriel.",
                )
                return self.cleaned_data
            self.cleaned_data["username"] = utilisateurs.get().get_username()
        elif not User.objects.filter(username=identifiant).exists() and re.fullmatch(
            r"[\d\s()+.\-]+", identifiant
        ):
            telephone = re.sub(r"\D", "", identifiant)
            if (
                8 <= len(telephone) <= 15
                and User.objects.filter(username=telephone).exists()
            ):
                self.cleaned_data["username"] = telephone
        return super().clean()


class InscriptionClientForm(forms.Form):
    first_name = forms.CharField(label="Prénom", max_length=150)
    last_name = forms.CharField(label="Nom", max_length=150)
    telephone = forms.CharField(
        label="Téléphone WhatsApp",
        max_length=30,
        help_text="Utilisez l’indicatif du pays, par exemple +509.",
    )
    email = forms.EmailField(label="Adresse courriel", required=False)
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_telephone(self):
        telephone = self.cleaned_data["telephone"].strip()
        identifiant = re.sub(r"\D", "", telephone)
        if not 8 <= len(identifiant) <= 15:
            raise forms.ValidationError(
                "Saisissez un numéro valide avec son indicatif de pays."
            )
        if User.objects.filter(username=identifiant).exists():
            raise forms.ValidationError(
                "Un compte existe déjà pour ce numéro. Connectez-vous ou contactez l’équipe."
            )
        self.cleaned_data["identifiant_telephone"] = identifiant
        return telephone

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Cette adresse courriel est déjà associée à un compte."
            )
        return email

    def clean(self):
        donnees = super().clean()
        mot_de_passe = donnees.get("password1")
        confirmation = donnees.get("password2")
        if mot_de_passe and confirmation and mot_de_passe != confirmation:
            self.add_error("password2", "Les deux mots de passe ne correspondent pas.")
        if mot_de_passe and not self.errors:
            utilisateur = User(
                username=donnees.get("identifiant_telephone", ""),
                first_name=donnees.get("first_name", ""),
                last_name=donnees.get("last_name", ""),
                email=donnees.get("email", ""),
            )
            try:
                validate_password(mot_de_passe, user=utilisateur)
            except ValidationError as erreur:
                self.add_error("password1", erreur)
        return donnees

    @transaction.atomic
    def save(self):
        donnees = self.cleaned_data
        utilisateur = User.objects.create_user(
            username=donnees["identifiant_telephone"],
            password=donnees["password1"],
            first_name=donnees["first_name"],
            last_name=donnees["last_name"],
            email=donnees["email"],
        )
        telephone = donnees["telephone"]
        ProfilUtilisateur.objects.create(
            utilisateur=utilisateur,
            telephone=telephone,
        )
        Client.objects.create(
            utilisateur=utilisateur,
            prenom=utilisateur.first_name,
            nom=utilisateur.last_name,
            telephone=telephone,
            email=utilisateur.email,
        )
        return utilisateur


class CreationCompteForm(UserCreationForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.none(),
        label="Dossier client associé",
    )
    email = forms.EmailField(label="Adresse courriel", required=True)
    first_name = forms.CharField(label="Prénom", max_length=150)
    last_name = forms.CharField(label="Nom", max_length=150)
    telephone = forms.CharField(label="Téléphone", max_length=30, required=False)
    photo = forms.ImageField(label="Photo de profil", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "client")
        labels = {
            "username": "Nom d’utilisateur",
            "first_name": "Prénom",
            "last_name": "Nom",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(
            utilisateur__isnull=True
        ).order_by("nom", "prenom")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Cette adresse courriel est déjà associée à un compte."
            )
        return email

    def save(self, commit=True):
        utilisateur = super().save(commit=commit)
        if commit:
            profil, _ = ProfilUtilisateur.objects.get_or_create(utilisateur=utilisateur)
            profil.telephone = self.cleaned_data.get("telephone", "")
            profil.photo = self.cleaned_data.get("photo") or profil.photo
            profil.save()
            client = self.cleaned_data["client"]
            client.utilisateur = utilisateur
            client.save(update_fields=["utilisateur"])
        return utilisateur


class ChangementMotDePasseForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Mot de passe actuel", widget=forms.PasswordInput
    )
    new_password1 = forms.CharField(
        label="Nouveau mot de passe", widget=forms.PasswordInput
    )
    new_password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe", widget=forms.PasswordInput
    )


class ReinitialisationMotDePasseForm(PasswordResetForm):
    email = forms.EmailField(label="Adresse courriel associée au compte")


class NouveauMotDePasseForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Nouveau mot de passe", widget=forms.PasswordInput
    )
    new_password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe", widget=forms.PasswordInput
    )


class ProfilUtilisateurForm(forms.ModelForm):
    class Meta:
        model = ProfilUtilisateur
        fields = ["telephone", "photo"]


class InformationsUtilisateurForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
            "email": "Adresse courriel",
        }


class ConfigurationSiteForm(forms.ModelForm):
    class Meta:
        model = ConfigurationSite
        fields = ["nom", "slogan", "logo", "adresse", "telephone", "email"]
