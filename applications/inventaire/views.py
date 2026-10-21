from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from applications.comptes.decorators import personnel_requis
from .forms import VenteForm
from .models import ArticleRevente


@personnel_requis
def liste(request):
    articles = ArticleRevente.objects.select_related("bien", "bien__client", "contrat")
    return render(request, "inventaire/liste.html", {"articles": articles})


@personnel_requis
def vendre(request, article_id):
    article = get_object_or_404(ArticleRevente, pk=article_id, vendu_le__isnull=True)
    formulaire = VenteForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        article.prix_vente = formulaire.cleaned_data["prix_vente"]
        article.vendu_le = timezone.now()
        article.bien.etat = article.bien.Etat.VENDU
        article.bien.save(update_fields=["etat"])
        article.save(update_fields=["prix_vente", "vendu_le"])
        messages.success(request, "La vente est enregistrée.")
    return redirect("inventaire:liste")
