from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from applications.contrats.models import Contrat, RappelContrat


class Command(BaseCommand):
    help = "Envoyer les rappels des échéances et des fins de délai de grâce."

    def handle(self, *args, **options):
        aujourd_hui = timezone.localdate()
        contrats = Contrat.objects.filter(statut=Contrat.Statut.ACTIF).select_related(
            "client", "client__utilisateur", "bien"
        )
        envoyes = 0
        ignores = 0

        for contrat in contrats:
            if not contrat.date_echeance:
                continue

            rappels_a_envoyer = []
            if contrat.date_echeance == aujourd_hui + timedelta(days=3):
                rappels_a_envoyer.append(RappelContrat.Type.ECHEANCE_PROCHE)
            if (
                contrat.date_echeance + timedelta(days=contrat.jours_de_grace)
                == aujourd_hui
            ):
                rappels_a_envoyer.append(RappelContrat.Type.FIN_GRACE)

            if not rappels_a_envoyer:
                continue

            destinataire = contrat.client.email
            if not destinataire and contrat.client.utilisateur_id:
                destinataire = contrat.client.utilisateur.email
            if not destinataire:
                self.stderr.write(
                    f"Aucun courriel pour le contrat {contrat.numero}; rappel ignoré."
                )
                ignores += len(rappels_a_envoyer)
                continue

            for type_rappel in rappels_a_envoyer:
                deja_envoye = RappelContrat.objects.filter(
                    contrat=contrat,
                    type=type_rappel,
                    date_echeance=contrat.date_echeance,
                ).exists()
                if deja_envoye:
                    ignores += 1
                    continue

                sujet, message = self._message(contrat, type_rappel, aujourd_hui)
                try:
                    nombre_envoye = send_mail(
                        sujet,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [destinataire],
                        fail_silently=False,
                    )
                except Exception as erreur:
                    self.stderr.write(f"Échec du rappel {contrat.numero}: {erreur}")
                    ignores += 1
                    continue

                if not nombre_envoye:
                    ignores += 1
                    continue

                RappelContrat.objects.create(
                    contrat=contrat,
                    type=type_rappel,
                    date_echeance=contrat.date_echeance,
                    destinataire=destinataire,
                )
                envoyes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Rappels envoyés : {envoyes}; ignorés ou déjà envoyés : {ignores}."
            )
        )

    @staticmethod
    def _message(contrat, type_rappel, aujourd_hui):
        if type_rappel == RappelContrat.Type.ECHEANCE_PROCHE:
            sujet = f"Échéance dans trois jours · contrat {contrat.numero}"
            introduction = (
                f"Votre contrat arrive à échéance le "
                f"{contrat.date_echeance:%d/%m/%Y}."
            )
        else:
            sujet = f"Fin du délai de grâce · contrat {contrat.numero}"
            introduction = (
                f"Le délai de grâce de votre contrat arrive à son terme aujourd'hui "
                f"({aujourd_hui:%d/%m/%Y}). Contactez le personnel sans tarder pour "
                "connaître les options prévues à votre contrat."
            )

        message = (
            f"Bonjour {contrat.client.prenom},\n\n"
            f"{introduction}\n\n"
            f"Bien concerné : {contrat.bien.marque} {contrat.bien.modele}\n"
            f"Capital restant : {contrat.capital_restant} {contrat.devise}\n"
            f"Échéance : {contrat.date_echeance:%d/%m/%Y}\n"
            f"Délai de grâce prévu : {contrat.jours_de_grace} jours\n\n"
            "Le montant de rachat doit être confirmé par le personnel. "
            "Ne répondez pas à ce message avec un mot de passe ou un code de paiement."
        )
        return sujet, message
