from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus import PageBreak
from reportlab.lib.colors import HexColor
import os

# ── Brand colours ──────────────────────────────────────────────────────────────
GFL_NAVY   = HexColor("#1A2B4A")
GFL_GOLD   = HexColor("#C9A84C")
GFL_LIGHT  = HexColor("#F5F5F0")
GFL_BORDER = HexColor("#D0D0C8")
RED_COL    = HexColor("#C0392B")
AMBER_COL  = HexColor("#E67E22")
GREEN_COL  = HexColor("#27AE60")
TEXT_DARK  = HexColor("#1C1C1C")
TEXT_MID   = HexColor("#4A4A4A")
HEADER_BG  = HexColor("#1A2B4A")

W, H = A4

# ── Styles ─────────────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()
    s = {}

    s["title"] = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=20,
        textColor=colors.white, alignment=TA_CENTER,
        spaceAfter=4, leading=24
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", fontName="Helvetica", fontSize=11,
        textColor=GFL_GOLD, alignment=TA_CENTER,
        spaceAfter=2, leading=14
    )
    s["meta"] = ParagraphStyle(
        "meta", fontName="Helvetica", fontSize=9,
        textColor=HexColor("#AAAAAA"), alignment=TA_CENTER,
        spaceAfter=0, leading=12
    )
    s["section"] = ParagraphStyle(
        "section", fontName="Helvetica-Bold", fontSize=12,
        textColor=colors.white, alignment=TA_LEFT,
        spaceAfter=0, spaceBefore=0, leading=16,
        leftIndent=6
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=9,
        textColor=TEXT_DARK, alignment=TA_JUSTIFY,
        spaceAfter=4, leading=13, leftIndent=4
    )
    s["bullet"] = ParagraphStyle(
        "bullet", fontName="Helvetica", fontSize=9,
        textColor=TEXT_DARK, alignment=TA_LEFT,
        spaceAfter=3, leading=13, leftIndent=14, firstLineIndent=-10
    )
    s["bold_label"] = ParagraphStyle(
        "bold_label", fontName="Helvetica-Bold", fontSize=9,
        textColor=GFL_NAVY, spaceAfter=2, leading=13
    )
    s["verdict_green"] = ParagraphStyle(
        "verdict_green", fontName="Helvetica-Bold", fontSize=16,
        textColor=colors.white, alignment=TA_CENTER,
        spaceAfter=4, leading=20
    )
    s["verdict_amber"] = ParagraphStyle(
        "verdict_amber", fontName="Helvetica-Bold", fontSize=16,
        textColor=colors.white, alignment=TA_CENTER,
        spaceAfter=4, leading=20
    )
    s["verdict_red"] = ParagraphStyle(
        "verdict_red", fontName="Helvetica-Bold", fontSize=16,
        textColor=colors.white, alignment=TA_CENTER,
        spaceAfter=4, leading=20
    )
    s["flag"] = ParagraphStyle(
        "flag", fontName="Helvetica-Oblique", fontSize=8,
        textColor=AMBER_COL, spaceAfter=2, leading=11, leftIndent=4
    )
    s["disclaimer"] = ParagraphStyle(
        "disclaimer", fontName="Helvetica-Oblique", fontSize=7.5,
        textColor=HexColor("#888888"), alignment=TA_CENTER,
        spaceAfter=0, leading=10
    )
    s["footer_ref"] = ParagraphStyle(
        "footer_ref", fontName="Helvetica", fontSize=7,
        textColor=HexColor("#AAAAAA"), alignment=TA_CENTER,
        spaceAfter=0, leading=10
    )
    return s


# ── Helpers ────────────────────────────────────────────────────────────────────
def section_header(title, styles):
    tbl = Table([[Paragraph(title, styles["section"])]], colWidths=[W - 28*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), HEADER_BG),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    return [Spacer(1, 5*mm), tbl, Spacer(1, 3*mm)]


def kv_table(rows, col_widths=None, zebra=True):
    if col_widths is None:
        col_widths = [60*mm, W - 28*mm - 60*mm]
    data = []
    for k, v in rows:
        data.append([
            Paragraph(f"<b>{k}</b>", ParagraphStyle("kl", fontName="Helvetica-Bold",
                fontSize=8.5, textColor=GFL_NAVY, leading=12)),
            Paragraph(str(v), ParagraphStyle("kv", fontName="Helvetica",
                fontSize=8.5, textColor=TEXT_DARK, leading=12))
        ])
    style = [
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("GRID",        (0, 0), (-1, -1), 0.3, GFL_BORDER),
    ]
    if zebra:
        for i in range(0, len(data), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), GFL_LIGHT))
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle(style))
    return tbl


def finance_table(headers, rows, col_widths=None):
    if col_widths is None:
        n = len(headers)
        each = (W - 28*mm) / n
        col_widths = [each] * n
    hdr_style = ParagraphStyle("fh", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=colors.white, alignment=TA_CENTER, leading=12)
    cell_style = ParagraphStyle("fc", fontName="Helvetica", fontSize=8.5,
        textColor=TEXT_DARK, alignment=TA_CENTER, leading=12)
    bold_cell = ParagraphStyle("fb", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=GFL_NAVY, alignment=TA_CENTER, leading=12)

    data = [[Paragraph(h, hdr_style) for h in headers]]
    for row in rows:
        r = []
        for i, cell in enumerate(row):
            sty = bold_cell if str(cell).startswith("**") else cell_style
            r.append(Paragraph(str(cell).replace("**", ""), sty))
        data.append(r)

    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), GFL_NAVY),
        ("GRID",          (0, 0), (-1, -1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(data), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), GFL_LIGHT))
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle(style))
    return tbl


