from datetime import timedelta

from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from applications.comptes.decorators import personnel_requis
from applications.biens.models import Bien
from applications.contrats.models import Contrat
from applications.inventaire.models import ArticleRevente
from applications.paiements.models import Paiement


@personnel_requis
def accueil(request):
    aujourd_hui = timezone.localdate()
    actifs = Contrat.objects.filter(statut=Contrat.Statut.ACTIF).select_related(
        "client", "bien"
    )
    echeances = actifs.filter(
        date_echeance__gte=aujourd_hui,
        date_echeance__lte=aujourd_hui + timedelta(days=3),
    )
    en_retard = [contrat for contrat in actifs if contrat.en_retard][:6]
    capital_par_devise = {
        ligne["devise"]: ligne["total"]
        for ligne in actifs.values("devise").annotate(total=Sum("capital_restant"))
    }
    contexte = {
        "contrats_actifs": actifs.count(),
        "capital_htg": capital_par_devise.get("HTG", 0),
        "capital_usd": capital_par_devise.get("USD", 0),
        "biens_en_garantie": Bien.objects.filter(etat=Bien.Etat.DEPOSE).count(),
        "articles_en_vente": ArticleRevente.objects.filter(
            vendu_le__isnull=True
        ).count(),
        "echeances": echeances.order_by("date_echeance")[:6],
        "en_retard": en_retard,
        "paiements_recents": Paiement.objects.select_related(
            "contrat", "contrat__client"
        ).all()[:6],
    }
    return render(request, "tableau_de_bord/accueil.html", contexte)
