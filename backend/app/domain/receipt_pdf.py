"""Demo Release Receipt PDF Generator.

Generates a standalone PDF receipt for released instruments using ReportLab.
Follows all project guidelines:
- Title: "Demo release receipt"
- Watermark: Light diagonal "DEMO"
- Disclaimer: "Demo release receipt. Synthetic data. Not a bank instrument; no funds are released."
- Verified fields: only claims in the signed token (receipt_id, instrument_hash, path, iat in IST, kid)
- Informational box: instrument ref no, institution name, bank code, amount formatted as Rs.
- Monospace small text: full token
- Plain text verify URL + ReportLab built-in QrCodeWidget
- Total size < 300 KB, starts with %PDF-
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.graphics.barcode.qr import QrCodeWidget  # type: ignore[import-untyped]
from reportlab.graphics.shapes import Drawing  # type: ignore[import-untyped]
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.domain.receipt import verify_release_receipt

IST_TZ = ZoneInfo("Asia/Kolkata")


def format_paise_to_inr(paise: int | None) -> str:
    """Format paise to Indian Rupee string using 'Rs.' prefix and Indian numbering grouping."""
    if paise is None:
        return "—"
    sign = "-" if paise < 0 else ""
    abs_paise = abs(paise)
    rupees = abs_paise // 100
    rem_paise = abs_paise % 100
    s = str(rupees)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        chunks: list[str] = []
        while len(rest) > 2:
            chunks.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            chunks.insert(0, rest)
        grouped = ",".join(chunks) + "," + last3
    else:
        grouped = s
    return f"{sign}Rs. {grouped}.{rem_paise:02d}"


class ReceiptDemoCanvas(canvas.Canvas):  # type: ignore[misc]
    """Two-pass canvas drawing DEMO watermark, official prototype header, and disclaimer footer."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int) -> None:
        # 1. Light diagonal DEMO watermark in center
        self.saveState()
        self.setFont("Helvetica-Bold", 68)
        self.setFillColor(colors.HexColor("#F1F5F9"))
        self.translate(297, 420)
        self.rotate(45)
        self.drawCentredString(0, 0, "DEMO")
        self.restoreState()

        # 2. Header
        self.saveState()
        self.setFont("Helvetica-Bold", 8.5)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawString(36, 810, "AICTE FDR Portal (prototype, PS 26265)")

        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(559, 810, "Demo Release Verification Artifact")

        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 802, 559, 802)

        # 3. Footer
        self.line(36, 36, 559, 36)
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(
            36,
            24,
            "Synthetic data, SIMULATED bank and email, DEMO rule values. Not an official document.",
        )
        self.drawRightString(559, 24, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


def build_release_receipt_pdf(
    *,
    token: str,
    instrument_ref_no: str,
    institution_name: str,
    bank_code: str,
    amount_paise: int,
) -> bytes:
    """Build and return binary PDF bytes for a demo release receipt."""
    # Verify token cryptographically and extract claims
    claims = verify_release_receipt(token)
    rid = str(claims.get("receipt_id", "—"))
    inst_hash = str(claims.get("instrument_hash", "—"))
    path_val = str(claims.get("path", "—"))
    kid_val = str(claims.get("kid", "—"))
    iat_val = claims.get("iat")

    if isinstance(iat_val, (int, float)):
        dt_ist = datetime.fromtimestamp(iat_val, tz=IST_TZ)
        iat_display = dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    else:
        iat_display = "—"

    # Verification URL
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    verify_url = f"{base_url}/verify-receipt#t={token}"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=44,
        pageCompression=0,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
    )
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )
    r3_disclaimer_style = ParagraphStyle(
        "R3Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#991B1B"),
        alignment=1,  # Center
    )
    box_header_style = ParagraphStyle(
        "BoxHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
    )
    label_style = ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    val_style = ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )
    val_mono = ParagraphStyle(
        "FieldValueMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )
    note_style = ParagraphStyle(
        "BoxNote",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748B"),
    )
    token_style = ParagraphStyle(
        "TokenBlock",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=6,
        leading=8,
        textColor=colors.HexColor("#334155"),
        wordWrap="CJK",
    )
    url_style = ParagraphStyle(
        "VerifyUrlStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#1D4ED8"),
        wordWrap="CJK",
    )

    story: list[Any] = []

    # Title & Subtitle
    story.append(Paragraph("Demo release receipt", title_style))
    story.append(
        Paragraph(
            "Cryptographically Signed Release Receipt (RS256 Signature)",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 6))

    # R3 Notice Callout Box
    r3_text = Paragraph(
        "Demo release receipt. Synthetic data. Not a bank instrument; no funds are released.",
        r3_disclaimer_style,
    )
    r3_table = Table([[r3_text]], colWidths=[523])
    r3_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FCA5A5")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(r3_table)
    story.append(Spacer(1, 8))

    # Box 1: Verified Fields (Claims in Signed Token)
    verified_hdr = Paragraph(
        "<font color='#166534'><b>VERIFIED FIELDS</b> (Covered by Cryptographic Signature)</font>",
        box_header_style,
    )
    verified_rows: list[list[Any]] = [
        [verified_hdr, ""],
        [Paragraph("Receipt ID (receipt_id):", label_style), Paragraph(rid, val_mono)],
        [
            Paragraph("Instrument Hash (SHA-256):", label_style),
            Paragraph(inst_hash, val_mono),
        ],
        [
            Paragraph("Approved Release Path:", label_style),
            Paragraph(path_val, val_style),
        ],
        [
            Paragraph("Issued At (iat, IST):", label_style),
            Paragraph(iat_display, val_style),
        ],
        [
            Paragraph("Signing Key ID (kid):", label_style),
            Paragraph(kid_val, val_mono),
        ],
        [
            Paragraph(
                "These five fields are cryptographically signed by the portal's RS256 key.",
                note_style,
            ),
            "",
        ],
    ]
    verified_table = Table(verified_rows, colWidths=[175, 348])
    verified_table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("SPAN", (0, 6), (1, 6)),
                ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#ECFDF5")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86EFAC")),
                ("LINEBELOW", (0, 0), (1, 0), 0.75, colors.HexColor("#86EFAC")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(verified_table)
    story.append(Spacer(1, 7))

    # Box 2: Informational Fields (Context Not Covered by Signature)
    info_hdr = Paragraph(
        "<font color='#475569'><b>INFORMATIONAL</b> (Display context; not covered by digital signature)</font>",
        box_header_style,
    )
    info_rows: list[list[Any]] = [
        [info_hdr, ""],
        [
            Paragraph("Instrument Ref No:", label_style),
            Paragraph(instrument_ref_no, val_style),
        ],
        [
            Paragraph("Institution Name:", label_style),
            Paragraph(institution_name, val_style),
        ],
        [Paragraph("Bank Code:", label_style), Paragraph(bank_code, val_style)],
        [
            Paragraph("Deposit Amount:", label_style),
            Paragraph(format_paise_to_inr(amount_paise), val_style),
        ],
        [
            Paragraph(
                "Provided for portal human context; not asserted by the cryptographic signature.",
                note_style,
            ),
            "",
        ],
    ]
    info_table = Table(info_rows, colWidths=[175, 348])
    info_table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("SPAN", (0, 5), (1, 5)),
                ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("LINEBELOW", (0, 0), (1, 0), 0.75, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 7))

    # QR Code & Verification Link Section
    qr_size = 90
    qr_widget = QrCodeWidget(verify_url)
    qr_bounds = qr_widget.getBounds()
    qr_w = qr_bounds[2] - qr_bounds[0]
    qr_h = qr_bounds[3] - qr_bounds[1]
    scale_x = qr_size / qr_w if qr_w else 1
    scale_y = qr_size / qr_h if qr_h else 1
    qr_drawing = Drawing(qr_size, qr_size, transform=[scale_x, 0, 0, scale_y, 0, 0])
    qr_drawing.add(qr_widget)

    verify_instructions = [
        Paragraph("<b>Public Verification</b>", box_header_style),
        Spacer(1, 3),
        Paragraph(
            "Scan this QR code with any mobile device or open the verification link to check "
            "this receipt against AICTE's public signing key. Cryptographic verification proves "
            "the receipt was issued by the portal and has not been modified.",
            val_style,
        ),
        Spacer(1, 4),
        Paragraph("<b>Verification URL:</b>", label_style),
        Paragraph(verify_url, url_style),
    ]

    verification_table = Table(
        [[verify_instructions, qr_drawing]],
        colWidths=[420, 103],
    )
    verification_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(verification_table)
    story.append(Spacer(1, 6))

    # Full Token Monospace Block
    token_box_hdr = Paragraph(
        "<b>Signed Token (RS256 JWT)</b> — <i>Paste into the public verifier or offline CLI tool</i>",
        label_style,
    )
    token_content = Paragraph(token, token_style)
    token_table = Table([[token_box_hdr], [token_content]], colWidths=[523])
    token_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(KeepTogether([token_table]))

    doc.build(story, canvasmaker=ReceiptDemoCanvas)
    return buf.getvalue()