def verdict_box(verdict, detail_lines, styles):
    colour = {"GREEN": GREEN_COL, "AMBER": AMBER_COL, "RED": RED_COL}.get(verdict, AMBER_COL)
    sty_key = f"verdict_{verdict.lower()}"
    inner = [
        [Paragraph(f"VERDICT: {verdict}", styles[sty_key])],
    ]
    for line in detail_lines:
        inner.append([Paragraph(line, ParagraphStyle("vd", fontName="Helvetica",
            fontSize=9, textColor=colors.white, alignment=TA_CENTER, leading=13))])
    tbl = Table(inner, colWidths=[W - 28*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colour),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return [Spacer(1, 4*mm), tbl, Spacer(1, 4*mm)]


def checklist_table(items, styles):
    data = []
    for item in items:
        data.append([
            Paragraph("☐", ParagraphStyle("cb", fontName="Helvetica", fontSize=10,
                textColor=GFL_NAVY, leading=13)),
            Paragraph(item, ParagraphStyle("ci", fontName="Helvetica", fontSize=8.5,
                textColor=TEXT_DARK, leading=13))
        ])
    tbl = Table(data, colWidths=[8*mm, W - 28*mm - 8*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW",   (0, 0), (-1, -1), 0.2, GFL_BORDER),
    ]))
    return tbl


def risk_table(rows):
    headers = ["Risk", "Likelihood", "Impact", "Mitigation"]
    col_widths = [55*mm, 22*mm, 20*mm, W - 28*mm - 97*mm]
    hdr_sty = ParagraphStyle("rh", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, alignment=TA_CENTER, leading=11)
    cell_sty = ParagraphStyle("rc", fontName="Helvetica", fontSize=8,
        textColor=TEXT_DARK, leading=11)
    centre_sty = ParagraphStyle("rcc", fontName="Helvetica-Bold", fontSize=8,
        textColor=TEXT_DARK, alignment=TA_CENTER, leading=11)

    likelihood_colours = {
        "LOW": HexColor("#D5F5E3"), "LOW-MEDIUM": HexColor("#FDEBD0"),
        "MEDIUM": HexColor("#FAD7A0"), "HIGH": HexColor("#F1948A"),
        "CRITICAL": HexColor("#E74C3C"),
    }
    impact_colours = {
        "LOW": HexColor("#D5F5E3"), "MEDIUM": HexColor("#FAD7A0"),
        "HIGH": HexColor("#F1948A"), "CRITICAL": HexColor("#E74C3C"),
    }

    data = [[Paragraph(h, hdr_sty) for h in headers]]
    for risk, lh, imp, mit in rows:
        data.append([
            Paragraph(risk, cell_sty),
            Paragraph(lh, centre_sty),
            Paragraph(imp, centre_sty),
            Paragraph(mit, cell_sty),
        ])

    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), GFL_NAVY),
        ("GRID",          (0, 0), (-1, -1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]
    for i, (_, lh, imp, _) in enumerate(rows, start=1):
        lh_key = lh.upper().replace("-", "-")
        imp_key = imp.upper()
        lh_col = likelihood_colours.get(lh_key, HexColor("#FFFFFF"))
        imp_col = impact_colours.get(imp_key, HexColor("#FFFFFF"))
        style.append(("BACKGROUND", (1, i), (1, i), lh_col))
        style.append(("BACKGROUND", (2, i), (2, i), imp_col))
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle(style))
    return tbl


# ── Cover page ─────────────────────────────────────────────────────────────────
def cover_page(styles):
    elements = []
    # Header band
    hdr = Table(
        [[Paragraph("GFL AI DEAL ANALYSER", styles["title"]),
          Paragraph("GFL PropertyTech", styles["subtitle"])]],
        colWidths=[W - 28*mm]
    )
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GFL_NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("SPAN",          (0, 0), (-1, -1)),
    ]))
    elements.append(hdr)
    elements.append(Spacer(1, 10*mm))

    # Gold rule
    elements.append(HRFlowable(width="100%", thickness=2, color=GFL_GOLD))
    elements.append(Spacer(1, 8*mm))

    # Property title block
    prop_sty = ParagraphStyle("pt", fontName="Helvetica-Bold", fontSize=18,
        textColor=GFL_NAVY, alignment=TA_CENTER, leading=24)
    sub_sty  = ParagraphStyle("ps", fontName="Helvetica", fontSize=12,
        textColor=TEXT_MID, alignment=TA_CENTER, leading=16)
    price_sty = ParagraphStyle("pp", fontName="Helvetica-Bold", fontSize=22,
        textColor=GFL_GOLD, alignment=TA_CENTER, leading=28)

    elements.append(Paragraph("31 Negril Estate", prop_sty))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph("Westmoreland, Jamaica", sub_sty))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("USD $345,000", price_sty))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("MLS# 98220  |  Coldwell Banker Jamaica Realty", sub_sty))
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=GFL_BORDER))
    elements.append(Spacer(1, 6*mm))

    # Summary verdict box (cover)
    elements += verdict_box("AMBER", [
        "Proceed to due diligence with conditions",
        "Strong location | Competitive pricing | Critical title & survey verification required",
    ], styles)

    elements.append(Spacer(1, 6*mm))

    # Key facts grid
    kf_data = [
        ["Strategy", "STR / Villa Rental + Medium-Term Hold"],
        ["Listing Agent", "Tracey Ann Mair, Coldwell Banker Jamaica Realty"],
        ["Property Type", "New-build detached villa (stone facade, metal roof)"],
        ["Beds / Baths", "Not yet confirmed — assume 3 bed / 2 bath (verify)"],
        ["Floor Size", "Not yet confirmed — assume 1,400–1,800 sq ft (verify)"],
        ["All-In Acquisition Cost", "~USD $381,000 (incl. furnishing)"],
        ["Base-Case NOI", "~USD $18,500 p.a. (STR, no pool)"],
        ["Net Yield (base)", "~5.4% on purchase price"],
        ["Recommended Offer", "USD $315,000 (subject to survey and clear title)"],
        ["Analysis Date", "9 June 2026"],
        ["Reference", "JAM-WES-0609-001"],
    ]
    kf_rows = [(k, v) for k, v in kf_data]
    elements.append(kv_table(kf_rows, col_widths=[65*mm, W - 28*mm - 65*mm]))
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GFL_BORDER))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph(
        "This report is produced for investment evaluation purposes only. It does not constitute legal, tax, mortgage, "
        "planning, or surveying advice. Instruct a qualified Jamaican attorney, chartered surveyor, and accountant "
        "before proceeding. All financial projections are estimates based on assumed data and must be independently verified.",
        styles["disclaimer"]
    ))
    elements.append(PageBreak())
    return elements


