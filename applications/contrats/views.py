from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab

from applications.biens.models import Bien
from applications.comptes.decorators import personnel_requis
from applications.comptes.models import ConfigurationSite
from applications.paiements.forms import PaiementForm, SaisieForm
from applications.paiements.models import Paiement
from applications.paiements.services import enregistrer_paiement, saisir_un_bien
from .forms import ContratForm
from .models import Contrat


@personnel_requis
def liste(request):
    contrats = Contrat.objects.select_related("client", "bien").all()
    return render(request, "contrats/liste.html", {"contrats": contrats})


@personnel_requis
def creer(request):
    formulaire = ContratForm(
        request.POST or None,
        initial={"client": request.GET.get("client")},
    )
    if request.method == "POST" and formulaire.is_valid():
        contrat = formulaire.save()
        messages.success(request, f"Le contrat {contrat.numero} est créé.")
        return redirect("contrats:detail", contrat_id=contrat.pk)
    return render(
        request,
        "commun/formulaire.html",
        {
            "formulaire": formulaire,
            "titre": "Nouveau contrat",
            "retour": "contrats:liste",
        },
    )


@personnel_requis
def biens_disponibles(request):
    client_id = request.GET.get("client")
    if not client_id or not client_id.isdigit():
        return JsonResponse({"biens": []})

    biens = (
        Bien.objects.filter(
            client_id=client_id,
            etat=Bien.Etat.DEPOSE,
        )
        .exclude(preuve_propriete="")
        .exclude(categorie=Bien.Categorie.INFORMATIQUE, appareil_deverrouille=False)
        .exclude(contrats__statut=Contrat.Statut.ACTIF)
        .distinct()
        .order_by("marque", "modele")
    )
    return JsonResponse(
        {"biens": [{"id": bien.pk, "label": str(bien)} for bien in biens]}
    )


@personnel_requis
def detail(request, contrat_id):
    contrat = get_object_or_404(
        Contrat.objects.select_related("client", "bien"), pk=contrat_id
    )
    return render(
        request,
        "contrats/detail.html",
        {
            "contrat": contrat,
            "paiements": contrat.paiements.all(),
            "formulaire_paiement": PaiementForm(),
            "formulaire_saisie": SaisieForm(),
        },
    )


