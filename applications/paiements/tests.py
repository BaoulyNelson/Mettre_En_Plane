from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from applications.biens.models import Bien
from applications.clients.models import Client
from applications.contrats.models import Contrat
from applications.inventaire.models import ArticleRevente
from .models import Paiement
from .services import enregistrer_paiement, saisir_un_bien


class OperationsFinancieresTests(TestCase):
    def setUp(self):
        self.client_dossier = Client.objects.create(
            nom="Jean", prenom="Mika", telephone="+509 0000 0000"
        )
        self.bien = Bien.objects.create(
            client=self.client_dossier,
            marque="Lenovo",
            modele="ThinkPad",
            appareil_deverrouille=True,
        )
        self.contrat = self.creer_contrat()

    def creer_contrat(self, **modifications):
        valeurs = {
            "client": self.client_dossier,
            "bien": self.bien,
            "capital_initial": Decimal("1000.00"),
            "capital_restant": Decimal("1000.00"),
            "taux_mensuel": Decimal("15.00"),
            "date_debut": timezone.localdate(),
            "date_echeance": timezone.localdate() + timedelta(days=30),
        }
        valeurs.update(modifications)
        return Contrat.objects.create(**valeurs)

    def test_paiement_interet_prolonge_et_conserve_le_capital(self):
        paiement = enregistrer_paiement(self.contrat.pk, Paiement.Type.INTERET)
        self.contrat.refresh_from_db()
        self.assertEqual(paiement.montant, Decimal("150.00"))
        self.assertEqual(self.contrat.capital_restant, Decimal("1000.00"))
        self.assertEqual(
            self.contrat.date_echeance, timezone.localdate() + timedelta(days=60)
        )

    def test_acompte_reduit_le_capital_et_recalcule_l_interet(self):
        enregistrer_paiement(self.contrat.pk, Paiement.Type.ACOMPTE, Decimal("200.00"))
        self.contrat.refresh_from_db()
        self.assertEqual(self.contrat.capital_restant, Decimal("800.00"))
        self.assertEqual(self.contrat.interet_mensuel, Decimal("120.00"))

    def test_solde_restitue_le_bien_et_garde_un_capital_nul(self):
        paiement = enregistrer_paiement(self.contrat.pk, Paiement.Type.SOLDE)
        self.contrat.refresh_from_db()
        self.bien.refresh_from_db()
        self.assertEqual(paiement.montant, Decimal("1150.00"))
        self.assertEqual(self.contrat.capital_restant, Decimal("0.00"))
        self.assertEqual(self.contrat.statut, Contrat.Statut.SOLDE)
        self.assertEqual(self.bien.etat, Bien.Etat.RESTITUE)

    def test_conversion_usd_vers_htg_est_conservee_sur_le_recu(self):
        contrat_usd = self.creer_contrat(
            devise="USD",
            capital_initial=Decimal("100.00"),
            capital_restant=Decimal("100.00"),
        )
        paiement = enregistrer_paiement(
            contrat_usd.pk,
            Paiement.Type.INTERET,
            devise_recue="HTG",
            taux_change=Decimal("150.0000"),
        )
        self.assertEqual(paiement.montant, Decimal("2250.00"))
        self.assertEqual(paiement.devise_recue, "HTG")
        self.assertEqual(paiement.taux_change, Decimal("150.0000"))

    def test_saisie_refusee_avant_fin_de_grace(self):
        with self.assertRaises(ValidationError):
            saisir_un_bien(self.contrat.pk, Decimal("900.00"))

    def test_saisie_transfere_le_bien_a_l_inventaire_apres_grace(self):
        self.contrat.date_echeance = timezone.localdate() - timedelta(days=6)
        self.contrat.save(update_fields=["date_echeance"])
        article = saisir_un_bien(self.contrat.pk, Decimal("900.00"))
        self.contrat.refresh_from_db()
        self.bien.refresh_from_db()
        self.assertIsInstance(article, ArticleRevente)
        self.assertEqual(self.contrat.statut, Contrat.Statut.SAISI)
        self.assertEqual(self.bien.etat, Bien.Etat.SAISI)
