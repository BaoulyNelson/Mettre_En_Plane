from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import Client as ClientHTTP
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from applications.biens.models import Bien
from applications.clients.models import Client
from applications.comptes.models import ConfigurationSite
from applications.contrats.models import Contrat, RappelContrat
from applications.demandes.models import DemandeMiseEnGage
from applications.inventaire.models import ArticleRevente
from applications.paiements.models import Paiement


@override_settings(DEBUG=True)
class DemoDataCommandTests(TestCase):
    def setUp(self):
        call_command("demo_data", stdout=StringIO())
        self.personnel = User.objects.get(username="demo_staff")
        self.client_utilisateur = User.objects.get(username="demo_client")

    def test_commande_rejouable_sans_dupliquer_les_donnees(self):
        ConfigurationSite.objects.filter(pk=1).update(nom="Site personnalisé")
        call_command("demo_data", stdout=StringIO())

        self.assertEqual(
            Client.objects.filter(numero_identite__startswith="DEMO-").count(), 2
        )
        self.assertEqual(
            Bien.objects.filter(numero_serie__startswith="DEMO-").count(), 3
        )
        self.assertEqual(Contrat.objects.count(), 2)
        self.assertEqual(Paiement.objects.count(), 1)
        self.assertEqual(ArticleRevente.objects.count(), 1)
        self.assertEqual(DemandeMiseEnGage.objects.count(), 2)
        self.assertEqual(
            ConfigurationSite.objects.get(pk=1).nom,
            "Site personnalisé",
        )

    def test_pages_de_demo_accessibles_selon_le_role(self):
        client_demo = Client.objects.get(numero_identite="DEMO-NIF-001")
        contrat_demo = Contrat.objects.get(bien__numero_serie="DEMO-LAPTOP-01")
        self.assertEqual(client_demo.utilisateur, self.client_utilisateur)
        demande_demo = DemandeMiseEnGage.objects.filter(
            utilisateur=self.client_utilisateur
        ).first()
        client_http = ClientHTTP()

        client_http.force_login(self.personnel)
        pages_personnel = [
            reverse("tableau_de_bord:accueil"),
            reverse("clients:liste"),
            reverse("clients:detail", args=[client_demo.pk]),
            reverse("biens:liste"),
            reverse("biens:creer"),
            reverse("contrats:liste"),
            reverse("contrats:detail", args=[contrat_demo.pk]),
            reverse("contrats:creer"),
            reverse("inventaire:liste"),
            reverse("demandes:liste_personnel"),
            reverse("demandes:traiter", args=[demande_demo.reference]),
            reverse("comptes:site"),
        ]
        for url in pages_personnel:
            with self.subTest(url=url):
                self.assertEqual(client_http.get(url).status_code, 200)

        client_http.force_login(self.client_utilisateur)
        self.assertContains(
            client_http.get(reverse("demandes:espace")), contrat_demo.numero
        )
        pages_client = [
            reverse("comptes:profil"),
            reverse("demandes:espace"),
            reverse("demandes:creer"),
            reverse("demandes:detail", args=[demande_demo.reference]),
        ]
        for url in pages_client:
            with self.subTest(url=url):
                self.assertEqual(client_http.get(url).status_code, 200)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Mete nan plan <rappels@example.test>",
)
class EnvoiRappelsContratTests(TestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user(
            username="client_rappel",
            email="compte@example.test",
        )
        self.client_dossier = Client.objects.create(
            utilisateur=self.utilisateur,
            nom="Client",
            prenom="Jean",
            telephone="+509 5555 0101",
        )
        self.bien = Bien.objects.create(
            client=self.client_dossier,
            marque="Lenovo",
            modele="ThinkPad",
        )

    def creer_contrat(self, date_echeance, jours_de_grace=5, **modifications):
        valeurs = {
            "client": self.client_dossier,
            "bien": self.bien,
            "capital_initial": "15000.00",
            "capital_restant": "15000.00",
            "date_echeance": date_echeance,
            "jours_de_grace": jours_de_grace,
        }
        valeurs.update(modifications)
        return Contrat.objects.create(**valeurs)

    def test_rappel_trois_jours_avant_est_envoye_une_seule_fois(self):
        contrat = self.creer_contrat(timezone.localdate() + timedelta(days=3))

        call_command("envoyer_rappels", stdout=StringIO())
        call_command("envoyer_rappels", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.utilisateur.email])
        self.assertIn(contrat.numero, mail.outbox[0].subject)
        rappel = RappelContrat.objects.get(contrat=contrat)
        self.assertEqual(rappel.type, RappelContrat.Type.ECHEANCE_PROCHE)

    def test_rappel_de_fin_de_grace_est_envoye_le_dernier_jour(self):
        contrat = self.creer_contrat(
            timezone.localdate() - timedelta(days=5),
            jours_de_grace=5,
        )

        call_command("envoyer_rappels", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Fin du délai de grâce", mail.outbox[0].subject)
        self.assertEqual(
            RappelContrat.objects.get(contrat=contrat).type,
            RappelContrat.Type.FIN_GRACE,
        )

    def test_aucun_envoi_sans_adresse_courriel(self):
        self.utilisateur.email = ""
        self.utilisateur.save(update_fields=["email"])
        self.creer_contrat(timezone.localdate() + timedelta(days=3))

        call_command("envoyer_rappels", stdout=StringIO(), stderr=StringIO())

        self.assertEqual(mail.outbox, [])
        self.assertEqual(RappelContrat.objects.count(), 0)

    def test_contrat_sans_echeance_est_ignore(self):
        contrat = self.creer_contrat(timezone.localdate() + timedelta(days=3))
        Contrat.objects.filter(pk=contrat.pk).update(date_echeance=None)

        call_command("envoyer_rappels", stdout=StringIO())

        self.assertEqual(mail.outbox, [])
        self.assertEqual(RappelContrat.objects.count(), 0)

    def test_aucun_journal_si_le_backend_ne_confirme_pas_l_envoi(self):
        contrat = self.creer_contrat(timezone.localdate() + timedelta(days=3))

        with patch(
            "applications.tableau_de_bord.management.commands.envoyer_rappels.send_mail",
            return_value=0,
        ):
            call_command("envoyer_rappels", stdout=StringIO(), stderr=StringIO())

        self.assertFalse(RappelContrat.objects.filter(contrat=contrat).exists())