# ── Section builders ───────────────────────────────────────────────────────────

def section_executive_summary(styles):
    el = []
    el += section_header("1. EXECUTIVE SUMMARY", styles)
    text = (
        "A newly constructed single-storey villa in Negril Estate, Westmoreland, listed at USD $345,000 through "
        "Coldwell Banker Jamaica Realty (MLS# 98220). Negril is Jamaica's premier tourism destination, generating "
        "consistent short-term rental (STR) and villa rental demand driven by North American and European leisure "
        "travellers. At this price point the deal sits in the mid-upper tier for the area and merits serious "
        "evaluation as a STR/villa rental hold or a medium-term capital appreciation play. "
        "Critical data — floor size, lot dimensions, bed/bath count, title status, utilities connection, and "
        "construction completion status — are not yet confirmed and represent the primary due diligence risk. "
        "The deal is rated AMBER: the location and pricing are strong, but a Green cannot be issued until title "
        "is verified, an independent structural survey is passed, and specification is confirmed. Pool addition "
        "(est. USD $30,000–$40,000) is strongly recommended and would materially improve all income scenarios."
    )
    el.append(Paragraph(text, styles["body"]))
    return el


def section_property_overview(styles):
    el = []
    el += section_header("2. PROPERTY OVERVIEW", styles)
    rows = [
        ("Address", "31 Negril Estate, Westmoreland, Jamaica"),
        ("MLS#", "98220"),
        ("Listing Price", "USD $345,000"),
        ("Property Type", "Detached residential villa (new build)"),
        ("Construction", "Stone/block facade, dark metal roof, single storey"),
        ("Completion Status", "Near-complete / recently completed — VERIFY snagging & certificate"),
        ("Beds / Baths", "NOT CONFIRMED — assume 3 bed / 2 bath pending Details tab"),
        ("Floor Size", "NOT CONFIRMED — assume 1,400–1,800 sq ft pending verification"),
        ("Lot Size", "NOT CONFIRMED — to verify from title / surveyor's report"),
        ("Pool", "NOT CONFIRMED — to verify (material impact on STR yield)"),
        ("Tenure / Title", "NOT CONFIRMED — registered title verification CRITICAL"),
        ("Listing Agent", "Tracey Ann Mair, Coldwell Banker Jamaica Realty"),
        ("Agent Contact", "C: (876) 439-2565  |  F: (876) 946-0007  |  CB Jamaica"),
    ]
    el.append(kv_table(rows, col_widths=[65*mm, W - 28*mm - 65*mm]))
    el.append(Spacer(1, 3*mm))
    el.append(Paragraph(
        "ASSUMPTION FLAG: Bed/bath count, floor area, lot size, pool and title are assumed. "
        "All financial projections must be re-run once confirmed.",
        styles["flag"]
    ))
    return el


def section_area(styles):
    el = []
    el += section_header("3. AREA AND DEMAND SUMMARY", styles)
    el.append(Paragraph(
        "<b>Negril, Westmoreland</b> is Jamaica's top leisure tourism destination, anchored by the Seven Mile "
        "Beach and the West End Cliffs. It draws a consistent mix of North American and European tourists "
        "year-round, with peak season running November–April.",
        styles["body"]
    ))
    el.append(Spacer(1, 2*mm))

    demand = [
        ("High STR / villa rental demand", "Negril is one of the most searched Jamaica destinations on Airbnb, VRBO, and specialist villa platforms."),
        ("USD-denominated market", "Protects against JMD depreciation; strong alignment with US tourist spend."),
        ("Growing villa development", "Boutique hotel and villa development is active across the Negril corridor."),
        ("Air access", "Sangster International Airport (Montego Bay) ~90 minutes; Norman Manley (Kingston) is further."),
        ("Negril Estate", "Established residential subdivision within the Negril corridor with good road access."),
    ]
    el.append(kv_table(demand, col_widths=[55*mm, W - 28*mm - 55*mm]))
    el.append(Spacer(1, 3*mm))

    el.append(Paragraph("<b>Demand Risks</b>", styles["bold_label"]))
    risks = [
        "Hurricane season exposure (June–November) — Westmoreland is on Jamaica's south-west coast, partially sheltered but not immune.",
        "Tourism is cyclical and vulnerable to airline disruption and macro shocks (COVID demonstrated the severity of impact on villa income).",
        "Potential STR oversupply in peak Negril periods — requires active monitoring of platform competitor inventory.",
    ]
    for r in risks:
        el.append(Paragraph(f"• {r}", styles["bullet"]))

    el.append(Spacer(1, 2*mm))
    el.append(Paragraph("<b>Comparable Market Context (Conservative Estimates)</b>", styles["bold_label"]))
    el.append(Paragraph(
        "New-build villas in Negril Estate and surrounding areas: USD $280,000–$550,000+ depending on size, "
        "pool, and finish. USD $345,000 for a new build is within range but requires floor size confirmation "
        "to assess per-sq-ft value. Resale liquidity: moderate — the Negril villa market is active but not "
        "as liquid as Kingston residential.",
        styles["body"]
    ))
    return el