@login_required
def telecharger_recu(request, contrat_id, paiement_id):
    paiements = Paiement.objects.select_related(
        "contrat__client", "contrat__bien"
    ).filter(contrat_id=contrat_id)
    if not request.user.is_staff:
        paiements = paiements.filter(contrat__client__utilisateur=request.user)
    paiement = get_object_or_404(paiements, pk=paiement_id)

    identite_site = ConfigurationSite.objects.filter(pk=1).first()
    nom_site = identite_site.nom if identite_site else "Mete nan plàn"
    dossier_polices = Path(reportlab.__file__).resolve().parent / "fonts"
    if "TicketVera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("TicketVera", dossier_polices / "Vera.ttf"))
    if "TicketVeraBold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont("TicketVeraBold", dossier_polices / "VeraBd.ttf")
        )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReceiptTitle",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#1d2a3a"),
            alignment=1,
            fontName="TicketVeraBold",
            fontSize=12,
            leading=15,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReceiptLabel",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#455469"),
            fontName="TicketVera",
            fontSize=7,
            leading=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReceiptValue",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#1d2a3a"),
            fontName="TicketVeraBold",
            fontSize=7,
            leading=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReceiptSiteInfo",
            parent=styles["BodyText"],
            alignment=1,
            textColor=colors.HexColor("#455469"),
            fontName="TicketVera",
            fontSize=6.5,
            leading=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReceiptSection",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#1d2a3a"),
            fontName="TicketVeraBold",
            fontSize=7.5,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReceiptTotal",
            parent=styles["BodyText"],
            alignment=1,
            textColor=colors.HexColor("#1d2a3a"),
            fontName="TicketVeraBold",
            fontSize=10,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReceiptFooter",
            parent=styles["BodyText"],
            alignment=1,
            textColor=colors.HexColor("#455469"),
            fontName="TicketVera",
            fontSize=6,
            leading=8,
        )
    )
    contrat = paiement.contrat
    bien = contrat.bien
    largeur_ticket = 80 * mm
    largeur_contenu = largeur_ticket - 14 * mm
    contenu = []
    if identite_site and identite_site.logo:
        try:
            with identite_site.logo.open("rb") as fichier_logo:
                contenu_logo = fichier_logo.read()
            lecteur_logo = ImageReader(BytesIO(contenu_logo))
            largeur_logo, hauteur_logo = lecteur_logo.getSize()
            facteur_logo = min(24 * mm / largeur_logo, 24 * mm / hauteur_logo)
            image_logo = Image(
                BytesIO(contenu_logo),
                width=largeur_logo * facteur_logo,
                height=hauteur_logo * facteur_logo,
            )
            image_logo.hAlign = "CENTER"
            contenu.extend([image_logo, Spacer(1, 3 * mm)])
        except (OSError, ValueError):
            pass

    contenu.extend(
        [
            Paragraph(escape(nom_site), styles["ReceiptTitle"]),
            Spacer(1, 1.5 * mm),
        ]
    )
    if identite_site:
        for information_site in (
            identite_site.slogan,
            identite_site.adresse,
            identite_site.telephone,
            identite_site.email,
        ):
            if information_site:
                contenu.append(
                    Paragraph(escape(information_site), styles["ReceiptSiteInfo"])
                )

    contenu.extend(
        [
            Spacer(1, 3 * mm),
            HRFlowable(
                width="100%",
                thickness=0.8,
                color=colors.HexColor("#1d2a3a"),
                dash=(2, 2),
            ),
            Spacer(1, 3 * mm),
            Paragraph("REÇU DE PAIEMENT", styles["ReceiptTitle"]),
            Paragraph(f"N° R-{paiement.pk:06d}", styles["ReceiptSiteInfo"]),
            Paragraph(
                paiement.recu_le.strftime("%d/%m/%Y à %H:%M"),
                styles["ReceiptSiteInfo"],
            ),
            Spacer(1, 3 * mm),
            Paragraph("CLIENT ET BIEN", styles["ReceiptSection"]),
            Spacer(1, 1.5 * mm),
        ]
    )
    lignes_client = [
        ("Client", str(contrat.client)),
        ("Téléphone", contrat.client.telephone or "Non renseigné"),
        ("Contrat", contrat.numero),
        ("Bien", f"{bien.marque} {bien.modele}"),
        ("N° série", bien.numero_serie or "Non renseigné"),
    ]
    contenu.append(
        Table(
            [
                [
                    Paragraph(escape(libelle), styles["ReceiptLabel"]),
                    Paragraph(escape(valeur), styles["ReceiptValue"]),
                ]
                for libelle, valeur in lignes_client
            ],
            colWidths=[20 * mm, largeur_contenu - 20 * mm],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#d4dce1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            ),
        )
    )
    contenu.extend(
        [
            Spacer(1, 3 * mm),
            Paragraph("DÉTAIL DU RÈGLEMENT", styles["ReceiptSection"]),
            Spacer(1, 1.5 * mm),
        ]
    )
    lignes_paiement = [
        ("Opération", paiement.get_type_display()),
        ("Intérêts", f"{paiement.montant_interet} {contrat.devise}"),
        ("Capital remboursé", f"{paiement.montant_capital} {contrat.devise}"),
    ]
    if paiement.devise_recue != contrat.devise:
        lignes_paiement.append(("Taux de change", f"{paiement.taux_change}"))
    contenu.append(
        Table(
            [
                [
                    Paragraph(escape(libelle), styles["ReceiptLabel"]),
                    Paragraph(escape(valeur), styles["ReceiptValue"]),
                ]
                for libelle, valeur in lignes_paiement
            ],
            colWidths=[20 * mm, largeur_contenu - 20 * mm],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#d4dce1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            ),
        )
    )
    contenu.extend(
        [
            Spacer(1, 3 * mm),
            Table(
                [
                    [Paragraph("TOTAL REÇU", styles["ReceiptSection"])],
                    [
                        Paragraph(
                            f"{paiement.montant} {paiement.devise_recue}",
                            styles["ReceiptTotal"],
                        )
                    ],
                ],
                colWidths=[largeur_contenu],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eaf1ef")),
                        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#1d2a3a")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
                    ]
                ),
            ),
            Spacer(1, 4 * mm),
            HRFlowable(
                width="100%",
                thickness=0.8,
                color=colors.HexColor("#1d2a3a"),
                dash=(2, 2),
            ),
            Spacer(1, 2 * mm),
            Paragraph("Document généré par le système", styles["ReceiptFooter"]),
        ]
    )
    signature_path = settings.BASE_DIR / "static" / "images" / "directeur.png"
    signature_incluse = False
    if signature_path.is_file():
        try:
            with signature_path.open("rb") as fichier_signature:
                contenu_signature = fichier_signature.read()
            lecteur_signature = ImageReader(BytesIO(contenu_signature))
            largeur_signature, hauteur_signature = lecteur_signature.getSize()
            facteur_signature = min(
                44 * mm / largeur_signature,
                16 * mm / hauteur_signature,
            )
            image_signature = Image(
                BytesIO(contenu_signature),
                width=largeur_signature * facteur_signature,
                height=hauteur_signature * facteur_signature,
            )
            image_signature.hAlign = "CENTER"
            contenu.extend(
                [
                    Paragraph("Signature du personnel", styles["ReceiptFooter"]),
                    image_signature,
                ]
            )
            signature_incluse = True
        except (OSError, ValueError):
            pass
    if not signature_incluse:
        contenu.append(
            Paragraph(
                "Signature du personnel : __________________",
                styles["ReceiptFooter"],
            )
        )

    fichier = BytesIO()
    document = SimpleDocTemplate(
        fichier,
        pagesize=(largeur_ticket, 300 * mm),
        rightMargin=7 * mm,
        leftMargin=7 * mm,
        topMargin=7 * mm,
        bottomMargin=7 * mm,
        title=f"Reçu R-{paiement.pk:06d}",
        author=nom_site,
        pageCompression=0,
    )
    document.build(contenu)
    reponse = HttpResponse(fichier.getvalue(), content_type="application/pdf")
    reponse["Content-Disposition"] = f'attachment; filename="recu-{paiement.pk}.pdf"'
    reponse["X-Content-Type-Options"] = "nosniff"
    return reponse


