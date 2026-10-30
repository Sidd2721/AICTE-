"""Server-side PDF Statement Report Generation using ReportLab.

Hard rules and requirements:
- Prototype header: "AICTE FDR Portal (prototype, PS 26265)"
- Visible disclaimer: "Synthetic data, SIMULATED bank and email, DEMO rule values. Not an official document."
- Watermark: Light diagonal "DEMO"
- Footer: Page numbers, generation timestamp, demo clock date
- Currency format: "Rs." (standard ReportLab Helvetica lacks the ₹ symbol)
- RLS / Persona Scoping: Enforced matching existing report endpoints
"""

import io
from datetime import UTC, datetime, timedelta
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlmodel import Session, col, select

from app.domain.clock import now as clock_now
from app.domain.clock import today as clock_today
from app.domain.trust import Confirmation as TrustConfirmation
from app.domain.trust import badge
from app.models import Confirmation, Document, Institution, Instrument, Obligation, User


def format_paise_rs(paise: int | None) -> str:
    """Format paise to Indian Rupee string using 'Rs.' prefix without float rounding."""
    if paise is None:
        return "—"
    sign = "-" if paise < 0 else ""
    abs_paise = abs(paise)
    rupees = abs_paise // 100
    rem_paise = abs_paise % 100
    return f"{sign}Rs. {rupees:,}.{rem_paise:02d}"


class NumberedDemoCanvas(canvas.Canvas):  # type: ignore[misc]
    """Two-pass canvas drawing DEMO watermark, official prototype header, disclaimer, and page numbers."""

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
        # 1. Light diagonal DEMO watermark in center of page
        self.saveState()
        self.setFont("Helvetica-Bold", 68)
        self.setFillColor(colors.HexColor("#E2E8F0"))
        self.translate(297, 420)
        self.rotate(45)
        self.drawCentredString(0, 0, "DEMO")
        self.restoreState()

        # 2. Header
        self.saveState()
        self.setFont("Helvetica-Bold", 9)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawString(36, 810, "AICTE FDR Portal (prototype, PS 26265)")

        self.setFont("Helvetica-Oblique", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(
            36,
            798,
            "Synthetic data, SIMULATED bank and email, DEMO rule values. Not an official document.",
        )
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 792, 559, 792)

        # 3. Footer
        self.line(36, 40, 559, 40)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        gen_time = clock_now().strftime("%Y-%m-%d %H:%M:%S UTC")
        demo_date = clock_today().isoformat()
        self.drawString(36, 28, f"Generated: {gen_time} | Demo Date: {demo_date}")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(559, 28, page_str)
        self.restoreState()


def _hydrate_badge_for_pdf(inst: Instrument, session: Session) -> str:
    confs = session.exec(
        select(Confirmation)
        .where(Confirmation.instrument_id == inst.id)
        .where(col(Confirmation.revoked).is_(False))
    ).all()
    trust_confs = [
        TrustConfirmation(
            fields=c.fields or {},
            method=c.method,
            confirmed_at=c.confirmed_at or datetime.now(UTC),
            expires_at=c.expires_at or datetime.now(UTC),
            revoked=c.revoked,
        )
        for c in confs
    ]
    return badge(
        {
            "ref_no": inst.ref_no,
            "bank_code": inst.bank_code,
            "amount_paise": inst.amount_paise,
            "maturity_date": str(inst.maturity_date),
        },
        trust_confs,
        datetime.now(UTC),
    )