def section_strategy(styles):
    el = []
    el += section_header("4. STRATEGY STACK ANALYSIS", styles)

    rows = [
        ("STR / Villa Rental", "HIGH", "Primary strategy — Negril's core demand driver. Strong nightly rates, proven platforms (Airbnb, VRBO, Luxury Retreats, Island Getaways)."),
        ("Medium-term Hold + Appreciation", "MEDIUM-HIGH", "USD-denominated asset; Negril values have tracked upward historically. 3–7 year hold recommended."),
        ("Operator Lease", "MEDIUM", "Could be leased to a villa management company — reduces management burden, reduces headline income."),
        ("Flip / Resale", "MEDIUM", "Possible after 2–3 years appreciation; market liquidity moderate — not an immediate flip play."),
        ("Corporate / Executive Let", "LOW-MEDIUM", "Limited corporate demand in Negril vs Kingston; not optimal for this location."),
        ("Long-term Residential Let", "LOW", "Rental yield likely poor vs STR potential; underutilises the asset's tourism location."),
        ("Tourism Accommodation Licence", "REQUIRED", "Must obtain TPDCo licence for legal STR operation before first booking."),
        ("Development / Subdivision", "N/A", "Single completed villa on residential lot — not applicable."),
        ("Care / Supported Living", "N/A", "Incompatible with Jamaica market context."),
    ]

    hdr = ["Strategy", "Viability", "Notes"]
    cw  = [52*mm, 26*mm, W - 28*mm - 78*mm]
    hs  = ParagraphStyle("sh", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, alignment=TA_CENTER, leading=11)
    ns  = ParagraphStyle("sn", fontName="Helvetica", fontSize=8,
        textColor=TEXT_DARK, leading=11)
    vs_map = {
        "HIGH": GREEN_COL, "MEDIUM-HIGH": HexColor("#5DAD8A"),
        "MEDIUM": AMBER_COL, "LOW-MEDIUM": HexColor("#D4A017"),
        "LOW": HexColor("#C0392B"), "REQUIRED": GFL_NAVY, "N/A": HexColor("#AAAAAA"),
    }
    data = [[Paragraph(h, hs) for h in hdr]]
    for strat, via, note in rows:
        data.append([
            Paragraph(strat, ParagraphStyle("sl", fontName="Helvetica-Bold", fontSize=8,
                textColor=GFL_NAVY, leading=11)),
            Paragraph(via, ParagraphStyle("sv", fontName="Helvetica-Bold", fontSize=8,
                textColor=colors.white, alignment=TA_CENTER, leading=11)),
            Paragraph(note, ns),
        ])

    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), GFL_NAVY),
        ("GRID",          (0, 0), (-1, -1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]
    for i, (_, via, _) in enumerate(rows, start=1):
        col = vs_map.get(via, HexColor("#DDDDDD"))
        style.append(("BACKGROUND", (1, i), (1, i), col))

    tbl = Table(data, colWidths=cw)
    tbl.setStyle(TableStyle(style))
    el.append(tbl)
    el.append(Spacer(1, 2*mm))
    el.append(Paragraph(
        "Recommended primary strategy: STR / Villa Rental with medium-term hold. "
        "Pool addition strongly recommended to maximise nightly rate and occupancy.",
        styles["flag"]
    ))
    return el


def section_financials(styles):
    el = []
    el += section_header("5. FINANCIAL ANALYSIS", styles)
    el.append(Paragraph(
        "All figures are conservative estimates based on assumed 3-bed / 2-bath, ~1,600 sq ft, no pool confirmed. "
        "Re-run once Details tab is confirmed.",
        styles["flag"]
    ))
    el.append(Spacer(1, 2*mm))

    # 5A Acquisition
    el.append(Paragraph("<b>A. Acquisition Costs</b>", styles["bold_label"]))
    acq = [
        ("Purchase price", "USD $345,000"),
        ("Jamaican attorney fees (~2.5%)", "USD $8,625"),
        ("Stamp duty / registration (~1.5%)", "USD $5,175"),
        ("Surveyor's ID report", "USD $750"),
        ("NLA title search", "USD $300"),
        ("Pre-purchase structural survey", "USD $1,000"),
        ("Furnishing / fit-out (STR ready)", "USD $20,000 – $30,000"),
        ("TOTAL ALL-IN (mid furnish)", "USD ~$381,000"),
    ]
    el.append(kv_table(acq, col_widths=[80*mm, W - 28*mm - 80*mm]))
    el.append(Spacer(1, 4*mm))

    # 5B STR Revenue
    el.append(Paragraph("<b>B. STR Revenue Projection (No Pool Assumed)</b>", styles["bold_label"]))
    el.append(finance_table(
        ["Metric", "Conservative", "Base Case", "Optimistic"],
        [
            ["Nightly rate (USD)",    "$180",      "$220",      "$280"],
            ["Occupancy",             "45%",       "55%",       "65%"],
            ["Occupied nights/year",  "164",       "201",       "237"],
            ["**Gross Revenue**",     "**$29,520**","**$44,220**","**$66,360**"],
            ["Platform fees (15%)",   "($4,428)",  "($6,633)",  "($9,954)"],
            ["**Net Platform Revenue**","**$25,092**","**$37,587**","**$56,406**"],
        ],
        col_widths=[50*mm, 36*mm, 36*mm, 36*mm]
    ))
    el.append(Spacer(1, 4*mm))

    # 5C Operating Costs
    el.append(Paragraph("<b>C. Annual Operating Costs</b>", styles["bold_label"]))
    ops = [
        ("Property management (20% of net revenue)", "USD $5,000 – $11,300"),
        ("Utilities (electricity, water, internet)", "USD $4,800"),
        ("Maintenance & repairs allowance (1% of value)", "USD $3,450"),
        ("Property tax (Jamaica — estimated)", "USD $1,200"),
        ("TPDCo / tourism accommodation licence", "USD $500"),
        ("Insurance (property + liability)", "USD $3,500"),
        ("Accounting / compliance", "USD $1,000"),
        ("TOTAL OPERATING COSTS", "~USD $19,450 – $25,731"),
    ]
    el.append(kv_table(ops, col_widths=[95*mm, W - 28*mm - 95*mm]))
    el.append(Spacer(1, 4*mm))

    # 5D NOI
    el.append(Paragraph("<b>D. Net Operating Income Summary</b>", styles["bold_label"]))
    el.append(finance_table(
        ["Scenario", "Gross Revenue", "Total Costs", "NOI", "Net Yield"],
        [
            ["Conservative", "$29,520", "$24,468", "**$5,052**", "**1.5%**"],
            ["Base Case",    "$44,220", "$25,731", "**$18,489**", "**5.4%**"],
            ["Optimistic",   "$66,360", "$29,000", "**$37,360**", "**10.8%**"],
        ],
        col_widths=[35*mm, 35*mm, 35*mm, 30*mm, 28*mm]
    ))
    el.append(Spacer(1, 2*mm))
    el.append(Paragraph(
        "Conservative scenario is weak — driven by low occupancy without a pool. Adding a pool "
        "(est. USD $25,000–$40,000) could push nightly rates to USD $280–$400 and materially "
        "improve all scenarios.",
        styles["flag"]
    ))
    el.append(Spacer(1, 4*mm))

    # 5E Appreciation
    el.append(Paragraph("<b>E. Capital Appreciation Scenario (5-Year Hold)</b>", styles["bold_label"]))
    el.append(finance_table(
        ["Appreciation Rate", "Value at Year 5", "Capital Gain", "Total Return (Base NOI + CG)"],
        [
            ["2% p.a.", "$381,000", "$36,000", "$128,445"],
            ["4% p.a. (central case)", "$420,000", "$75,000", "$167,445"],
            ["6% p.a.", "$462,000", "$117,000", "$209,445"],
        ],
        col_widths=[50*mm, 40*mm, 38*mm, W - 28*mm - 128*mm]
    ))
    el.append(Spacer(1, 4*mm))

    # 5F Price per sq ft
    el.append(Paragraph("<b>F. Price Per Square Foot Sensitivity</b>", styles["bold_label"]))
    el.append(finance_table(
        ["Assumed Floor Size", "Price / sq ft", "Market Range (Negril new build)"],
        [
            ["1,200 sq ft", "$288 / sq ft", "Mid-market — reasonable"],
            ["1,500 sq ft", "$230 / sq ft", "Good value"],
            ["1,800 sq ft", "$192 / sq ft", "Strong value"],
        ],
        col_widths=[55*mm, 45*mm, W - 28*mm - 100*mm]
    ))
    el.append(Spacer(1, 2*mm))
    el.append(Paragraph(
        "Market range for Negril new builds: approximately USD $180–$320 / sq ft. "
        "At 1,400–1,600 sq ft the asking price is competitive.",
        styles["flag"]
    ))
    return el


def section_risks(styles):
    el = []
    el += section_header("6. RISK REGISTER", styles)
    rows = [
        ("Unregistered / defective title", "Medium", "CRITICAL", "NLA title search and attorney review before any deposit payment"),
        ("Construction defects (new build)", "Medium", "High", "Independent structural survey and snagging inspection before completion"),
        ("Construction not fully complete at listing", "Medium", "High", "Verify snagging list and completion certificate from Parish Council"),
        ("No pool — lower STR competitiveness", "Medium", "Medium", "Assess cost of adding pool post-purchase; budget USD $30,000–$40,000"),
        ("Hurricane / weather damage", "Medium", "High", "Comprehensive insurance essential; confirm flood zone classification"),
        ("STR oversupply in Negril", "Medium", "Medium", "Track Airbnb data; differentiate through quality management and design"),
        ("Currency risk (USD income, GBP reporting)", "Low-Medium", "Medium", "USD-denominated deal limits JMD exposure; monitor GBP/USD rate"),
        ("Management quality / remote ownership", "Medium", "Medium", "Vet local management company before purchase; require monthly reporting"),
        ("TPDCo licensing delays", "Low", "Medium", "Factor 3–6 month timeline into STR launch schedule"),
        ("NEPA / planning non-compliance (new build)", "Low-Medium", "High", "Obtain copies of all planning approvals and NEPA environmental sign-off"),
        ("Market liquidity on resale", "Medium", "Medium", "Negril villa market is active but not deep — minimum 3–5 year hold horizon"),
    ]
    el.append(risk_table(rows))
    return el


def section_compliance(styles):
    el = []
    el += section_header("7. COMPLIANCE AND DUE DILIGENCE FLAGS", styles)

    sections = [
        ("CRITICAL — Resolve Before Any Deposit", [
            "Obtain Volume/Folio reference and confirm registered title with National Land Agency (NLA)",
            "Instruct Jamaican attorney to conduct full 30-year title search",
            "Confirm seller's ownership — no encumbrances, caveats, or mortgages",
            "Obtain approved building plans and completion certificate from Westmoreland Parish Council",
            "Confirm NEPA environmental clearance for new build",
        ]),
        ("HIGH PRIORITY — Before Exchange", [
            "Commission independent structural survey from a local chartered surveyor",
            "Conduct snagging inspection — document all incomplete or defective works",
            "Obtain NLA / government land valuation for transfer tax purposes",
            "Obtain surveyor's identification report confirming lot boundaries match title",
            "Confirm road access status (private vs NWA-maintained public road)",
            "Confirm live utility connections: NWC (water), JPS (electricity), internet provider",
            "Confirm property tax compliance — no arrears outstanding",
            "Confirm HOA / estate covenants and annual maintenance obligations for Negril Estate",
        ]),
        ("OPERATIONAL — Before First Booking", [
            "Apply for TPDCo tourism accommodation licence (allow 3–6 months)",
            "Register for Taxpayer Registration Number (TRN) for rental income declaration in Jamaica",
            "Onboard to STR platforms: Airbnb, VRBO, Luxury Retreats, specialist Jamaica villa sites",
            "Appoint and contract local property management company",
            "Obtain comprehensive insurance: hurricane, property, contents, and STR liability",
        ]),
        ("PROFESSIONAL ADVICE REQUIRED", [
            "Jamaican attorney — title search, transfer, and legal completion",
            "UK / Jamaica accountant — rental income tax treatment, double tax treaty, HMRC reporting",
            "Local chartered surveyor — structural survey and identification report",
            "Insurance broker (Jamaica-specialist) — property, hurricane, and STR liability cover",
        ]),
    ]

    colour_map = {
        "CRITICAL — Resolve Before Any Deposit": RED_COL,
        "HIGH PRIORITY — Before Exchange": AMBER_COL,
        "OPERATIONAL — Before First Booking": GFL_NAVY,
        "PROFESSIONAL ADVICE REQUIRED": HexColor("#555555"),
    }

    for heading, items in sections:
        col = colour_map.get(heading, GFL_NAVY)
        lbl_sty = ParagraphStyle("cl", fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.white, leading=13)
        lbl_tbl = Table([[Paragraph(heading, lbl_sty)]], colWidths=[W - 28*mm])
        lbl_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), col),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        el.append(lbl_tbl)
        el.append(checklist_table(items, styles))
        el.append(Spacer(1, 3*mm))
    return el


