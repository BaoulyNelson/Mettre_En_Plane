from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from applications.biens.models import Bien
from applications.clients.models import Client
from applications.comptes.models import ConfigurationSite
from .models import Contrat
from .forms import ContratForm


class ConditionsOuvertureContratTests(TestCase):
    def setUp(self):
        self.client_dossier = Client.objects.create(
            nom="Jean",
            prenom="Mika",
            telephone="+509 0000 0000",
            numero_identite="1234567890",
            note_identite_verifiee=True,
        )
        self.bien = Bien.objects.create(
            client=self.client_dossier,
            marque="Lenovo",
            modele="ThinkPad",
            appareil_deverrouille=True,
            preuve_propriete="Déclaration sur l’honneur",
        )

    def formulaire(self, **modifications):
        donnees = {
            "client": self.client_dossier.pk,
            "bien": self.bien.pk,
            "capital_initial": "1000.00",
            "devise": "HTG",
            "taux_mensuel": "15.00",
            "duree_jours": "30",
            "jours_de_grace": "5",
        }
        donnees.update(modifications)
        return ContratForm(data=donnees)

    def test_ordinateur_verrouille_refuse(self):
        self.bien.appareil_deverrouille = False
        self.bien.save(update_fields=["appareil_deverrouille"])
        formulaire = self.formulaire()
        self.assertFalse(formulaire.is_valid())
        self.assertIn("bien", formulaire.errors)

    def test_identite_non_verifiee_refusee(self):
        self.client_dossier.note_identite_verifiee = False
        self.client_dossier.save(update_fields=["note_identite_verifiee"])
        formulaire = self.formulaire()
        self.assertFalse(formulaire.is_valid())
        self.assertIn("client", formulaire.errors)

    def test_capital_nul_refuse(self):
        formulaire = self.formulaire(capital_initial="0.00")
        self.assertFalse(formulaire.is_valid())
        self.assertIn("capital_initial", formulaire.errors)

    def test_conditions_completes_autorisent_le_contrat(self):
        formulaire = self.formulaire()
        self.assertTrue(formulaire.is_valid(), formulaire.errors)
        contrat = formulaire.save()
        self.assertEqual(contrat.capital_restant, Decimal("1000.00"))

    def test_client_preselectionne_depuis_son_detail(self):
        personnel = User.objects.create_user(
            username="personnel",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(personnel)

        detail = self.client.get(
            reverse("clients:detail", args=[self.client_dossier.pk])
        )
        self.assertContains(
            detail,
            f'href="{reverse("contrats:creer")}?client={self.client_dossier.pk}"',
        )

        formulaire = self.client.get(
            reverse("contrats:creer"), {"client": self.client_dossier.pk}
        )
        self.assertEqual(
            formulaire.context["formulaire"]["client"].value(),
            str(self.client_dossier.pk),
        )

    def test_biens_disponibles_filtre_par_client_et_par_etat(self):
        autre_client = Client.objects.create(
            nom="Autre",
            prenom="Client",
            telephone="+509 1111 1111",
        )
        bien_autre = Bien.objects.create(
            client=autre_client,
            marque="Apple",
            modele="MacBook",
        )
        bien_saisi = Bien.objects.create(
            client=self.client_dossier,
            marque="Samsung",
            modele="Saisi",
            etat=Bien.Etat.SAISI,
        )
        personnel = User.objects.create_user(
            username="personnel",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(personnel)

        reponse = self.client.get(
            reverse("contrats:biens_disponibles"),
            {"client": self.client_dossier.pk},
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            [bien["id"] for bien in reponse.json()["biens"]],
            [self.bien.pk],
        )
        self.assertNotIn(
            bien_autre.pk, [bien["id"] for bien in reponse.json()["biens"]]
        )
        self.assertNotIn(
            bien_saisi.pk, [bien["id"] for bien in reponse.json()["biens"]]
        )

    def test_contrat_imprimable_par_le_personnel_et_seulement_son_client(self):
        contrat = Contrat.objects.create(
            client=self.client_dossier,
            bien=self.bien,
            capital_initial=Decimal("1000.00"),
            capital_restant=Decimal("1000.00"),
            taux_mensuel=Decimal("15.00"),
        )
        client_proprietaire = User.objects.create_user(
            username="client_proprietaire",
        )
        self.client_dossier.utilisateur = client_proprietaire
        self.client_dossier.save(update_fields=["utilisateur"])
        autre_client = User.objects.create_user(username="autre_client")
        ConfigurationSite.objects.create(
            nom="Plan Lakay",
            slogan="Clarté dans chaque engagement",
            adresse="12 rue du Port",
            telephone="+509 5555 1212",
            email="contact@planlakay.example",
        )
        url_document = reverse("contrats:document", args=[contrat.pk])
        personnel = User.objects.create_user(
            username="personnel_document",
            password="test-password",
            is_staff=True,
        )

        self.client.force_login(personnel)
        detail = self.client.get(reverse("contrats:detail", args=[contrat.pk]))
        self.assertContains(detail, url_document)
        document_personnel = self.client.get(url_document)
        self.assertEqual(document_personnel.status_code, 200)
        self.assertEqual(document_personnel["Content-Type"], "application/pdf")
        self.assertTrue(document_personnel.content.startswith(b"%PDF-"))
        self.assertIn(b"/Count 1", document_personnel.content)
        self.assertIn(b"/FontFile2", document_personnel.content)
        self.assertIn(b"/Subtype /Image", document_personnel.content)
        self.assertIn(b"Plan Lakay", document_personnel.content)
        self.assertIn(b"+509 5555 1212", document_personnel.content)

        self.client.force_login(client_proprietaire)
        self.assertEqual(self.client.get(url_document).status_code, 200)

        self.client.force_login(autre_client)
        self.assertEqual(self.client.get(url_document).status_code, 404)
