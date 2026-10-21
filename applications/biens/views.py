from django.contrib import messages
from django.shortcuts import redirect, render

from applications.comptes.decorators import personnel_requis
from .forms import BienForm
from .models import Bien


@personnel_requis
def liste(request):
    biens = Bien.objects.select_related("client").all()
    return render(request, "biens/liste.html", {"biens": biens})


@personnel_requis
def creer(request):
    formulaire = BienForm(
        request.POST or None,
        initial={"client": request.GET.get("client")},
    )
    if request.method == "POST" and formulaire.is_valid():
        bien = formulaire.save()
        messages.success(
            request, f"Le bien {bien.marque} {bien.modele} est enregistré."
        )
        return redirect("biens:liste")
    return render(
        request,
        "commun/formulaire.html",
        {
            "formulaire": formulaire,
            "titre": "Nouveau bien en garantie",
            "retour": "biens:liste",
        },
    )