def section_offer(styles):
    el = []
    el += section_header("8. OFFER PRICE GUIDANCE", styles)
    rows = [
        ("Title clear, construction complete, pool confirmed", "USD $320,000 – $330,000", "4–7% below ask — justifiable on unverified finish and furnishing cost"),
        ("Title clear, no pool, minor snagging", "USD $300,000 – $315,000", "Pool adds ~$30,000 cost to buyer; re-price accordingly"),
        ("Any title defect or incomplete construction", "DO NOT OFFER", "Resolve title / construction first — material deal-breaker in Jamaica"),
        ("Pool confirmed + strong rental history / income evidence", "USD $335,000 – $345,000", "Closer to ask justified if STR income data supports yield"),
    ]

    hdr_sty = ParagraphStyle("oh", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, alignment=TA_CENTER, leading=11)
    cell_sty = ParagraphStyle("oc", fontName="Helvetica", fontSize=8.5,
        textColor=TEXT_DARK, leading=12)
    price_sty = ParagraphStyle("op", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=GFL_NAVY, alignment=TA_CENTER, leading=12)

    cw = [70*mm, 40*mm, W - 28*mm - 110*mm]
    data = [[Paragraph(h, hdr_sty) for h in ["Scenario", "Offer", "Rationale"]]]
    for scen, price, rat in rows:
        data.append([
            Paragraph(scen, cell_sty),
            Paragraph(price, price_sty),
            Paragraph(rat, cell_sty),
        ])

    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), GFL_NAVY),
        ("GRID",          (0, 0), (-1, -1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("BACKGROUND",    (0, 3), (-1, 3), HexColor("#FDECEA")),
        ("BACKGROUND",    (1, 3), (1, 3), RED_COL),
        ("FONTNAME",      (1, 3), (1, 3), "Helvetica-Bold"),
        ("TEXTCOLOR",     (1, 3), (1, 3), colors.white),
    ]
    for i in range(1, len(data), 2):
        if i != 3:
            style.append(("BACKGROUND", (0, i), (-1, i), GFL_LIGHT))

    tbl = Table(data, colWidths=cw)
    tbl.setStyle(TableStyle(style))
    el.append(tbl)
    el.append(Spacer(1, 3*mm))

    # Opening offer highlight
    box_data = [[Paragraph(
        "Opening Offer Recommendation: <b>USD $315,000</b> — subject to independent survey clean "
        "and title confirmed clear. Escalate to USD $330,000 if pool is confirmed and survey passes.",
        ParagraphStyle("ob", fontName="Helvetica", fontSize=9.5,
            textColor=GFL_NAVY, alignment=TA_CENTER, leading=14)
    )]]
    box = Table(box_data, colWidths=[W - 28*mm])
    box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), HexColor("#FFF8E7")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("BOX",           (0, 0), (-1, -1), 1.5, GFL_GOLD),
    ]))
    el.append(box)
    return el