@login_required
def telecharger_document_contrat(request, contrat_id):
    contrats = Contrat.objects.select_related("client", "bien")
    if not request.user.is_staff:
        contrats = contrats.filter(client__utilisateur=request.user)
    contrat = get_object_or_404(contrats, pk=contrat_id)

    identite_site = ConfigurationSite.objects.filter(pk=1).first()
    nom_site = identite_site.nom if identite_site else "Mete nan plàn"
    dossier_polices = Path(reportlab.__file__).resolve().parent / "fonts"
    if "TicketVera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("TicketVera", dossier_polices / "Vera.ttf"))
    if "TicketVeraBold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont("TicketVeraBold", dossier_polices / "VeraBd.ttf")
        )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="PledgeTitle",
            parent=styles["Title"],
            fontName="TicketVeraBold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#1d2a3a"),
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PledgeHeading",
            parent=styles["Heading2"],
            fontName="TicketVeraBold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#1d2a3a"),
            spaceBefore=2 * mm,
            spaceAfter=1 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PledgeBody",
            parent=styles["BodyText"],
            fontName="TicketVera",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#1d2a3a"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="PledgeLabel",
            parent=styles["BodyText"],
            fontName="TicketVera",
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#455469"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="PledgeValue",
            parent=styles["BodyText"],
            fontName="TicketVeraBold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1d2a3a"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="PledgeSmall",
            parent=styles["BodyText"],
            fontName="TicketVera",
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#455469"),
            alignment=1,
        )
    )

    client = contrat.client
    bien = contrat.bien
    largeur_page = 210 * mm
    largeur_contenu = largeur_page - 36 * mm
    contenu = []
    if identite_site and identite_site.logo:
        try:
            with identite_site.logo.open("rb") as fichier_logo:
                contenu_logo = fichier_logo.read()
            lecteur_logo = ImageReader(BytesIO(contenu_logo))
            largeur_logo, hauteur_logo = lecteur_logo.getSize()
            facteur_logo = min(35 * mm / largeur_logo, 18 * mm / hauteur_logo)
            logo = Image(
                BytesIO(contenu_logo),
                width=largeur_logo * facteur_logo,
                height=hauteur_logo * facteur_logo,
            )
            logo.hAlign = "CENTER"
            contenu.append(logo)
        except (OSError, ValueError):
            pass

    contenu.append(Paragraph(escape(nom_site), styles["PledgeTitle"]))
    if identite_site:
        informations_site = [
            identite_site.slogan,
            identite_site.adresse,
            identite_site.telephone,
            identite_site.email,
        ]
        texte_site = "<br/>".join(
            escape(information) for information in informations_site if information
        )
        if texte_site:
            contenu.append(Paragraph(texte_site, styles["PledgeSmall"]))
    contenu.extend(
        [
            Spacer(1, 3 * mm),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1d2a3a")),
            Spacer(1, 2 * mm),
            Paragraph("CONTRAT DE MISE EN GAGE", styles["PledgeTitle"]),
            Paragraph(
                f"Référence {escape(contrat.numero)} · préparé le "
                f"{timezone.localtime():%d/%m/%Y à %H:%M}",
                styles["PledgeSmall"],
            ),
            Paragraph(
                "Document à relire avec les deux parties et à signer avant la remise du capital.",
                styles["PledgeBody"],
            ),
            Paragraph("1. IDENTITÉ DU CLIENT", styles["PledgeHeading"]),
        ]
    )

    def tableau(lignes):
        return Table(
            [
                [
                    Paragraph(escape(libelle), styles["PledgeLabel"]),
                    Paragraph(
                        escape(str(valeur or "Non renseigné")), styles["PledgeValue"]
                    ),
                ]
                for libelle, valeur in lignes
            ],
            colWidths=[48 * mm, largeur_contenu - 48 * mm],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d4dce1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                ]
            ),
        )

    contenu.append(
        tableau(
            [
                ("Nom complet", str(client)),
                ("Téléphone", client.telephone),
                ("NIF / CIN", client.numero_identite),
                ("Adresse", client.adresse),
            ]
        )
    )
    contenu.append(Paragraph("2. DESCRIPTION DU BIEN REMIS", styles["PledgeHeading"]))
    contenu.append(
        tableau(
            [
                ("Catégorie", bien.get_categorie_display()),
                ("Marque et modèle", f"{bien.marque} {bien.modele}"),
                ("Numéro de série", bien.numero_serie),
                ("État et description", bien.description),
                ("Accessoires remis", bien.accessoires),
                ("Preuve de propriété", bien.preuve_propriete),
            ]
        )
    )
    contenu.append(Paragraph("3. CONDITIONS FINANCIÈRES", styles["PledgeHeading"]))
    contenu.append(
        tableau(
            [
                ("Capital convenu", f"{contrat.capital_initial} {contrat.devise}"),
                ("Taux d’intérêt mensuel", f"{contrat.taux_mensuel} %"),
                (
                    "Intérêt mensuel calculé à ce jour",
                    f"{contrat.interet_mensuel} {contrat.devise}",
                ),
                ("Date de début", contrat.date_debut.strftime("%d/%m/%Y")),
                (
                    "Échéance enregistrée",
                    (
                        contrat.date_echeance.strftime("%d/%m/%Y")
                        if contrat.date_echeance
                        else "Non définie"
                    ),
                ),
                ("Délai de grâce", f"{contrat.jours_de_grace} jours"),
            ]
        )
    )
    contenu.extend(
        [
            Paragraph("4. ACCORD DES PARTIES", styles["PledgeHeading"]),
            Paragraph(
                "Le client reconnaît avoir remis le bien décrit ci-dessus en garantie du capital convenu. "
                "Les paiements et toute prolongation doivent être enregistrés par le personnel. "
                f"L’échéance enregistrée est le {contrat.date_echeance:%d/%m/%Y} et le délai de grâce prévu est de "
                f"{contrat.jours_de_grace} jours. À l’issue de ce délai, les suites applicables sont celles "
                "acceptées par les parties et permises par la réglementation en vigueur. Ce document ne transfère "
                "pas automatiquement la propriété du bien.",
                styles["PledgeBody"],
            ),
            Spacer(1, 3 * mm),
        ]
    )

    signature_personnel = [
        Paragraph("LE PERSONNEL", styles["PledgeSmall"]),
        Spacer(1, 2 * mm),
    ]
    signature_path = settings.BASE_DIR / "static" / "images" / "directeur.png"
    if signature_path.is_file():
        try:
            contenu_signature = signature_path.read_bytes()
            lecteur_signature = ImageReader(BytesIO(contenu_signature))
            largeur_signature, hauteur_signature = lecteur_signature.getSize()
            facteur_signature = min(
                55 * mm / largeur_signature,
                20 * mm / hauteur_signature,
            )
            signature_personnel.append(
                Image(
                    BytesIO(contenu_signature),
                    width=largeur_signature * facteur_signature,
                    height=hauteur_signature * facteur_signature,
                )
            )
        except (OSError, ValueError):
            signature_personnel.append(Spacer(1, 15 * mm))
    else:
        signature_personnel.append(Spacer(1, 15 * mm))
    signature_personnel.extend(
        [
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1d2a3a")),
            Paragraph("Nom et signature", styles["PledgeSmall"]),
        ]
    )
    signature_client = [
        Paragraph("LE CLIENT", styles["PledgeSmall"]),
        Spacer(1, 14 * mm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1d2a3a")),
        Paragraph("Nom et signature", styles["PledgeSmall"]),
    ]
    contenu.append(
        Table(
            [[signature_personnel, signature_client]],
            colWidths=[largeur_contenu / 2, largeur_contenu / 2],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                ]
            ),
        )
    )

    fichier = BytesIO()
    document = SimpleDocTemplate(
        fichier,
        pagesize=(210 * mm, 297 * mm),
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Contrat de mise en gage {contrat.numero}",
        author=nom_site,
        pageCompression=0,
    )
    document.build(contenu)
    reponse = HttpResponse(fichier.getvalue(), content_type="application/pdf")
    reponse["Content-Disposition"] = (
        f'attachment; filename="contrat-{contrat.numero}.pdf"'
    )
    reponse["X-Content-Type-Options"] = "nosniff"
    return reponse