def generate_reports_pdf(
    session: Session,
    current_user: User,
    report_type: str | None = None,
) -> tuple[bytes, str, int]:
    """Generate statement report PDF bytes, filename, and total item count.

    Respects persona RLS context and query filtering matching existing endpoints.
    """
    normalized_type = (
        report_type.strip().lower().replace("_", "-") if report_type else None
    )
    if normalized_type in ("all", "full", ""):
        normalized_type = None

    today_val = clock_today()
    cutoff_90 = today_val + timedelta(days=90)

    # Base query filters
    user_region = current_user.region if current_user.role == "regional" else None
    user_inst_id = (
        current_user.institution_id if current_user.role == "institution" else None
    )

    # Section 1: Pending Verifications
    pv_query = select(Instrument).where(Instrument.lifecycle == "pending")
    if user_inst_id:
        pv_query = pv_query.where(Instrument.institution_id == user_inst_id)
    elif user_region:
        pv_query = pv_query.where(Instrument.region == user_region)
    pv_items = session.exec(pv_query).all()

    # Section 2: Upcoming Maturities
    um_query = (
        select(Instrument)
        .where(Instrument.lifecycle == "active")
        .where(Instrument.maturity_date <= cutoff_90)
    )
    if user_inst_id:
        um_query = um_query.where(Instrument.institution_id == user_inst_id)
    elif user_region:
        um_query = um_query.where(Instrument.region == user_region)
    um_items = session.exec(um_query).all()

    # Section 3: Missing Documents
    md_query = select(Instrument).where(
        col(Instrument.lifecycle).in_(["pending", "active"])
    )
    if user_inst_id:
        md_query = md_query.where(Instrument.institution_id == user_inst_id)
    elif user_region:
        md_query = md_query.where(Instrument.region == user_region)
    all_cand_md = session.exec(md_query).all()
    md_rows: list[dict[str, Any]] = []
    for inst in all_cand_md:
        docs = session.exec(
            select(Document).where(Document.instrument_id == inst.id)
        ).all()
        doc_kinds = {d.kind for d in docs}
        missing = [k for k in ("fdr_scan", "payment_proof") if k not in doc_kinds]
        if missing:
            inst_obj = session.get(Institution, inst.institution_id)
            md_rows.append(
                {
                    "inst": inst,
                    "institution_name": inst_obj.name if inst_obj else "—",
                    "missing": missing,
                }
            )

    # Section 4: Cases Needing Intervention
    ci_query = select(Instrument).where(
        col(Instrument.lifecycle).in_(["pending", "active", "matured"])
    )
    if user_inst_id:
        ci_query = ci_query.where(Instrument.institution_id == user_inst_id)
    elif user_region:
        ci_query = ci_query.where(Instrument.region == user_region)
    all_cand_ci = session.exec(ci_query).all()
    ci_rows: list[dict[str, Any]] = []
    for inst in all_cand_ci:
        reasons: list[str] = []
        if inst.lifecycle == "matured":
            reasons.append("Instrument reached maturity without renewal or release")
        obs = session.exec(
            select(Obligation)
            .where(Obligation.instrument_id == inst.id)
            .where(Obligation.status == "open")
            .where(Obligation.due_date < today_val)
        ).all()
        for o in obs:
            reasons.append(f"Overdue obligation: {o.kind} (due {o.due_date})")
        if reasons:
            ci_rows.append({"inst": inst, "reasons": reasons})

    # Determine which sections to include
    include_pv = normalized_type is None or normalized_type == "pending-verifications"
    include_um = normalized_type is None or normalized_type == "upcoming-maturities"
    include_md = normalized_type is None or normalized_type == "missing-documents"
    include_ci = (
        normalized_type is None or normalized_type == "cases-needing-intervention"
    )

    total_rows = 0
    if include_pv:
        total_rows += len(pv_items)
    if include_um:
        total_rows += len(um_items)
    if include_md:
        total_rows += len(md_rows)
    if include_ci:
        total_rows += len(ci_rows)

    # Document assembly
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        pageCompression=0,
        leftMargin=36,
        rightMargin=36,
        topMargin=56,
        bottomMargin=54,
    )

    sample_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=sample_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=sample_styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    section_h2 = ParagraphStyle(
        "SectionH2",
        parent=sample_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=8,
        spaceAfter=6,
    )
    cell_body = ParagraphStyle(
        "CellBody",
        parent=sample_styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E293B"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )
    empty_note = ParagraphStyle(
        "EmptyNote",
        parent=sample_styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=8,
    )

    story: list[Any] = []

    # Title & Metadata
    if normalized_type is None:
        title_text = "Comprehensive Statement Report"
    elif normalized_type == "pending-verifications":
        title_text = "Statement Report: Pending Verifications"
    elif normalized_type == "upcoming-maturities":
        title_text = "Statement Report: Upcoming Maturities"
    elif normalized_type == "missing-documents":
        title_text = "Statement Report: Missing Documents"
    elif normalized_type == "cases-needing-intervention":
        title_text = "Statement Report: Cases Needing Intervention"
    else:
        title_text = f"Statement Report: {normalized_type}"

    story.append(Paragraph(title_text, title_style))

    scope_str = (
        f"Region: {user_region}"
        if user_region
        else "Region: All (National Scope)"
        if current_user.role != "institution"
        else "Scope: Institution"
    )
    actor_str = f"Exported by: {current_user.email} ({current_user.role}) | {scope_str}"
    story.append(Paragraph(actor_str, subtitle_style))

    # KPI summary table
    summary_data = [
        [
            Paragraph("<b>Pending Verifications</b>", cell_body),
            Paragraph("<b>Upcoming Maturities (≤90d)</b>", cell_body),
            Paragraph("<b>Missing Documents</b>", cell_body),
            Paragraph("<b>Cases Needing Intervention</b>", cell_body),
        ],
        [
            Paragraph(f"<font size=10><b>{len(pv_items)}</b></font>", cell_bold),
            Paragraph(f"<font size=10><b>{len(um_items)}</b></font>", cell_bold),
            Paragraph(f"<font size=10><b>{len(md_rows)}</b></font>", cell_bold),
            Paragraph(f"<font size=10><b>{len(ci_rows)}</b></font>", cell_bold),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[130, 131, 131, 131])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Standard table header style
    def table_header_style() -> list[Any]:
        return [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#F8FAFC")],
            ),
        ]

    # Section 1: Pending Verifications
    if include_pv:
        story.append(
            Paragraph(f"1. Pending Verifications ({len(pv_items)})", section_h2)
        )
        if not pv_items:
            story.append(
                Paragraph("No instruments currently pending verification.", empty_note)
            )
        else:
            pv_table_data = [
                [
                    Paragraph("<b>Ref No</b>", cell_bold),
                    Paragraph("<b>Bank</b>", cell_bold),
                    Paragraph("<b>Region</b>", cell_bold),
                    Paragraph("<b>Amount</b>", cell_bold),
                    Paragraph("<b>Issue Date</b>", cell_bold),
                    Paragraph("<b>Maturity Date</b>", cell_bold),
                    Paragraph("<b>Badge</b>", cell_bold),
                ]
            ]
            for inst in pv_items:
                b_str = _hydrate_badge_for_pdf(inst, session)
                pv_table_data.append(
                    [
                        Paragraph(inst.ref_no, cell_body),
                        Paragraph(inst.bank_code or "—", cell_body),
                        Paragraph(inst.region, cell_body),
                        Paragraph(format_paise_rs(inst.amount_paise), cell_body),
                        Paragraph(str(inst.issue_date), cell_body),
                        Paragraph(str(inst.maturity_date), cell_body),
                        Paragraph(b_str, cell_body),
                    ]
                )
            t_pv = Table(pv_table_data, colWidths=[115, 45, 45, 105, 74, 74, 65])
            t_pv.setStyle(TableStyle(table_header_style()))
            story.append(t_pv)
        story.append(Spacer(1, 10))

    # Section 2: Upcoming Maturities
    if include_um:
        story.append(Paragraph(f"2. Upcoming Maturities ({len(um_items)})", section_h2))
        if not um_items:
            story.append(
                Paragraph("No active instruments maturing within 90 days.", empty_note)
            )
        else:
            um_table_data = [
                [
                    Paragraph("<b>Ref No</b>", cell_bold),
                    Paragraph("<b>Bank</b>", cell_bold),
                    Paragraph("<b>Region</b>", cell_bold),
                    Paragraph("<b>Amount</b>", cell_bold),
                    Paragraph("<b>Maturity Date</b>", cell_bold),
                    Paragraph("<b>Days Remaining</b>", cell_bold),
                ]
            ]
            for inst in um_items:
                days_left = (inst.maturity_date - today_val).days
                um_table_data.append(
                    [
                        Paragraph(inst.ref_no, cell_body),
                        Paragraph(inst.bank_code or "—", cell_body),
                        Paragraph(inst.region, cell_body),
                        Paragraph(format_paise_rs(inst.amount_paise), cell_body),
                        Paragraph(str(inst.maturity_date), cell_body),
                        Paragraph(f"{days_left}d", cell_body),
                    ]
                )
            t_um = Table(um_table_data, colWidths=[125, 50, 48, 120, 90, 90])
            t_um.setStyle(TableStyle(table_header_style()))
            story.append(t_um)
        story.append(Spacer(1, 10))

    # Section 3: Missing Documents
    if include_md:
        story.append(Paragraph(f"3. Missing Documents ({len(md_rows)})", section_h2))
        if not md_rows:
            story.append(
                Paragraph(
                    "All instruments have mandatory documents present.", empty_note
                )
            )
        else:
            md_table_data = [
                [
                    Paragraph("<b>Ref No</b>", cell_bold),
                    Paragraph("<b>Region</b>", cell_bold),
                    Paragraph("<b>Institution</b>", cell_bold),
                    Paragraph("<b>Missing Documents</b>", cell_bold),
                ]
            ]
            for row in md_rows:
                inst = row["inst"]
                missing_str = ", ".join(row["missing"])
                md_table_data.append(
                    [
                        Paragraph(inst.ref_no, cell_body),
                        Paragraph(inst.region, cell_body),
                        Paragraph(row["institution_name"], cell_body),
                        Paragraph(missing_str, cell_body),
                    ]
                )
            t_md = Table(md_table_data, colWidths=[130, 48, 185, 160])
            t_md.setStyle(TableStyle(table_header_style()))
            story.append(t_md)
        story.append(Spacer(1, 10))

    # Section 4: Cases Needing Intervention
    if include_ci:
        story.append(
            Paragraph(f"4. Cases Needing Intervention ({len(ci_rows)})", section_h2)
        )
        if not ci_rows:
            story.append(
                Paragraph(
                    "No cases currently requiring officer intervention.", empty_note
                )
            )
        else:
            ci_table_data = [
                [
                    Paragraph("<b>Ref No</b>", cell_bold),
                    Paragraph("<b>Region</b>", cell_bold),
                    Paragraph("<b>Lifecycle</b>", cell_bold),
                    Paragraph("<b>Intervention Reasons</b>", cell_bold),
                ]
            ]
            for row in ci_rows:
                inst = row["inst"]
                reasons_str = "; ".join(row["reasons"])
                ci_table_data.append(
                    [
                        Paragraph(inst.ref_no, cell_body),
                        Paragraph(inst.region, cell_body),
                        Paragraph(inst.lifecycle, cell_body),
                        Paragraph(reasons_str, cell_body),
                    ]
                )
            t_ci = Table(ci_table_data, colWidths=[130, 48, 65, 280])
            t_ci.setStyle(TableStyle(table_header_style()))
            story.append(t_ci)
        story.append(Spacer(1, 10))

    # Build PDF
    doc.build(story, canvasmaker=NumberedDemoCanvas)
    pdf_bytes = buf.getvalue()

    filename_tag = normalized_type or "full"
    date_str = today_val.isoformat()
    filename = f"statement_report_{filename_tag}_{date_str}.pdf"

    return pdf_bytes, filename, total_rows