def section_best_exit(styles):
    el = []
    el += section_header("9. BEST EXIT STRATEGY", styles)
    el.append(Paragraph(
        "<b>STR / Villa Rental — Medium-Term Hold (3–7 Years)</b>",
        styles["bold_label"]
    ))
    el.append(Paragraph(
        "Operate as a fully managed short-term rental targeting North American and European tourists via "
        "Airbnb, VRBO, and a specialist Jamaica villa company. Engage a Negril-based property management "
        "company at 18–22% of gross revenue. Target base-case NOI of USD $18,000–$22,000 per annum once "
        "established and fully operational.",
        styles["body"]
    ))
    el.append(Paragraph(
        "Hold for 3–7 years. In a normalised Negril market with modest appreciation (4% p.a.), the asset "
        "should reach USD $420,000–$450,000 at resale, delivering a total return of approximately "
        "USD $130,000–$180,000 above all-in acquisition cost (before UK tax). Engage UK accountant to "
        "manage double tax treaty position between Jamaica and UK.",
        styles["body"]
    ))
    el.append(Spacer(1, 2*mm))
    el.append(Paragraph(
        "Pool addition is strongly recommended — budget USD $30,000–$40,000. Expected to increase "
        "nightly rates by 40–60% and occupancy by 5–10 percentage points. This single improvement "
        "could upgrade the deal verdict from AMBER to GREEN.",
        styles["flag"]
    ))
    return el