@personnel_requis
def payer(request, contrat_id):
    contrat = get_object_or_404(Contrat, pk=contrat_id)
    formulaire = PaiementForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        try:
            paiement = enregistrer_paiement(
                contrat.pk,
                formulaire.cleaned_data["type"],
                formulaire.cleaned_data["capital_verse"],
                formulaire.cleaned_data["note"],
                formulaire.cleaned_data["devise_recue"],
                formulaire.cleaned_data["taux_change"],
            )
        except ValidationError as erreur:
            messages.error(request, " ".join(erreur.messages))
        else:
            messages.success(
                request, f"Paiement de {paiement.montant} {contrat.devise} enregistré."
            )
    return redirect("contrats:detail", contrat_id=contrat.pk)


@personnel_requis
def saisir(request, contrat_id):
    contrat = get_object_or_404(Contrat, pk=contrat_id)
    formulaire = SaisieForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        try:
            saisir_un_bien(contrat.pk, formulaire.cleaned_data["prix_liquidation"])
        except ValidationError as erreur:
            messages.error(request, " ".join(erreur.messages))
        else:
            messages.success(
                request, "Le bien est transféré à l'inventaire de revente."
            )
            return redirect("inventaire:liste")
    return redirect("contrats:detail", contrat_id=contrat.pk)
