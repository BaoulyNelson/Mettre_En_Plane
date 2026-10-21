from io import BytesIO
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image as PillowImage

from applications.biens.models import Bien
from applications.clients.models import Client
from applications.comptes.models import ConfigurationSite
from applications.contrats.models import Contrat
from applications.paiements.models import Paiement
from .models import DemandeMiseEnGage


class ParcoursDemandeEnLigneTests(TestCase):
    def setUp(self):
        self.client_utilisateur = User.objects.create_user(
            username="client",
            password="Securite-Client-2026!",
            email="client@example.test",
        )
        self.personnel = User.objects.create_user(
            username="personnel",
            password="Securite-Staff-2026!",
            is_staff=True,
        )

    def donnees_demande(self, **modifications):
        donnees = {
            "telephone_contact": "+509 1234 5678",
            "categorie": "informatique",
            "marque": "Lenovo",
            "modele": "ThinkPad",
            "numero_serie": "SERIE-001",
            "description": "Bon état, batterie fonctionnelle.",
            "accessoires": "Chargeur d’origine",
            "appareil_deverrouille": True,
            "preuve_propriete": "Facture disponible",
            "montant_souhaite": "12000.00",
            "devise": "HTG",
            "accepte_conditions": True,
        }
        donnees.update(modifications)
        return donnees

    def creer_contrat(self, utilisateur, suffixe):
        client_dossier = Client.objects.create(
            utilisateur=utilisateur,
            nom=f"Client {suffixe}",
            prenom="Jean",
            telephone="+509 1234 5678",
        )
        bien = Bien.objects.create(
            client=client_dossier,
            marque="Lenovo",
            modele=f"ThinkPad {suffixe}",
            numero_serie=f"SERIE-{suffixe}",
        )
        contrat = Contrat.objects.create(
            client=client_dossier,
            bien=bien,
            capital_initial=Decimal("1000.00"),
            capital_restant=Decimal("1000.00"),
            taux_mensuel=Decimal("15.00"),
            date_echeance=timezone.localdate() + timedelta(days=2),
        )
        paiement = Paiement.objects.create(
            contrat=contrat,
            type=Paiement.Type.INTERET,
            montant=Decimal("150.00"),
            montant_interet=Decimal("150.00"),
            note="Ne doit pas être visible au client.",
        )
        return contrat, paiement

    def test_client_voit_son_contrat_et_telecharge_son_recu_pdf(self):
        contrat, paiement = self.creer_contrat(self.client_utilisateur, "PROPRE")
        self.client.force_login(self.client_utilisateur)

        reponse = self.client.get(reverse("demandes:espace"))

        self.assertContains(reponse, contrat.numero)
        self.assertContains(reponse, "Estimation de rachat aujourd’hui")
        self.assertEqual(
            reponse.context["contrats"][0].montant_rachat_estime,
            Decimal("1150.00"),
        )
        self.assertContains(
            reponse, reverse("contrats:recu", args=[contrat.pk, paiement.pk])
        )
        self.assertNotContains(reponse, paiement.note)

        image_logo = BytesIO()
        PillowImage.new("RGB", (120, 60), color="navy").save(image_logo, format="PNG")
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                configuration = ConfigurationSite.objects.create(
                    nom="Plan Lakay",
                    slogan="Clarté dans chaque engagement",
                    adresse="12 rue du Port, Port-au-Prince",
                    telephone="+509 5555 1212",
                    email="contact@planlakay.example",
                )
                configuration.logo.save(
                    "logo.png",
                    SimpleUploadedFile(
                        "logo.png", image_logo.getvalue(), content_type="image/png"
                    ),
                    save=True,
                )
                recu = self.client.get(
                    reverse("contrats:recu", args=[contrat.pk, paiement.pk])
                )

        self.assertEqual(recu.status_code, 200)
        self.assertEqual(recu["Content-Type"], "application/pdf")
        self.assertTrue(recu.content.startswith(b"%PDF-"))
        self.assertIn(b"/Count 1", recu.content)
        self.assertIn(b"/FontFile2", recu.content)
        self.assertGreaterEqual(recu.content.count(b"/Subtype /Image"), 2)
        self.assertIn(b"Plan Lakay", recu.content)
        self.assertIn(b"contact@planlakay.example", recu.content)
        self.assertIn(b"12 rue du Port, Port-au-Prince", recu.content)

    def test_client_ne_voit_ni_le_contrat_ni_le_recu_d_un_autre(self):
        contrat_autre, paiement_autre = self.creer_contrat(self.personnel, "AUTRE")
        self.client.force_login(self.client_utilisateur)

        espace = self.client.get(reverse("demandes:espace"))
        self.assertNotContains(espace, contrat_autre.numero)
        reponse = self.client.get(
            reverse("contrats:recu", args=[contrat_autre.pk, paiement_autre.pk])
        )
        self.assertEqual(reponse.status_code, 404)

    def test_client_soumet_une_demande_en_attente_sans_creer_de_contrat(self):
        self.client.force_login(self.client_utilisateur)
        reponse = self.client.post("/mise-en-gage/nouvelle/", self.donnees_demande())
        self.assertRedirects(reponse, "/mon-espace/")
        demande = DemandeMiseEnGage.objects.get()
        self.assertEqual(demande.utilisateur, self.client_utilisateur)
        self.assertEqual(demande.statut, DemandeMiseEnGage.Statut.A_ETUDIER)
        self.assertEqual(Contrat.objects.count(), 0)

    def test_client_ne_peut_consulter_que_ses_demandes(self):
        demande = DemandeMiseEnGage.objects.create(
            utilisateur=self.personnel,
            **self.donnees_demande(accepte_conditions=True),
        )
        self.client.force_login(self.client_utilisateur)
        reponse = self.client.get(f"/mon-espace/{demande.reference}/")
        self.assertEqual(reponse.status_code, 404)

    def test_client_est_renvoye_hors_des_urls_staff(self):
        self.client.force_login(self.client_utilisateur)
        reponse = self.client.get("/gestion/demandes/")
        self.assertRedirects(reponse, "/mon-espace/")

    def test_navigation_client_est_coherente_sur_profil_et_securite(self):
        self.client.force_login(self.client_utilisateur)

        for url in ("/comptes/profil/", "/mot-de-passe/modifier/"):
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertContains(reponse, "Nouvelle demande")
                self.assertNotContains(reponse, "Mettre un bien en gage")

    def test_entete_prefer_logo_mobile_avec_repli_textuel(self):
        self.client.force_login(self.client_utilisateur)

        reponse_sans_logo = self.client.get("/comptes/profil/")
        self.assertContains(reponse_sans_logo, "Mete nan plàn · HAÏTI")
        self.assertNotContains(reponse_sans_logo, "topbar-mobile-logo")

        configuration = ConfigurationSite.objects.create(
            nom="Plan Lakay",
            logo="identite/logo.png",
        )
        reponse_avec_logo = self.client.get("/comptes/profil/")
        self.assertContains(reponse_avec_logo, "topbar-mobile-logo")
        self.assertContains(reponse_avec_logo, configuration.logo.url)

    def test_espace_client_conserve_un_panneau_sans_liens_personnel(self):
        demande = DemandeMiseEnGage.objects.create(
            utilisateur=self.client_utilisateur,
            **self.donnees_demande(accepte_conditions=True),
        )
        self.client.force_login(self.client_utilisateur)

        pages_client = [
            reverse("demandes:espace"),
            reverse("demandes:creer"),
            reverse("demandes:detail", args=[demande.reference]),
        ]
        for url in pages_client:
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertContains(reponse, 'class="sidebar"')
                self.assertContains(reponse, 'aria-label="Navigation rapide"')
                self.assertContains(reponse, "Sécurité et mot de passe")
                self.assertContains(reponse, "Nouvelle demande")
                self.assertNotContains(reponse, "Revente")
                self.assertNotContains(reponse, 'href="/clients/')

    def test_staff_peut_mettre_a_jour_le_statut_sans_creer_de_pret(self):
        demande = DemandeMiseEnGage.objects.create(
            utilisateur=self.client_utilisateur,
            **self.donnees_demande(accepte_conditions=True),
        )
        self.client.force_login(self.personnel)
        reponse = self.client.post(
            f"/gestion/demandes/{demande.reference}/",
            {"statut": "en_cours", "note_interne": "Appeler pour rendez-vous."},
        )
        self.assertRedirects(reponse, f"/gestion/demandes/{demande.reference}/")
        demande.refresh_from_db()
        self.assertEqual(demande.statut, DemandeMiseEnGage.Statut.EN_COURS)