def section_backup_exit(styles):
    el = []
    el += section_header("10. BACKUP EXIT STRATEGY", styles)
    el.append(Paragraph(
        "<b>Operator Lease / Villa Management Lease</b>",
        styles["bold_label"]
    ))
    el.append(Paragraph(
        "If active STR management proves difficult to manage remotely, lease the villa to a Negril villa "
        "operator (e.g., Island Getaways, specialist Jamaica villa companies) on a guaranteed rent or "
        "revenue-share arrangement. Typical terms: operator takes 35–45% of gross revenue in exchange "
        "for full management, marketing, and maintenance. Lower yield but significantly lower management "
        "burden for a remote owner.",
        styles["body"]
    ))
    el.append(Spacer(1, 2*mm))
    el.append(Paragraph(
        "<b>Secondary Backup: Hold and Resale</b>",
        styles["bold_label"]
    ))
    el.append(Paragraph(
        "Exit at Year 3 if NOI underperforms or Negril market strengthens ahead of projections, capturing "
        "capital appreciation as the primary return.",
        styles["body"]
    ))
    return el


def section_verdict(styles):
    el = []
    el += section_header("11. RED / AMBER / GREEN VERDICT", styles)
    el += verdict_box("AMBER", [
        "Proceed to Due Diligence with Conditions",
        "",
        "Strong location | Competitive pricing for new build | Critical verification items outstanding",
    ], styles)

    verdict_rows = [
        ("Location", "STRONG", "Negril is the right market for STR villa investment"),
        ("Asking Price", "REASONABLE", "Competitive for a new build, subject to floor size confirmation"),
        ("New Build Quality", "UNVERIFIED", "Independent structural survey required before exchange"),
        ("Title", "UNVERIFIED", "CRITICAL — NLA title search and attorney review essential"),
        ("STR Income Potential", "GOOD", "Base case viable; materially improved with pool addition"),
        ("Utilities / Road Access", "UNVERIFIED", "JPS, NWC, and internet connections to be confirmed live"),
        ("Planning / NEPA Compliance", "UNVERIFIED", "Building plans and NEPA clearance to be obtained"),
        ("Construction Completion", "UNVERIFIED", "Site appears undressed in listing photos — verify status"),
    ]

    sty_map = {
        "STRONG": GREEN_COL, "REASONABLE": HexColor("#5DAD8A"),
        "GOOD": HexColor("#5DAD8A"), "UNVERIFIED": AMBER_COL,
        "CRITICAL — NLA title search and attorney review essential": RED_COL,
    }

    hs = ParagraphStyle("vh", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, alignment=TA_CENTER, leading=11)
    ns = ParagraphStyle("vn", fontName="Helvetica", fontSize=8.5,
        textColor=TEXT_DARK, leading=12)
    ss = ParagraphStyle("vs", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=colors.white, alignment=TA_CENTER, leading=12)

    cw = [50*mm, 30*mm, W - 28*mm - 80*mm]
    data = [[Paragraph(h, hs) for h in ["Factor", "Status", "Notes"]]]
    status_colours = {
        "STRONG": GREEN_COL, "REASONABLE": HexColor("#5DAD8A"),
        "GOOD": HexColor("#5DAD8A"), "UNVERIFIED": AMBER_COL,
    }
    for factor, status, note in verdict_rows:
        data.append([
            Paragraph(factor, ns),
            Paragraph(status, ss),
            Paragraph(note, ns),
        ])

    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), GFL_NAVY),
        ("GRID",          (0, 0), (-1, -1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]
    for i, (_, status, _) in enumerate(verdict_rows, start=1):
        col = status_colours.get(status, HexColor("#DDDDDD"))
        style.append(("BACKGROUND", (1, i), (1, i), col))

    tbl = Table(data, colWidths=cw)
    tbl.setStyle(TableStyle(style))
    el.append(tbl)

    el.append(Spacer(1, 3*mm))
    el.append(Paragraph(
        "Issue GREEN once: title is clean, planning approvals confirmed, independent survey passed, "
        "utilities live, and floor size / specification confirmed. "
        "Issue RED if: title is defective or unregistered without a clear path to registration, "
        "or structural survey reveals material defects.",
        styles["flag"]
    ))
    return el


def section_checklist(styles):
    el = []
    el += section_header("12. NEXT ACTION CHECKLIST", styles)

    action_groups = [
        ("Immediate — This Week", [
            "Request Details tab data from agent: beds, baths, floor size, lot size, title Vol/Folio, pool Y/N",
            "Request copies of: title, approved building plans, completion certificate, NEPA sign-off",
            "Instruct Jamaican attorney to commence NLA title search immediately",
            "Request agent confirm utility connections: JPS (electricity), NWC (water), internet",
            "Obtain comparables data from agent (Comparables tab on MLS listing)",
        ]),
        ("Within 2 Weeks", [
            "Instruct independent structural survey and snagging inspection",
            "Obtain surveyor's identification report confirming lot boundaries vs title",
            "Obtain 2–3 quotes from Negril property management companies",
            "Obtain insurance quote: hurricane, property, contents, STR liability",
            "Run STR market research: Airbnb / VRBO comparable Negril 3-bed listings (with and without pool)",
            "Assess cost of adding a pool post-purchase — obtain quote from local contractor",
        ]),
        ("Before Exchange", [
            "Confirm government land valuation for transfer tax calculation",
            "Confirm HOA / estate covenants and annual maintenance fees for Negril Estate",
            "Confirm TRN registration process for rental income reporting in Jamaica",
            "Confirm TPDCo licensing timeline and documentation requirements",
            "Brief UK accountant on Jamaica rental income — double tax treaty and HMRC reporting obligations",
            "Confirm completion and snagging sign-off — all defective works resolved before funds transfer",
        ]),
    ]

    colour_map = {
        "Immediate — This Week": RED_COL,
        "Within 2 Weeks": AMBER_COL,
        "Before Exchange": GFL_NAVY,
    }

    for heading, items in action_groups:
        col = colour_map.get(heading, GFL_NAVY)
        lbl_sty = ParagraphStyle("al", fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.white, leading=13)
        lbl_tbl = Table([[Paragraph(heading, lbl_sty)]], colWidths=[W - 28*mm])
        lbl_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), col),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        el.append(lbl_tbl)
        el.append(checklist_table(items, styles))
        el.append(Spacer(1, 3*mm))
    return el


