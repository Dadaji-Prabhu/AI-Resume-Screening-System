from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from io import BytesIO
import os


# ── Color Palette ─────────────────────────────────────────
PRIMARY = colors.HexColor('#1a1a2e')
ACCENT = colors.HexColor('#4361ee')
LIGHT_BLUE = colors.HexColor('#e8ecff')
SUCCESS = colors.HexColor('#2ecc71')
LIGHT_GRAY = colors.HexColor('#f8f9fa')
BORDER_GRAY = colors.HexColor('#dee2e6')
TEXT_DARK = colors.HexColor('#212529')
TEXT_MUTED = colors.HexColor('#6c757d')
WHITE = colors.white

def generate_offer_letter_pdf(offer, candidate, company):
    """
    Generate a professional PDF offer letter.
    Returns BytesIO buffer.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Custom Styles ─────────────────────────────────────
    company_name_style = ParagraphStyle(
        'CompanyName',
        parent=styles['Normal'],
        fontSize=20,
        fontName='Helvetica-Bold',
        textColor=WHITE,
        alignment=TA_LEFT,
        spaceAfter=2,
    )
    company_sub_style = ParagraphStyle(
        'CompanySub',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=colors.HexColor('#a0b4e8'),
        alignment=TA_LEFT,
    )
    header_right_style = ParagraphStyle(
        'HeaderRight',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=colors.HexColor('#a0b4e8'),
        alignment=TA_RIGHT,
    )
    offer_title_style = ParagraphStyle(
        'OfferTitle',
        parent=styles['Normal'],
        fontSize=22,
        fontName='Helvetica-Bold',
        textColor=ACCENT,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=ACCENT,
        spaceAfter=6,
        spaceBefore=12,
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica',
        textColor=TEXT_DARK,
        leading=16,
        spaceAfter=6,
    )
    bold_body_style = ParagraphStyle(
        'BoldBody',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=TEXT_DARK,
        leading=16,
    )
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=TEXT_MUTED,
        leading=12,
    )
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=WHITE,
        alignment=TA_CENTER,
    )

    from django.utils import timezone
    date_str = offer.sent_at.strftime('%B %d, %Y')
    header_data = [
        [
            Paragraph(
                company.company_name.upper(),
                company_name_style
            ),
            Paragraph(
                f'Date: {date_str}<br/>'
                f'Ref: OL-{offer.id:04d}',
                header_right_style
            )
        ]
    ]
    header_table = Table(
        header_data,
        colWidths=[doc.width * 0.7, doc.width * 0.3]
    )
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 16),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    story.append(header_table)

    # Company sub-info
    company_info_data = [[
        Paragraph(
            f'<font color="#6c757d">'
            f'Industry: {company.industry} &nbsp;·&nbsp; '
            f'Size: {company.company_size} employees'
            f'</font>',
            ParagraphStyle(
                'ci', fontSize=8,
                fontName='Helvetica',
                textColor=TEXT_MUTED
            )
        ),
        Paragraph(
            f'<font color="#6c757d">'
            f'{company.website or "www.hireiq.com"}'
            f'</font>',
            ParagraphStyle(
                'cw', fontSize=8,
                fontName='Helvetica',
                textColor=TEXT_MUTED,
                alignment=TA_RIGHT
            )
        )
    ]]
    ci_table = Table(
        company_info_data,
        colWidths=[doc.width * 0.7, doc.width * 0.3]
    )
    ci_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(ci_table)
    story.append(Spacer(1, 0.4 * cm))

    story.append(
        Paragraph('OFFER OF EMPLOYMENT', offer_title_style)
    )
    story.append(
        HRFlowable(
            width='100%', thickness=2,
            color=ACCENT, spaceAfter=12
        )
    )

    # ── CONFIDENTIAL BADGE ────────────────────────────────
    conf_data = [[
        Paragraph(
            '🔒 CONFIDENTIAL DOCUMENT — '
            'For the addressee only',
            ParagraphStyle(
                'conf', fontSize=8,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#856404'),
                alignment=TA_CENTER,
            )
        )
    ]]
    conf_table = Table(conf_data, colWidths=[17 * cm])
    conf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1),
         colors.HexColor('#fff3cd')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('BOX', (0, 0), (-1, -1), 1,
         colors.HexColor('#ffc107')),
    ]))
    story.append(conf_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── CANDIDATE INFO ────────────────────────────────────
    story.append(Paragraph('Dear Candidate,', body_style))
    story.append(Spacer(1, 0.2 * cm))

    cand_info = [
        ['Full Name:', candidate.full_name],
        ['Email Address:', candidate.email],
        ['Contact Number:', candidate.phone or 'N/A'],
        ['Position Applied:', candidate.job.title],
    ]
    cand_table = Table(
        cand_info,
        colWidths=[4.5 * cm, 12.5 * cm]
    )
    cand_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BLUE),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(cand_table)
    story.append(Spacer(1, 0.3 * cm))

    # ── OPENING PARAGRAPH ─────────────────────────────────
    story.append(Paragraph(
        f'We are delighted to extend this offer of employment '
        f'to you for the position of '
        f'<b>{offer.designation}</b> at '
        f'<b>{company.company_name}</b>. '
        f'After a thorough evaluation of your qualifications, '
        f'experience, and interview performance, we are '
        f'confident that you will be a valuable addition to '
        f'our team.',
        body_style
    ))

    # ── OFFER DETAILS TABLE ───────────────────────────────
    story.append(
        Paragraph('📋 Offer Details', section_title_style)
    )

    from datetime import datetime, date
    joining_date_value = offer.joining_date
    if joining_date_value:
        if isinstance(joining_date_value, str):
            try:
                joining_date_value = datetime.strptime(
                    joining_date_value,
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                joining_date = joining_date_value
            else:
                joining_date = joining_date_value.strftime(
                    "%B %d, %Y"
                )
        elif isinstance(joining_date_value, date):
            joining_date = joining_date_value.strftime(
                "%B %d, %Y"
            )
        else:
            joining_date = str(joining_date_value)
    else:
        joining_date = "To be confirmed"

    offer_details = [
        ['OFFER DETAILS', ''],
        ['Designation', offer.designation],
        ['Department', candidate.job.title],
        ['Employment Type', 'Full-Time, Permanent'],
        ['Date of Joining', joining_date],
        ['Work Location', candidate.job.location or 'Company Premises'],
        ['Reporting To', company.hr_name],
    ]
    od_table = Table(
        offer_details,
        colWidths=[6 * cm, 11 * cm]
    )
    od_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BLUE),
        ('BACKGROUND', (1, 1), (1, -1), WHITE),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_DARK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [WHITE, LIGHT_GRAY]),
    ]))
    story.append(od_table)

    story.append(
        Paragraph('💰 Compensation & Benefits',
                  section_title_style)
    )

    comp_details = [
        ['COMPENSATION DETAILS', ''],
        ['Total CTC (Annual)', offer.salary_package],
        ['Probation Period', '6 Months'],
        ['Leave Entitlement', '18 Days per annum'],
        ['Medical Insurance', 'Covered under company policy'],
        ['Performance Review', 'Annual'],
    ]
    comp_table = Table(
        comp_details,
        colWidths=[6 * cm, 11 * cm]
    )
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SUCCESS),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BLUE),
        ('BACKGROUND', (1, 1), (1, -1), WHITE),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_DARK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [WHITE, LIGHT_GRAY]),
    ]))
    story.append(comp_table)

    # ── DOCUMENTS REQUIRED ────────────────────────────────
    story.append(
        Paragraph('📄 Documents Required at Joining',
                  section_title_style)
    )
    docs = [
        '• Aadhaar Card (Original + 2 copies)',
        '• PAN Card (Original + 2 copies)',
        '• 10th & 12th Marksheets (Originals + copies)',
        '• Degree/Diploma Certificate (Original + copies)',
        '• Last 3 months salary slips (if applicable)',
        '• Previous employment offer/experience letters',
        '• 4 passport size photographs',
        '• Bank account details (cancelled cheque)',
    ]
    docs_text = '<br/>'.join(docs)
    story.append(Paragraph(docs_text, body_style))

    # ── TERMS & CONDITIONS ────────────────────────────────
    story.append(
        Paragraph('📌 Terms & Conditions',
                  section_title_style)
    )
    terms = [
        '1. This offer is contingent upon successful '
        'completion of background verification.',
        '2. The candidate must respond to this offer '
        'within <b>7 days</b> of receipt.',
        '3. Employment is subject to satisfactory '
        'completion of the probation period of 6 months.',
        '4. Notice period after confirmation: '
        '<b>30 days</b>.',
        '5. The candidate must not have any '
        'conflicting obligations with previous employer.',
        '6. This offer is non-transferable and '
        'confidential.',
    ]
    for term in terms:
        story.append(Paragraph(term, body_style))

    # ── ADDITIONAL NOTES ──────────────────────────────────
    if offer.offer_letter_text:
        story.append(
            Paragraph('📝 Additional Notes',
                      section_title_style)
        )
        story.append(
            Paragraph(offer.offer_letter_text, body_style)
        )

    # ── ACCEPTANCE SECTION ────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        HRFlowable(
            width='100%', thickness=1,
            color=BORDER_GRAY, spaceAfter=12
        )
    )
    story.append(
        Paragraph(
            'Please sign and return a copy of this offer '
            'letter as your acceptance.',
            ParagraphStyle(
                'acc', fontSize=9,
                fontName='Helvetica',
                textColor=TEXT_MUTED,
                alignment=TA_CENTER
            )
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    # Signature Block
    sig_data = [
        [
            Paragraph(
                '________',
                ParagraphStyle(
                    'sig', fontSize=10,
                    alignment=TA_CENTER
                )
            ),
            Paragraph(
                '________',
                ParagraphStyle(
                    'sig', fontSize=10,
                    alignment=TA_CENTER
                )
            ),
        ],
        [
            Paragraph(
                f'<b>{company.hr_name}</b><br/>'
                f'<font color="#6c757d" size="8">'
                f'HR Manager<br/>'
                f'{company.company_name}</font>',
                ParagraphStyle(
                    'sig2', fontSize=9,
                    fontName='Helvetica',
                    alignment=TA_CENTER,
                    leading=14
                )
            ),
            Paragraph(
                f'<b>{candidate.full_name}</b><br/>'
                f'<font color="#6c757d" size="8">'
                f'Candidate Signature<br/>'
                f'Date: ___</font>',
                ParagraphStyle(
                    'sig3', fontSize=9,
                    fontName='Helvetica',
                    alignment=TA_CENTER,
                    leading=14
                )
            ),
        ]
    ]
    sig_table = Table(
        sig_data,
        colWidths=[8.5 * cm, 8.5 * cm]
    )
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(sig_table)

    # ── FOOTER ────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * cm))
    footer_data = [[
        Paragraph(
            f'{company.company_name} | '
            f'Generated via HireIQ AI Recruitment Platform | '
            f'Document ID: OL-{offer.id:04d} | '
            f'Confidential',
            footer_style
        )
    ]]
    footer_table = Table(
        footer_data, colWidths=[17 * cm]
    )
    footer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(footer_table)

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer