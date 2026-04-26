from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io

def get_grade(mark):
    if mark >= 80: return "A"
    if mark >= 70: return "B"
    if mark >= 60: return "C"
    if mark >= 50: return "D"
    return "F"

def get_grade_color(grade):
    return {
        "A": colors.HexColor("#00a07a"),
        "B": colors.HexColor("#3a86ff"),
        "C": colors.HexColor("#f5c400"),
        "D": colors.HexColor("#ff8c00"),
        "F": colors.HexColor("#ff4d6d"),
    }.get(grade, colors.black)

def get_remark(average):
    if average >= 80: return "Excellent Performance"
    if average >= 70: return "Very Good Performance"
    if average >= 60: return "Good Performance"
    if average >= 50: return "Satisfactory Performance"
    return "Needs Improvement"

def generate_report_pdf(student, school, marks_data, term, year, average):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    GREEN  = colors.HexColor("#006644")
    LGREEN = colors.HexColor("#00c896")
    DARK   = colors.HexColor("#0a1525")
    GREY   = colors.HexColor("#f5f7fa")
    MGREY  = colors.HexColor("#e0e7ef")
    MUTED  = colors.HexColor("#5a7a9a")

    styles = getSampleStyleSheet()
    story  = []

    # ── Header ──────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(
            f'<font color="#ffffff"><b>MINISTRY OF PRIMARY &amp; SECONDARY EDUCATION</b></font><br/>'
            f'<font color="#a0d8c8" size="9">Republic of Zimbabwe</font>',
            ParagraphStyle("hdr", fontName="Helvetica-Bold", fontSize=13, textColor=colors.white, leading=18)
        ),
        Paragraph(
            f'<font color="#a0d8c8" size="9">STUDENT REPORT CARD</font><br/>'
            f'<font color="#ffffff"><b>{term} · {year}</b></font>',
            ParagraphStyle("hdr2", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white, leading=16, alignment=TA_RIGHT)
        )
    ]]
    header_table = Table(header_data, colWidths=[11*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GREEN),
        ("PADDING",       (0,0), (-1,-1), 14),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS",(0,0), (-1,-1), [8,8,0,0]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4*cm))

    # ── School & Student Info ─────────────────────────────────────────────
    info_data = [[
        Paragraph(f'<b>School:</b> {school["name"]}', ParagraphStyle("inf", fontSize=9, leading=14)),
        Paragraph(f'<b>Student:</b> {student["name"]}', ParagraphStyle("inf", fontSize=9, leading=14)),
    ],[
        Paragraph(f'<b>Class:</b> {student["class"]}', ParagraphStyle("inf", fontSize=9, leading=14)),
        Paragraph(f'<b>Student ID:</b> {student["student_id"]}', ParagraphStyle("inf", fontSize=9, leading=14)),
    ]]
    info_table = Table(info_data, colWidths=[9*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), GREY),
        ("BOX",         (0,0), (-1,-1), 0.5, MGREY),
        ("PADDING",     (0,0), (-1,-1), 10),
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Marks Table ───────────────────────────────────────────────────────
    story.append(Paragraph(
        "ACADEMIC PERFORMANCE",
        ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=9, textColor=MUTED, spaceBefore=4, spaceAfter=6, letterSpacing=1.5)
    ))

    table_data = [[
        Paragraph("<b>Subject</b>",         ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
        Paragraph("<b>Mark (%)</b>",        ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("<b>Grade</b>",           ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("<b>Teacher's Remark</b>",ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
    ]]

    row_styles = [
        ("BACKGROUND",  (0,0), (-1,0), DARK),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("PADDING",     (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, GREY]),
        ("GRID",        (0,0), (-1,-1), 0.3, MGREY),
        ("ALIGN",       (1,1), (2,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
    ]

    for i, m in enumerate(marks_data):
        grade = m["grade"]
        gc    = get_grade_color(grade)
        table_data.append([
            Paragraph(m["subject"], ParagraphStyle("td", fontSize=9)),
            Paragraph(f'<b>{m["mark"]}</b>', ParagraphStyle("td", fontSize=10, alignment=TA_CENTER)),
            Paragraph(f'<b><font color="{gc.hexval() if hasattr(gc,"hexval") else "#000"}">{grade}</font></b>',
                      ParagraphStyle("td", fontSize=11, alignment=TA_CENTER, fontName="Helvetica-Bold")),
            Paragraph(m.get("comment", "—"), ParagraphStyle("td", fontSize=8, textColor=MUTED)),
        ])
        row_styles.append(("TEXTCOLOR", (2, i+1), (2, i+1), gc))

    marks_table = Table(table_data, colWidths=[5.5*cm, 3*cm, 2.5*cm, 7*cm])
    marks_table.setStyle(TableStyle(row_styles))
    story.append(marks_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Summary ───────────────────────────────────────────────────────────
    remark     = get_remark(average)
    avg_grade  = get_grade(average)
    avg_color  = get_grade_color(avg_grade)

    summary_data = [[
        Paragraph(f'Overall Average', ParagraphStyle("sl", fontSize=9, textColor=MUTED)),
        Paragraph(f'<b>{average}%</b>', ParagraphStyle("sv", fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER)),
        Paragraph(f'Grade: <b>{avg_grade}</b>', ParagraphStyle("sg", fontName="Helvetica-Bold", fontSize=11, textColor=avg_color, alignment=TA_CENTER)),
        Paragraph(f'<i>{remark}</i>', ParagraphStyle("sr", fontSize=9, textColor=MUTED)),
    ]]
    summary_table = Table(summary_data, colWidths=[4*cm, 3*cm, 3.5*cm, 7.5*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#e8f5f0")),
        ("BOX",        (0,0), (-1,-1), 1, LGREEN),
        ("PADDING",    (0,0), (-1,-1), 12),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LINEAFTER",  (0,0), (2,0), 0.5, MGREY),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Signatures ────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY))
    story.append(Spacer(1, 0.4*cm))
    sig_data = [[
        Paragraph("____________________<br/><font size='8' color='#5a7a9a'>Class Teacher</font>",
                  ParagraphStyle("sig", fontSize=9, alignment=TA_CENTER)),
        Paragraph("____________________<br/><font size='8' color='#5a7a9a'>Headmaster</font>",
                  ParagraphStyle("sig", fontSize=9, alignment=TA_CENTER)),
        Paragraph("____________________<br/><font size='8' color='#5a7a9a'>Parent / Guardian</font>",
                  ParagraphStyle("sig", fontSize=9, alignment=TA_CENTER)),
    ]]
    sig_table = Table(sig_data, colWidths=[6*cm, 6*cm, 6*cm])
    sig_table.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER"), ("PADDING", (0,0), (-1,-1), 8)]))
    story.append(sig_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Paragraph(
        f'Generated by Smart Report System · Ministry of Primary &amp; Secondary Education · Zimbabwe · {year}',
        ParagraphStyle("ft", fontSize=7, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
