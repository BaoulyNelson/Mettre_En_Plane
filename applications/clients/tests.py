from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Client


class AssociationCompteClientTests(TestCase):
    def setUp(self):
        self.personnel = User.objects.create_user(
            username="personnel",
            password="Motdepasse-Test-2026!",
            is_staff=True,
        )
        self.client_dossier = Client.objects.create(
            nom="Pierre",
            prenom="Jean",
            telephone="+509 1234 5678",
        )

    def test_personnel_associe_un_compte_non_lie(self):
        utilisateur = User.objects.create_user(
            username="client_existant",
            password="Motdepasse-Test-2026!",
        )
        self.client.force_login(self.personnel)

        reponse = self.client.post(
            reverse("clients:associer_compte", args=[self.client_dossier.pk]),
            {"utilisateur": utilisateur.pk},
        )

        self.assertRedirects(
            reponse,
            reverse("clients:detail", args=[self.client_dossier.pk]),
        )
        self.client_dossier.refresh_from_db()
        self.assertEqual(self.client_dossier.utilisateur, utilisateur)

    def test_un_compte_deja_lie_ne_peut_pas_etre_reutilise(self):
        autre_fiche = Client.objects.create(
            nom="Autre",
            prenom="Client",
            telephone="+509 0000 0000",
        )
        utilisateur = User.objects.create_user(username="client_lie")
        autre_fiche.utilisateur = utilisateur
        autre_fiche.save(update_fields=["utilisateur"])
        self.client.force_login(self.personnel)

        reponse = self.client.post(
            reverse("clients:associer_compte", args=[self.client_dossier.pk]),
            {"utilisateur": utilisateur.pk},
        )

        self.client_dossier.refresh_from_db()
        self.assertIsNone(self.client_dossier.utilisateur)
        self.assertEqual(reponse.status_code, 302)

    def test_client_ne_peut_pas_associer_un_compte(self):
        utilisateur = User.objects.create_user(username="client")
        self.client.force_login(utilisateur)

        reponse = self.client.post(
            reverse("clients:associer_compte", args=[self.client_dossier.pk]),
            {"utilisateur": utilisateur.pk},
        )

        self.assertRedirects(reponse, "/mon-espace/")
        self.client_dossier.refresh_from_db()
        self.assertIsNone(self.client_dossier.utilisateur)

    def test_enregistrement_bien_depuis_fiche_preselctionne_client(self):
        self.client.force_login(self.personnel)

        detail = self.client.get(
            reverse("clients:detail", args=[self.client_dossier.pk])
        )
        self.assertContains(
            detail,
            f'href="{reverse("biens:creer")}?client={self.client_dossier.pk}"',
        )

        formulaire = self.client.get(
            reverse("biens:creer"), {"client": self.client_dossier.pk}
        )
        self.assertEqual(
            formulaire.context["formulaire"]["client"].value(),
            str(self.client_dossier.pk),
        )
