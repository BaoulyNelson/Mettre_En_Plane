from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from applications.comptes.decorators import personnel_requis
from .forms import AssocierCompteClientForm, ClientForm
from .models import Client


@personnel_requis
def liste(request):
    recherche = request.GET.get("q", "").strip()
    clients = Client.objects.all()
    if recherche:
        clients = clients.filter(
            Q(nom__icontains=recherche)
            | Q(prenom__icontains=recherche)
            | Q(telephone__icontains=recherche)
            | Q(numero_identite__icontains=recherche)
        )
    return render(
        request, "clients/liste.html", {"clients": clients, "recherche": recherche}
    )


@personnel_requis
def creer(request):
    formulaire = ClientForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        client = formulaire.save()
        messages.success(request, f"Le dossier de {client} est enregistré.")
        return redirect("clients:liste")
    return render(
        request,
        "commun/formulaire.html",
        {
            "formulaire": formulaire,
            "titre": "Nouveau client",
            "retour": "clients:liste",
        },
    )


@personnel_requis
def detail(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    return render(
        request,
        "clients/detail.html",
        {
            "client": client,
            "contrats": client.contrats.select_related("bien"),
            "formulaire_compte": (
                AssocierCompteClientForm() if not client.utilisateur_id else None
            ),
        },
    )


@personnel_requis
@require_POST
def associer_compte(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    if client.utilisateur_id:
        messages.error(request, "Un compte est déjà associé à cette fiche client.")
        return redirect("clients:detail", client_id=client.pk)

    formulaire = AssocierCompteClientForm(request.POST)
    if formulaire.is_valid():
        client.utilisateur = formulaire.cleaned_data["utilisateur"]
        client.save(update_fields=["utilisateur"])
        messages.success(request, "Le compte client est associé à cette fiche.")
    else:
        messages.error(request, "Sélectionnez un compte client disponible.")
    return redirect("clients:detail", client_id=client.pk)