def footer_disclaimer(styles):
    el = []
    el.append(HRFlowable(width="100%", thickness=0.5, color=GFL_BORDER))
    el.append(Spacer(1, 3*mm))
    el.append(Paragraph(
        "This report is produced for investment evaluation purposes only and does not constitute legal, tax, mortgage, "
        "planning, or professional surveying advice. All financial projections are estimates based on assumed data and "
        "must be independently verified. Instruct a qualified Jamaican attorney, chartered surveyor, and accountant "
        "before proceeding with any transaction.",
        styles["disclaimer"]
    ))
    el.append(Spacer(1, 2*mm))
    el.append(Paragraph(
        "GFL AI Deal Analyser  |  GFL PropertyTech  |  Ref: JAM-WES-0609-001  |  9 June 2026",
        styles["footer_ref"]
    ))
    return el


# ── Page template (header/footer on every page) ────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # Top strip
    canvas.setFillColor(GFL_NAVY)
    canvas.rect(0, H - 12*mm, W, 12*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.white)
    canvas.drawString(14*mm, H - 8*mm, "GFL AI DEAL ANALYSER  |  31 Negril Estate, Westmoreland")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GFL_GOLD)
    canvas.drawRightString(W - 14*mm, H - 8*mm, f"Page {doc.page}  |  JAM-WES-0609-001")
    # Bottom strip
    canvas.setFillColor(GFL_NAVY)
    canvas.rect(0, 0, W, 8*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#AAAAAA"))
    canvas.drawCentredString(W / 2, 2.5*mm, "GFL PropertyTech  |  Investment analysis only — not legal, tax or professional advice")
    canvas.restoreState()


# ── Main build ─────────────────────────────────────────────────────────────────
def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=14*mm,
        topMargin=18*mm,
        bottomMargin=14*mm,
        title="GFL Deal Analysis — 31 Negril Estate",
        author="GFL PropertyTech AI Deal Analyser",
        subject="Jamaica Property Investment Analysis",
    )

    styles = build_styles()
    story = []

    story += cover_page(styles)
    story += section_executive_summary(styles)
    story += section_property_overview(styles)
    story += section_area(styles)
    story += section_strategy(styles)
    story += section_financials(styles)
    story += section_risks(styles)
    story += section_compliance(styles)
    story += section_offer(styles)
    story += section_best_exit(styles)
    story += section_backup_exit(styles)
    story += section_verdict(styles)
    story += section_checklist(styles)
    story += footer_disclaimer(styles)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    out = "/home/user/GFL-PHONE-AGENT/GFL_Deal_Analysis_31_Negril_Estate.pdf"
    build_pdf(out)
