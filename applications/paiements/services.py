from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from applications.biens.models import Bien
from applications.contrats.models import Contrat
from applications.inventaire.models import ArticleRevente
from .models import Paiement


@transaction.atomic
def enregistrer_paiement(
    contrat_id,
    type_paiement,
    capital_verse=Decimal("0"),
    note="",
    devise_recue=None,
    taux_change=None,
):
    contrat = Contrat.objects.select_for_update().get(pk=contrat_id)
    if contrat.statut != Contrat.Statut.ACTIF:
        raise ValidationError("Ce contrat n'accepte plus de paiement.")

    interet = contrat.interet_mensuel
    capital_verse = Decimal(capital_verse or "0")
    if type_paiement == Paiement.Type.INTERET:
        montant_total = interet
        montant_capital = Decimal("0")
    elif type_paiement == Paiement.Type.ACOMPTE:
        if capital_verse <= 0 or capital_verse >= contrat.capital_restant:
            raise ValidationError(
                "L'acompte doit être positif et inférieur au capital restant."
            )
        montant_total = interet + capital_verse
        montant_capital = capital_verse
    elif type_paiement == Paiement.Type.SOLDE:
        montant_capital = contrat.capital_restant
        montant_total = interet + montant_capital
    else:
        raise ValidationError("Type de paiement inconnu.")

    devise_recue = devise_recue or contrat.devise
    taux_change = Decimal(taux_change or "1")
    if devise_recue != contrat.devise and taux_change <= 0:
        raise ValidationError("Le taux de change doit être supérieur à zéro.")
    montant_recu = montant_total
    if devise_recue != contrat.devise:
        montant_recu = (
            montant_total * taux_change
            if contrat.devise == "USD"
            else montant_total / taux_change
        )
    montant_recu = montant_recu.quantize(Decimal("0.01"))

    paiement = Paiement.objects.create(
        contrat=contrat,
        type=type_paiement,
        montant=montant_recu,
        devise_recue=devise_recue,
        taux_change=taux_change if devise_recue != contrat.devise else Decimal("1"),
        montant_interet=interet,
        montant_capital=montant_capital,
        note=note,
    )
    if type_paiement == Paiement.Type.SOLDE:
        contrat.capital_restant = Decimal("0")
        contrat.statut = Contrat.Statut.SOLDE
        contrat.bien.etat = Bien.Etat.RESTITUE
        contrat.bien.save(update_fields=["etat"])
    else:
        contrat.capital_restant -= montant_capital
        contrat.date_echeance = max(
            contrat.date_echeance, timezone.localdate()
        ) + timedelta(days=30)
    contrat.save(update_fields=["capital_restant", "statut", "date_echeance"])
    return paiement


@transaction.atomic
def saisir_un_bien(contrat_id, prix_liquidation):
    contrat = (
        Contrat.objects.select_for_update().select_related("bien").get(pk=contrat_id)
    )
    date_limite = contrat.date_echeance + timedelta(days=contrat.jours_de_grace)
    if contrat.statut != Contrat.Statut.ACTIF or timezone.localdate() <= date_limite:
        raise ValidationError("La période de grâce n'est pas encore échue.")
    article = ArticleRevente.objects.create(
        bien=contrat.bien,
        contrat=contrat,
        prix_liquidation=prix_liquidation or contrat.capital_restant,
    )
    contrat.statut = Contrat.Statut.SAISI
    contrat.save(update_fields=["statut"])
    contrat.bien.etat = Bien.Etat.SAISI
    contrat.bien.save(update_fields=["etat"])
    return article
