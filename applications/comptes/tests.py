from io import BytesIO
import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings, tag
from django.urls import reverse
from PIL import Image

from applications.clients.models import Client
from .models import ConfigurationSite, ProfilUtilisateur


class GestionComptesTests(TestCase):
    def setUp(self):
        media_temporaire = tempfile.TemporaryDirectory()
        self.addCleanup(media_temporaire.cleanup)
        configuration_media = override_settings(MEDIA_ROOT=media_temporaire.name)
        configuration_media.enable()
        self.addCleanup(configuration_media.disable)
        self.personnel = User.objects.create_user(
            username="gestionnaire",
            password="Initial!Password2026",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="agent",
            email="agent@example.test",
            password="Initial!Password2026",
        )
        self.client_dossier = Client.objects.create(
            nom="Client",
            prenom="Exemple",
            telephone="+509 1234 5678",
        )

    def test_creation_compte_reserve_au_personnel(self):
        self.client.force_login(self.user)
        reponse = self.client.get("/comptes/nouveau/")
        self.assertRedirects(reponse, "/mon-espace/")

    def test_inscription_publique_cree_un_compte_client_et_sa_fiche(self):
        reponse = self.client.post(
            "/inscription/",
            {
                "first_name": "Jean",
                "last_name": "Pierre",
                "email": "jean@example.test",
                "telephone": "+509 1234 5678",
                "password1": "Securite-Creation-2026!",
                "password2": "Securite-Creation-2026!",
            },
        )
        self.assertRedirects(reponse, "/mise-en-gage/nouvelle/")
        utilisateur = User.objects.get(username="50912345678")
        self.assertFalse(utilisateur.is_staff)
        self.assertEqual(utilisateur.profil.telephone, "+509 1234 5678")
        self.assertEqual(utilisateur.dossier_client.telephone, "+509 1234 5678")

    def test_accueil_public_propose_connexion_et_creation_client(self):
        reponse = self.client.get("/")

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Créer un compte client")
        self.assertContains(reponse, "/inscription/")
        self.assertContains(reponse, 'aria-label="Se connecter"')

    def test_accueil_public_reste_accessible_aux_utilisateurs_connectes(self):
        for utilisateur in (self.personnel, self.user):
            with self.subTest(utilisateur=utilisateur.username):
                self.client.force_login(utilisateur)
                reponse = self.client.get("/")
                self.assertEqual(reponse.status_code, 200)
                self.assertTemplateUsed(reponse, "accueil_public.html")
                self.assertContains(reponse, "Présenter un bien")
                self.assertContains(reponse, reverse("comptes:profil"))
                self.assertContains(reponse, 'aria-label="Mon profil"')

    def test_deconnexion_redirige_vers_accueil_public(self):
        self.client.force_login(self.user)

        reponse = self.client.post(reverse("deconnexion"))

        self.assertRedirects(reponse, reverse("accueil_public"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_tableau_de_bord_utilise_une_route_distincte(self):
        self.client.force_login(self.personnel)
        url_tableau = reverse("tableau_de_bord:accueil")

        self.assertEqual(url_tableau, "/tableau-de-bord/")
        self.assertContains(self.client.get(url_tableau), "Vue d’ensemble")

    def test_menu_affiche_admin_django_uniquement_au_superutilisateur(self):
        self.client.force_login(self.personnel)
        reponse_personnel = self.client.get(reverse("tableau_de_bord:accueil"))
        self.assertContains(reponse_personnel, reverse("accueil_public"))
        self.assertNotContains(reponse_personnel, reverse("admin:index"))

        superutilisateur = User.objects.create_superuser(
            username="administrateur",
            email="admin@example.test",
            password="Admin-2026-Secure!",
        )
        self.client.force_login(superutilisateur)
        reponse_admin = self.client.get(reverse("tableau_de_bord:accueil"))
        self.assertContains(reponse_admin, reverse("accueil_public"))
        self.assertContains(reponse_admin, reverse("admin:index"))

    def test_connexion_propose_clairement_la_creation_de_compte(self):
        reponse = self.client.get("/connexion/")
        self.assertContains(reponse, "/inscription/")
        self.assertContains(reponse, "Créer un compte client")

    def test_connexion_accepte_adresse_courriel(self):
        reponse = self.client.post(
            "/connexion/",
            {"username": self.user.email, "password": "Initial!Password2026"},
        )
        self.assertRedirects(reponse, "/mon-espace/")

    def test_connexion_accepte_nom_utilisateur(self):
        reponse = self.client.post(
            "/connexion/",
            {"username": self.user.username, "password": "Initial!Password2026"},
        )
        self.assertRedirects(reponse, "/mon-espace/")

    def test_connexion_accepte_le_numero_de_telephone(self):
        telephone = "+509 2345 6789"
        utilisateur = User.objects.create_user(
            username="50923456789",
            password="Securite-Telephone-2026!",
        )
        Client.objects.create(
            utilisateur=utilisateur,
            nom="Pierre",
            prenom="Jean",
            telephone=telephone,
        )

        reponse = self.client.post(
            "/connexion/",
            {"username": telephone, "password": "Securite-Telephone-2026!"},
        )

        self.assertRedirects(reponse, "/mon-espace/")

    def test_personnel_peut_afficher_le_formulaire_de_creation(self):
        self.client.force_login(self.personnel)
        reponse = self.client.get("/comptes/nouveau/")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Créer un compte")

    def test_personnel_peut_creer_un_compte_non_administrateur(self):
        self.client.force_login(self.personnel)
        reponse = self.client.post(
            "/comptes/nouveau/",
            {
                "username": "nouvel_agent",
                "first_name": "Anne",
                "last_name": "Pierre",
                "email": "anne@example.test",
                "client": self.client_dossier.pk,
                "password1": "Plan-Securise-2026!",
                "password2": "Plan-Securise-2026!",
            },
        )
        self.assertEqual(reponse.status_code, 302)
        compte = User.objects.get(username="nouvel_agent")
        self.assertFalse(compte.is_staff)
        self.assertTrue(compte.check_password("Plan-Securise-2026!"))
        self.client_dossier.refresh_from_db()
        self.assertEqual(self.client_dossier.utilisateur, compte)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_reinitialisation_envoie_un_lien_securise(self):
        reponse = self.client.post("/mot-de-passe/oublie/", {"email": self.user.email})
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/mot-de-passe/", mail.outbox[0].body)

    def test_changement_de_mot_de_passe_enregistre_le_nouveau(self):
        self.client.force_login(self.user)
        reponse = self.client.post(
            "/mot-de-passe/modifier/",
            {
                "old_password": "Initial!Password2026",
                "new_password1": "A_Different!Password2026",
                "new_password2": "A_Different!Password2026",
            },
        )
        self.assertEqual(reponse.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("A_Different!Password2026"))

    @tag("photo-profil")
    def test_utilisateur_peut_enregistrer_sa_photo_de_profil(self):
        image = BytesIO()
        Image.new("RGB", (2, 2), color="blue").save(image, format="PNG")
        photo = SimpleUploadedFile(
            "profil.png", image.getvalue(), content_type="image/png"
        )
        self.client.force_login(self.user)
        reponse = self.client.post(
            "/comptes/profil/",
            {
                "first_name": "Agent",
                "last_name": "Test",
                "email": self.user.email,
                "telephone": "+509 1234 5678",
                "photo": photo,
            },
        )
        self.assertRedirects(reponse, "/comptes/profil/")
        self.user.profil.refresh_from_db()
        self.assertTrue(self.user.profil.photo.name.endswith("profil.png"))

    def test_staff_peut_configurer_identite_et_coordonnees_du_site(self):
        self.client.force_login(self.personnel)
        reponse = self.client.post(
            "/comptes/site/",
            {
                "nom": "Plan Lakay",
                "slogan": "Un service proche de vous",
                "adresse": "Port-au-Prince",
                "telephone": "+509 1234 5678",
                "email": "contact@example.test",
            },
        )
        self.assertRedirects(reponse, "/comptes/site/")
        identite = ConfigurationSite.objects.get(pk=1)
        self.assertEqual(identite.nom, "Plan Lakay")
        self.assertEqual(identite.telephone, "+509 1234 5678")


class AccesMediaPriveTests(TransactionTestCase):
    def setUp(self):
        media_temporaire = tempfile.TemporaryDirectory()
        self.addCleanup(media_temporaire.cleanup)
        configuration_media = override_settings(MEDIA_ROOT=media_temporaire.name)
        configuration_media.enable()
        self.addCleanup(configuration_media.disable)
        self.proprietaire = User.objects.create_user(username="proprietaire")
        self.autre_utilisateur = User.objects.create_user(username="autre")
        image = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(image, format="PNG")
        photo = SimpleUploadedFile(
            "privee.png", image.getvalue(), content_type="image/png"
        )
        self.profil = ProfilUtilisateur.objects.create(
            utilisateur=self.proprietaire,
            photo=photo,
        )

    @tag("photo-profil")
    def test_photo_visible_au_proprietaire_et_invisible_aux_autres(self):
        chemin_photo = self.profil.photo.url
        self.client.force_login(self.proprietaire)
        reponse_proprietaire = self.client.get(chemin_photo)
        self.assertEqual(reponse_proprietaire.status_code, 200)
        reponse_proprietaire.close()

        self.client.force_login(self.autre_utilisateur)
        reponse_autre = self.client.get(chemin_photo)
        self.assertEqual(reponse_autre.status_code, 404)
        reponse_autre.close()
