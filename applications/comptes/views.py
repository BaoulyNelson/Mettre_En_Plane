from django.contrib import messages
from django.contrib.auth import login as connecter
import mimetypes

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.text import get_valid_filename
from django.views.decorators.http import require_GET

from .decorators import personnel_requis
from .forms import (
    ConfigurationSiteForm,
    ConnexionForm,
    CreationCompteForm,
    InscriptionClientForm,
    InformationsUtilisateurForm,
    ProfilUtilisateurForm,
)
from .models import ConfigurationSite, ProfilUtilisateur


class ConnexionView(LoginView):
    template_name = "comptes/connexion_split.html"
    authentication_form = ConnexionForm

    def get_success_url(self):
        destination = self.get_redirect_url()
        if destination:
            return destination
        if self.request.user.is_staff:
            return reverse_lazy("tableau_de_bord:accueil")
        return reverse_lazy("demandes:espace")


def accueil_public(request):
    return render(request, "accueil_public.html")


def inscription(request):
    formulaire = InscriptionClientForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        utilisateur = formulaire.save()
        connecter(request, utilisateur)
        messages.success(
            request,
            "Votre compte client est créé. Vous pouvez présenter votre bien.",
        )
        return redirect("demandes:creer")
    return render(request, "comptes/inscription.html", {"form": formulaire})


@login_required
def profil(request):
    profil_utilisateur, _ = ProfilUtilisateur.objects.get_or_create(
        utilisateur=request.user
    )
    informations = InformationsUtilisateurForm(
        request.POST or None, instance=request.user
    )
    formulaire_profil = ProfilUtilisateurForm(
        request.POST or None,
        request.FILES or None,
        instance=profil_utilisateur,
    )
    if (
        request.method == "POST"
        and informations.is_valid()
        and formulaire_profil.is_valid()
    ):
        informations.save()
        formulaire_profil.save()
        messages.success(request, "Votre profil est mis à jour.")
        return redirect("comptes:profil")
    return render(
        request,
        "comptes/profil.html",
        {"informations": informations, "formulaire_profil": formulaire_profil},
    )


@personnel_requis
def configurer_site(request):
    configuration, _ = ConfigurationSite.objects.get_or_create(pk=1)
    formulaire = ConfigurationSiteForm(
        request.POST or None,
        request.FILES or None,
        instance=configuration,
    )
    if request.method == "POST" and formulaire.is_valid():
        formulaire.save()
        messages.success(request, "L’identité du site est mise à jour.")
        return redirect("comptes:site")
    return render(
        request,
        "comptes/site.html",
        {"form": formulaire},
    )


@require_GET
def servir_media(request, chemin):
    if ".." in chemin.split("/"):
        raise Http404

    fichier = None
    prive = True
    if chemin.startswith("profils/"):
        if not request.user.is_authenticated:
            raise Http404
        profil_utilisateur = (
            ProfilUtilisateur.objects.filter(photo=chemin)
            .select_related("utilisateur")
            .first()
        )
        if profil_utilisateur and (
            request.user.is_staff
            or profil_utilisateur.utilisateur_id == request.user.pk
        ):
            fichier = profil_utilisateur.photo
    elif chemin.startswith("demandes/"):
        if not request.user.is_authenticated:
            raise Http404

        from applications.demandes.models import DemandeMiseEnGage

        demande = (
            DemandeMiseEnGage.objects.filter(photo_bien=chemin)
            .select_related("utilisateur")
            .first()
        )
        if demande and (
            request.user.is_staff or demande.utilisateur_id == request.user.pk
        ):
            fichier = demande.photo_bien
    elif chemin.startswith("identite/"):
        configuration = ConfigurationSite.objects.filter(logo=chemin).first()
        if configuration:
            fichier = configuration.logo
            prive = False

    if not fichier:
        raise Http404

    try:
        contenu = fichier.open("rb")
    except (FileNotFoundError, OSError, ValueError) as erreur:
        raise Http404 from erreur

    content_type, _ = mimetypes.guess_type(fichier.name)
    reponse = FileResponse(
        contenu,
        as_attachment=False,
        filename=get_valid_filename(fichier.name.rsplit("/", 1)[-1]),
        content_type=content_type or "application/octet-stream",
    )
    reponse["X-Content-Type-Options"] = "nosniff"
    reponse["Cache-Control"] = (
        "private, max-age=300" if prive else "public, max-age=3600"
    )
    return reponse


@personnel_requis
def creer(request):
    formulaire = CreationCompteForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        compte = formulaire.save()
        messages.success(
            request,
            f"Le compte de {compte.get_full_name() or compte.username} est créé.",
        )
        return redirect("tableau_de_bord:accueil")
    return render(
        request,
        "comptes/formulaire.html",
        {
            "formulaire": formulaire,
            "form": formulaire,
            "titre": "Créer un compte",
            "description": "Associez ce compte à une fiche client existante. Un client ne pourra consulter que ses propres dossiers.",
        },
    )
