from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import reverse_lazy
from django.urls import include, path

from applications.comptes.forms import (
    ChangementMotDePasseForm,
    NouveauMotDePasseForm,
    ReinitialisationMotDePasseForm,
)
from applications.comptes.views import ConnexionView
from applications.comptes import views as comptes_views

urlpatterns = [
    path("", comptes_views.accueil_public, name="accueil_public"),
    path(
        "connexion/",
        ConnexionView.as_view(),
        name="connexion",
    ),
    path("inscription/", comptes_views.inscription, name="inscription"),
    path("media/<path:chemin>", comptes_views.servir_media, name="media_prive"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
    path(
        "mot-de-passe/modifier/",
        auth_views.PasswordChangeView.as_view(
            template_name="comptes/formulaire.html",
            form_class=ChangementMotDePasseForm,
            success_url=reverse_lazy("password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "mot-de-passe/modifie/",
        auth_views.PasswordChangeDoneView.as_view(template_name="comptes/message.html"),
        name="password_change_done",
    ),
    path(
        "mot-de-passe/oublie/",
        auth_views.PasswordResetView.as_view(
            template_name="comptes/public_formulaire.html",
            form_class=ReinitialisationMotDePasseForm,
            email_template_name="comptes/reinitialisation_email.txt",
            subject_template_name="comptes/reinitialisation_objet.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "mot-de-passe/envoye/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="comptes/public_message.html"
        ),
        name="password_reset_done",
    ),
    path(
        "mot-de-passe/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="comptes/public_formulaire.html",
            form_class=NouveauMotDePasseForm,
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "mot-de-passe/termine/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="comptes/public_message.html"
        ),
        name="password_reset_complete",
    ),
    path("comptes/", include("applications.comptes.urls")),
    path("tableau-de-bord/", include("applications.tableau_de_bord.urls")),
    path("", include("applications.demandes.urls")),
    path("admin/", admin.site.urls),
    path("clients/", include("applications.clients.urls")),
    path("biens/", include("applications.biens.urls")),
    path("contrats/", include("applications.contrats.urls")),
    path("inventaire/", include("applications.inventaire.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
