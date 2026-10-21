from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from applications.clients.models import Client
from applications.comptes.decorators import client_requis, personnel_requis
from applications.contrats.models import Contrat
from .forms import DemandeMiseEnGageForm, TraitementDemandeForm
from .models import DemandeMiseEnGage


@client_requis
def espace(request):
    client = Client.objects.filter(utilisateur=request.user).first()
    contrats = Contrat.objects.none()
    if client:
        contrats = (
            Contrat.objects.filter(client=client)
            .select_related("bien")
            .prefetch_related("paiements")
        )
    demandes = DemandeMiseEnGage.objects.filter(utilisateur=request.user)
    return render(
        request,
        "demandes/espace.html",
        {"client": client, "contrats": contrats, "demandes": demandes},
    )


@client_requis
def creer(request):
    formulaire = DemandeMiseEnGageForm(
        request.POST or None,
        request.FILES or None,
        initial={
            "telephone_contact": getattr(
                getattr(request.user, "profil", None), "telephone", ""
            ),
        },
    )
    if request.method == "POST" and formulaire.is_valid():
        demande = formulaire.save(commit=False)
        demande.utilisateur = request.user
        demande.save()
        messages.success(
            request,
            f"Votre demande {demande.reference} a été envoyée pour étude.",
        )
        return redirect("demandes:espace")
    return render(request, "demandes/formulaire.html", {"form": formulaire})


@client_requis
def detail_client(request, reference):
    demande = get_object_or_404(
        DemandeMiseEnGage,
        reference=reference,
        utilisateur=request.user,
    )
    return render(request, "demandes/detail_client.html", {"demande": demande})


@personnel_requis
def liste_personnel(request):
    demandes = DemandeMiseEnGage.objects.select_related("utilisateur")
    return render(
        request,
        "demandes/liste_personnel.html",
        {"demandes": demandes},
    )


@personnel_requis
def traiter(request, reference):
    demande = get_object_or_404(DemandeMiseEnGage, reference=reference)
    formulaire = TraitementDemandeForm(request.POST or None, instance=demande)
    if request.method == "POST" and formulaire.is_valid():
        formulaire.save()
        messages.success(request, f"La demande {demande.reference} a été mise à jour.")
        return redirect("demandes:traiter", reference=demande.reference)
    return render(
        request,
        "demandes/traiter.html",
        {"demande": demande, "form": formulaire},
    )
