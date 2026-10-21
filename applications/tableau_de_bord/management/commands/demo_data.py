from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from applications.biens.models import Bien
from applications.clients.models import Client
from applications.comptes.models import ConfigurationSite, ProfilUtilisateur
from applications.contrats.models import Contrat
from applications.demandes.models import DemandeMiseEnGage
from applications.inventaire.models import ArticleRevente
from applications.paiements.models import Paiement


class Command(BaseCommand):
    help = "Créer ou actualiser des comptes et dossiers reconnaissables pour une démo locale."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mot-de-passe",
            default="Demo-Plan-2026!",
            help="Mot de passe commun des comptes démo (défaut: Demo-Plan-2026!).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Les données de démonstration sont réservées au mode DEBUG."
            )

        configuration_site, _ = ConfigurationSite.objects.get_or_create(
            pk=1,
            defaults={
                "nom": "Mete nan plàn · Démo",
                "slogan": "Clarté dans chaque engagement.",
                "adresse": "Adresse de démonstration, Port-au-Prince",
                "telephone": "+509 5550 0100",
                "email": "demo@example.test",
            },
        )
        logo_demo = settings.MEDIA_ROOT / "identite" / "logo.png"
        if not configuration_site.logo and logo_demo.is_file():
            configuration_site.logo.name = "identite/logo.png"
            configuration_site.save(update_fields=["logo"])

        mot_de_passe = options["mot_de_passe"]
        personnel = self._compte(
            "demo_staff",
            "demo-staff@example.test",
            "Personnel",
            "Démo",
            mot_de_passe,
            is_staff=True,
        )
        client_compte = self._compte(
            "demo_client",
            "demo-client@example.test",
            "Client",
            "Démo",
            mot_de_passe,
            is_staff=False,
        )
        self._profil(client_compte, "+509 5550 0101")

        client_actif = self._client("DEMO-NIF-001", "Jean", "Démo", "+509 5550 0101")
        if not Client.objects.filter(utilisateur=client_compte).exclude(
            pk=client_actif.pk
        ).exists() and client_actif.utilisateur_id in (None, client_compte.pk):
            client_actif.utilisateur = client_compte
            client_actif.save(update_fields=["utilisateur"])
        bien_actif = self._bien(
            client_actif,
            "DEMO-LAPTOP-01",
            "Lenovo",
            "ThinkPad T14",
            Bien.Etat.DEPOSE,
        )
        contrat_actif = self._contrat(
            client_actif,
            bien_actif,
            Decimal("15000.00"),
            date_echeance=timezone.localdate() + timedelta(days=2),
            statut=Contrat.Statut.ACTIF,
        )
        self._bien(
            client_actif,
            "DEMO-LAPTOP-03",
            "Dell",
            "Latitude 5420",
            Bien.Etat.DEPOSE,
        )
        if not Paiement.objects.filter(note="DEMO-PAIEMENT-01").exists():
            Paiement.objects.create(
                contrat=contrat_actif,
                type=Paiement.Type.INTERET,
                montant=contrat_actif.interet_mensuel,
                devise_recue=contrat_actif.devise,
                montant_interet=contrat_actif.interet_mensuel,
                note="DEMO-PAIEMENT-01",
            )

        client_saisi = self._client("DEMO-NIF-002", "Mika", "Exemple", "+509 5550 0102")
        bien_saisi = self._bien(
            client_saisi,
            "DEMO-TELEPHONE-02",
            "Samsung",
            "Galaxy S22",
            Bien.Etat.SAISI,
        )
        contrat_saisi = self._contrat(
            client_saisi,
            bien_saisi,
            Decimal("9000.00"),
            date_echeance=timezone.localdate() - timedelta(days=7),
            statut=Contrat.Statut.SAISI,
        )
        ArticleRevente.objects.get_or_create(
            bien=bien_saisi,
            defaults={
                "contrat": contrat_saisi,
                "prix_liquidation": Decimal("10500.00"),
            },
        )

        for numero_serie, statut, marque, modele, montant in (
            (
                "DEMO-REQ-01",
                DemandeMiseEnGage.Statut.A_ETUDIER,
                "HP",
                "EliteBook 840",
                Decimal("12000.00"),
            ),
            (
                "DEMO-REQ-02",
                DemandeMiseEnGage.Statut.EN_COURS,
                "Apple",
                "iPhone 13",
                Decimal("18000.00"),
            ),
        ):
            DemandeMiseEnGage.objects.get_or_create(
                utilisateur=client_compte,
                numero_serie=numero_serie,
                defaults={
                    "telephone_contact": "+509 5550 0101",
                    "categorie": (
                        DemandeMiseEnGage.Categorie.INFORMATIQUE
                        if marque == "HP"
                        else DemandeMiseEnGage.Categorie.TELEPHONE
                    ),
                    "marque": marque,
                    "modele": modele,
                    "description": "Dossier de démonstration. Bien en bon état général.",
                    "appareil_deverrouille": True,
                    "preuve_propriete": "Facture de démonstration vérifiée",
                    "montant_souhaite": montant,
                    "devise": "HTG",
                    "accepte_conditions": True,
                    "statut": statut,
                },
            )

        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes."))
        self.stdout.write("Personnel : demo_staff / " + mot_de_passe)
        self.stdout.write("Client : demo_client / " + mot_de_passe)
        self.stdout.write("Relancer cette commande ne duplique pas les dossiers DEMO-.")

    @staticmethod
    def _compte(username, email, first_name, last_name, password, is_staff):
        user, _ = User.objects.get_or_create(username=username)
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_staff = is_staff
        user.is_superuser = False
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def _profil(user, telephone):
        ProfilUtilisateur.objects.update_or_create(
            utilisateur=user,
            defaults={"telephone": telephone},
        )

    @staticmethod
    def _client(numero_identite, prenom, nom, telephone):
        client, _ = Client.objects.get_or_create(
            numero_identite=numero_identite,
            defaults={"prenom": prenom, "nom": nom, "telephone": telephone},
        )
        client.prenom = prenom
        client.nom = nom
        client.telephone = telephone
        client.email = "demo@example.test"
        client.note_identite_verifiee = True
        client.save()
        return client

    @staticmethod
    def _bien(client, numero_serie, marque, modele, etat):
        bien, _ = Bien.objects.get_or_create(
            numero_serie=numero_serie,
            defaults={"client": client, "marque": marque, "modele": modele},
        )
        bien.client = client
        bien.categorie = (
            Bien.Categorie.INFORMATIQUE
            if marque in {"Lenovo", "HP"}
            else Bien.Categorie.TELEPHONE
        )
        bien.marque = marque
        bien.modele = modele
        bien.description = "Bien de démonstration en bon état général."
        bien.accessoires = "Chargeur"
        bien.appareil_deverrouille = True
        bien.preuve_propriete = "Facture DEMO vérifiée"
        bien.etat = etat
        bien.save()
        return bien

    @staticmethod
    def _contrat(client, bien, capital, date_echeance, statut):
        contrat = Contrat.objects.filter(bien=bien).order_by("-cree_le").first()
        if contrat:
            return contrat
        return Contrat.objects.create(
            client=client,
            bien=bien,
            capital_initial=capital,
            capital_restant=capital,
            devise="HTG",
            taux_mensuel=Decimal("15.00"),
            date_debut=timezone.localdate() - timedelta(days=28),
            date_echeance=date_echeance,
            statut=statut,
        )
