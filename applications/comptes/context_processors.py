from .models import ConfigurationSite, ProfilUtilisateur


def informations_globales(request):
    identite_site = ConfigurationSite.objects.filter(pk=1).first()
    if identite_site is None:
        identite_site = ConfigurationSite()

    profil_utilisateur = None
    if request.user.is_authenticated:
        profil_utilisateur = ProfilUtilisateur.objects.filter(
            utilisateur=request.user
        ).first()

    return {
        "identite_site": identite_site,
        "profil_utilisateur": profil_utilisateur,
    }
