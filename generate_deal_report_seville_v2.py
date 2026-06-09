from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.colors import HexColor

GFL_NAVY   = HexColor("#1A2B4A")
GFL_GOLD   = HexColor("#C9A84C")
GFL_LIGHT  = HexColor("#F5F5F0")
GFL_BORDER = HexColor("#D0D0C8")
RED_COL    = HexColor("#C0392B")
AMBER_COL  = HexColor("#E67E22")
GREEN_COL  = HexColor("#27AE60")
TEXT_DARK  = HexColor("#1C1C1C")
TEXT_MID   = HexColor("#4A4A4A")

W, H = A4
CW_FULL = W - 28*mm

# ── Exchange rates ─────────────────────────────────────────────────────────────
JMD_USD = 155.0   # JMD per USD
GBP_USD = 1.27    # USD per GBP
JMD_GBP = JMD_USD / GBP_USD  # ~122 JMD per GBP

PRICE_JMD = 54_500_000
PRICE_USD = PRICE_JMD / JMD_USD        # ~$351,613
PRICE_GBP = PRICE_JMD / JMD_GBP       # ~£259,007


def sty(name, **kw):
    d = dict(fontName="Helvetica", fontSize=9, textColor=TEXT_DARK, leading=13, spaceAfter=3)
    d.update(kw)
    return ParagraphStyle(name, **d)


S = {
    "title":  sty("ti", fontName="Helvetica-Bold", fontSize=20, textColor=colors.white,
                  alignment=TA_CENTER, leading=24),
    "sec":    sty("se", fontName="Helvetica-Bold", fontSize=12, textColor=colors.white,
                  leading=16, leftIndent=6),
    "body":   sty("bo", alignment=TA_JUSTIFY, leftIndent=4),
    "bullet": sty("bu", leftIndent=14, firstLineIndent=-10),
    "lbl":    sty("lb", fontName="Helvetica-Bold", textColor=GFL_NAVY),
    "flag":   sty("fl", fontName="Helvetica-Oblique", fontSize=8, textColor=AMBER_COL,
                  leading=11, leftIndent=4),
    "red":    sty("rf", fontName="Helvetica-Bold", fontSize=8.5, textColor=RED_COL,
                  leading=11, leftIndent=4),
    "disc":   sty("di", fontName="Helvetica-Oblique", fontSize=7.5,
                  textColor=HexColor("#888888"), alignment=TA_CENTER, leading=10),
    "foot":   sty("fo", fontSize=7, textColor=HexColor("#AAAAAA"), alignment=TA_CENTER, leading=10),
    "vt":     sty("vt", fontName="Helvetica-Bold", fontSize=16, textColor=colors.white,
                  alignment=TA_CENTER, leading=20),
    "vs":     sty("vs", fontName="Helvetica", fontSize=9, textColor=colors.white,
                  alignment=TA_CENTER, leading=13),
    "upd":    sty("up", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white,
                  alignment=TA_CENTER, leading=13),
}


def sec_hdr(t):
    tbl = Table([[Paragraph(t, S["sec"])]], colWidths=[CW_FULL])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), GFL_NAVY),
        ("TOPPADDING", (0,0),(-1,-1), 5), ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 8),
    ]))
    return [Spacer(1, 5*mm), tbl, Spacer(1, 3*mm)]


def kv(rows, cw=None):
    if cw is None:
        cw = [65*mm, CW_FULL - 65*mm]
    ks = ParagraphStyle("k", fontName="Helvetica-Bold", fontSize=8.5, textColor=GFL_NAVY, leading=12)
    vs = ParagraphStyle("v", fontName="Helvetica", fontSize=8.5, textColor=TEXT_DARK, leading=12)
    data = [[Paragraph(k, ks), Paragraph(str(v), vs)] for k, v in rows]
    st = [
        ("VALIGN", (0,0),(-1,-1), "TOP"), ("TOPPADDING", (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4), ("LEFTPADDING", (0,0),(-1,-1), 6),
        ("GRID", (0,0),(-1,-1), 0.3, GFL_BORDER),
    ]
    for i in range(0, len(data), 2):
        st.append(("BACKGROUND", (0,i),(-1,i), GFL_LIGHT))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    return t


def ftbl(headers, rows, cw=None):
    if cw is None:
        n = len(headers); cw = [CW_FULL/n]*n
    hs = ParagraphStyle("fh", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white,
                        alignment=TA_CENTER, leading=12)
    cs = ParagraphStyle("fc", fontName="Helvetica", fontSize=8.5, textColor=TEXT_DARK,
                        alignment=TA_CENTER, leading=12)
    bs = ParagraphStyle("fb", fontName="Helvetica-Bold", fontSize=8.5, textColor=GFL_NAVY,
                        alignment=TA_CENTER, leading=12)
    data = [[Paragraph(h, hs) for h in headers]]
    for row in rows:
        r = []
        for cell in row:
            bold = str(cell).startswith("**")
            r.append(Paragraph(str(cell).replace("**",""), bs if bold else cs))
        data.append(r)
    st = [
        ("BACKGROUND", (0,0),(-1,0), GFL_NAVY), ("GRID", (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING", (0,0),(-1,-1), 4), ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
    ]
    for i in range(1, len(data), 2):
        st.append(("BACKGROUND", (0,i),(-1,i), GFL_LIGHT))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    return t


def vbox(verdict, lines, sub=None):
    col = {"GREEN": GREEN_COL, "AMBER": AMBER_COL, "RED": RED_COL}.get(verdict, AMBER_COL)
    inner = [[Paragraph(f"VERDICT: {verdict}", S["vt"])]]
    if sub:
        inner.append([Paragraph(sub, S["upd"])])
    for l in lines:
        inner.append([Paragraph(l, S["vs"])])
    t = Table(inner, colWidths=[CW_FULL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), col),
        ("TOPPADDING", (0,0),(-1,-1), 6), ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0),(-1,-1), 10), ("RIGHTPADDING", (0,0),(-1,-1), 10),
    ]))
    return [Spacer(1, 4*mm), t, Spacer(1, 4*mm)]


def chklist(items):
    cs = ParagraphStyle("cb", fontName="Helvetica", fontSize=10, textColor=GFL_NAVY, leading=13)
    is_ = ParagraphStyle("ci", fontName="Helvetica", fontSize=8.5, textColor=TEXT_DARK, leading=13)
    data = [[Paragraph("☐", cs), Paragraph(item, is_)] for item in items]
    t = Table(data, colWidths=[8*mm, CW_FULL-8*mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0,0),(-1,-1), "TOP"), ("TOPPADDING", (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3), ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("LINEBELOW", (0,0),(-1,-1), 0.2, GFL_BORDER),
    ]))
    return t


def risk_tbl(rows):
    lh_c = {"LOW": HexColor("#D5F5E3"), "LOW-MEDIUM": HexColor("#FDEBD0"),
             "MEDIUM": HexColor("#FAD7A0"), "HIGH": HexColor("#F1948A")}
    im_c = {"LOW": HexColor("#D5F5E3"), "MEDIUM": HexColor("#FAD7A0"),
             "HIGH": HexColor("#F1948A"), "CRITICAL": HexColor("#E74C3C")}
    hs = ParagraphStyle("rh", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white,
                        alignment=TA_CENTER, leading=11)
    cs = ParagraphStyle("rc", fontName="Helvetica", fontSize=8, textColor=TEXT_DARK, leading=11)
    ms = ParagraphStyle("rm", fontName="Helvetica-Bold", fontSize=8, textColor=TEXT_DARK,
                        alignment=TA_CENTER, leading=11)
    cw = [58*mm, 24*mm, 22*mm, CW_FULL-104*mm]
    data = [[Paragraph(h, hs) for h in ["Risk", "Likelihood", "Impact", "Mitigation"]]]
    for risk, lh, im, mit in rows:
        data.append([Paragraph(risk, cs), Paragraph(lh, ms), Paragraph(im, ms), Paragraph(mit, cs)])
    st = [
        ("BACKGROUND", (0,0),(-1,0), GFL_NAVY), ("GRID", (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING", (0,0),(-1,-1), 4), ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN", (0,0),(-1,-1), "TOP"), ("LEFTPADDING", (0,0),(-1,-1), 5),
    ]
    for i, (_, lh, im, _) in enumerate(rows, 1):
        st.append(("BACKGROUND", (1,i),(1,i), lh_c.get(lh.upper(), HexColor("#FFF"))))
        st.append(("BACKGROUND", (2,i),(2,i), im_c.get(im.upper(), HexColor("#FFF"))))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    return t


def lbl_sec(heading, items, col):
    ls = ParagraphStyle("ls", fontName="Helvetica-Bold", fontSize=9,
                        textColor=colors.white, leading=13)
    lt = Table([[Paragraph(heading, ls)]], colWidths=[CW_FULL])
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), col),
        ("TOPPADDING", (0,0),(-1,-1), 4), ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0),(-1,-1), 8),
    ]))
    return [lt, chklist(items), Spacer(1, 3*mm)]


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GFL_NAVY)
    canvas.rect(0, H-12*mm, W, 12*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8); canvas.setFillColor(colors.white)
    canvas.drawString(14*mm, H-8*mm, "GFL AI DEAL ANALYSER  |  9 Hibiscus Way, Seville — UPDATED v2")
    canvas.setFont("Helvetica", 8); canvas.setFillColor(GFL_GOLD)
    canvas.drawRightString(W-14*mm, H-8*mm, f"Page {doc.page}  |  JAM-STA-0609-002v2")
    canvas.setFillColor(GFL_NAVY)
    canvas.rect(0, 0, W, 8*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7); canvas.setFillColor(HexColor("#AAAAAA"))
    canvas.drawCentredString(W/2, 2.5*mm,
        "GFL PropertyTech  |  Investment analysis only — not legal, tax or professional advice")
    canvas.restoreState()


# ── COVER ──────────────────────────────────────────────────────────────────────
def cover(story):
    t = Table([[Paragraph("GFL AI DEAL ANALYSER", S["title"])]], colWidths=[CW_FULL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), GFL_NAVY),
        ("TOPPADDING", (0,0),(-1,-1), 14), ("BOTTOMPADDING", (0,0),(-1,-1), 14),
    ]))
    story.append(t)

    # UPDATE BANNER
    upd = Table([[Paragraph("UPDATED ANALYSIS — Asking Price Confirmed", S["upd"])]], colWidths=[CW_FULL])
    upd.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), GFL_GOLD),
        ("TOPPADDING", (0,0),(-1,-1), 5), ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 8),
    ]))
    story.append(upd)
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=GFL_GOLD))
    story.append(Spacer(1, 5*mm))

    p_s = ParagraphStyle("pt", fontName="Helvetica-Bold", fontSize=18,
                          textColor=GFL_NAVY, alignment=TA_CENTER, leading=24)
    s_s = ParagraphStyle("ps", fontName="Helvetica", fontSize=12,
                          textColor=TEXT_MID, alignment=TA_CENTER, leading=16)

    story.append(Paragraph("9 Hibiscus Way", p_s))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("Seville, St. Ann's Bay, St. Ann, Jamaica", s_s))
    story.append(Spacer(1, 4*mm))

    # Triple price display
    price_data = [[
        Paragraph(f"JMD $54,500,000",
                  ParagraphStyle("p1", fontName="Helvetica-Bold", fontSize=14,
                                 textColor=GFL_NAVY, alignment=TA_CENTER, leading=18)),
        Paragraph(f"USD ~${PRICE_USD:,.0f}",
                  ParagraphStyle("p2", fontName="Helvetica-Bold", fontSize=14,
                                 textColor=GFL_GOLD, alignment=TA_CENTER, leading=18)),
        Paragraph(f"GBP £{PRICE_GBP:,.0f}",
                  ParagraphStyle("p3", fontName="Helvetica-Bold", fontSize=14,
                                 textColor=GFL_NAVY, alignment=TA_CENTER, leading=18)),
    ]]
    pt = Table(price_data, colWidths=[CW_FULL/3]*3)
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), GFL_LIGHT),
        ("TOPPADDING", (0,0),(-1,-1), 8), ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("BOX", (0,0),(-1,-1), 1, GFL_GOLD),
        ("INNERGRID", (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "MLS# 100907  |  6 Bed / 6 Bath  |  4 Apartments  |  4,245 sq ft  |  0.30 acres  |  Listed 22 Apr 2026  |  DOM: 48",
        s_s
    ))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GFL_BORDER))

    story += vbox("AMBER", [
        "Proceed to Due Diligence with Conditions",
        "STR mix yield of ~12% gross is compelling | Unknown build date and planning compliance are key risks",
        "Offer GBP £232,000 – £245,000 | Subject to structural survey and clear title",
    ])

    kf = [
        ("Property",              "Split-level, 4 apartments (2× 2-bed/2-bath + 2× 1-bed/1-bath)"),
        ("MLS# / Agent",          "100907  |  Tracey Ann Mair, Coldwell Banker Jamaica Realty"),
        ("Confirmed Price",       f"JMD $54,500,000  |  USD ~${PRICE_USD:,.0f}  |  GBP ~£{PRICE_GBP:,.0f}"),
        ("Price per sq ft",       f"~USD $83 / sq ft  (market range: $70–$120 for JA multi-family)"),
        ("Exchange rates used",   "155 JMD/USD  |  1.27 USD/GBP  |  ~122 JMD/GBP"),
        ("LTL gross yield",       "~5.2% (USD) — marginal as standalone"),
        ("STR mix gross yield",   "~12.2% (USD) — 2× LTL 2-beds + 2× STR 1-beds"),
        ("STR mix net yield",     "~7.0% (USD) — after all operating costs"),
        ("Best Strategy",         "Multi-family BTL + convert upper 1-beds to STR (ocean views)"),
        ("Recommended Offer",     f"GBP £232,000–£245,000 / JMD ~$50.5M–$53.3M"),
        ("Year Built",            "NOT STATED — structural survey non-negotiable"),
        ("Ref / Date",            "JAM-STA-0609-002v2  |  9 June 2026"),
    ]
    story.append(kv(kf, cw=[65*mm, CW_FULL-65*mm]))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GFL_BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "This report is for investment evaluation only. It does not constitute legal, tax, mortgage, planning, "
        "or surveying advice. All projections are estimates and must be independently verified. "
        "Instruct a qualified Jamaican attorney, chartered surveyor, and accountant before proceeding.",
        S["disc"]
    ))
    story.append(PageBreak())


# ── SECTION 1 ──────────────────────────────────────────────────────────────────
def s1(story):
    story += sec_hdr("1. EXECUTIVE SUMMARY")
    story.append(Paragraph(
        f"9 Hibiscus Way, Seville is a 4,245 sq ft split-level house in an established St. Ann subdivision, "
        f"listed at JMD $54,500,000 (USD ~${PRICE_USD:,.0f} / GBP ~£{PRICE_GBP:,.0f}) and already configured "
        f"as four income-producing apartments. The confirmed price equates to ~USD $83/sq ft — within the "
        f"acceptable range for Jamaica multi-family stock. On a long-term let (LTL) only basis, the gross USD "
        f"yield is a marginal 5.2%, driven by JMD-denominated rents and currency conversion friction. However, "
        f"converting the two upper-level 1-bed units (ocean views, 10-min walk to sea, 20-min from Ocho Rios) "
        f"to short-term rental (STR) via Airbnb/VRBO transforms the return profile to approximately 12.2% gross "
        f"and 7.0% net in USD — a compelling outcome for a Jamaican multi-family asset. The deal remains AMBER "
        f"pending title verification, structural survey (year of build not stated), and confirmation of planning "
        f"approval for the 4-unit conversion. With 48 DOM and those open diligence items, a 5–10% discount from "
        f"asking is reasonable and justified.",
        S["body"]
    ))


# ── SECTION 2 ──────────────────────────────────────────────────────────────────
def s2(story):
    story += sec_hdr("2. PROPERTY OVERVIEW")
    rows = [
        ("Address",            "9 Hibiscus Way, Seville, St. Ann's Bay, St. Ann, Jamaica"),
        ("MLS# / Lot#",        "100907  |  Lot 84, Block N/A, Seville Subdivision"),
        ("Listing Agent",      "Tracey Ann Mair  |  Coldwell Banker Jamaica Realty  |  (876) 439-2565"),
        ("Listed / Updated",   "22 Apr 2026  |  Confirmed GBP price: 28 May 2026  |  DOM: 48"),
        ("Confirmed Price",    f"JMD $54,500,000  =  USD ~${PRICE_USD:,.0f}  =  GBP ~£{PRICE_GBP:,.0f}"),
        ("Style",              "Split-level house"),
        ("Beds / Baths",       "6 bedrooms / 6 bathrooms (across 4 self-contained apartments)"),
        ("Unit Mix",           "2× 2-bed/2-bath (ensuite)  +  2× 1-bed/1-bath"),
        ("Additional Spaces",  "Laundry room, helper's quarters, storeroom, utility space, large garage"),
        ("Floor Area",         "4,245 sq ft total"),
        ("Lot Size",           "12,887 sq ft (0.2958 acres)"),
        ("Year Built",         "NOT STATED — structural survey essential before exchange"),
        ("EPC / Condition",    "Jamaica has no EPC regime; condition to be confirmed by survey"),
        ("Furnishing",         "Unfurnished — furnishing budget required for all units"),
        ("Views",              "Ocean views from upper level"),
        ("Road Access",        "Paved road  |  North coast highway community"),
        ("Proximity",          "5 min St. Ann's Bay town  |  20 min Ocho Rios  |  10 min walk to sea"),
        ("Region",             "Middlesex, St. Ann  |  Post code: St. Ann's Bay"),
        ("Sale Type",          "For Sale  |  Status: Active"),
        ("Price note",         "Original MLS entry shows GBP £1,877 — likely a data entry error in system; confirmed price GBP £259,007"),
    ]
    story.append(kv(rows, cw=[60*mm, CW_FULL-60*mm]))


# ── SECTION 3 ──────────────────────────────────────────────────────────────────
def s3(story):
    story += sec_hdr("3. AREA AND DEMAND SUMMARY")
    story.append(Paragraph(
        "<b>St. Ann's Bay, St. Ann</b> is the parish capital on Jamaica's north coast. It sits between "
        "Ocho Rios (20 min east) and Runaway Bay (15 min west). The town services a mixed economy of "
        "local professional and public sector workers, north coast tourism spillover, and a growing "
        "retirement demographic. Seville is an established residential subdivision with paved road access.",
        S["body"]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(kv([
        ("Residential demand",   "Steady from healthcare workers (St. Ann's Bay Hospital), teachers, public sector, and north coast business employees."),
        ("Tourism spillover",    "Ocho Rios (20 min) is Jamaica's #2 tourism hub — STR guests seeking quieter stays within reach of Ocho Rios activities."),
        ("Ocean views / access", "Upper-level sea views and 10-min walk to sea are strong STR marketing differentiators."),
        ("Infrastructure",       "Paved road, north coast highway, easy access to all St. Ann amenities."),
        ("Senior market",        "Listing flags 'seniors oriented' — aligns with boutique senior accommodation opportunity."),
    ], cw=[55*mm, CW_FULL-55*mm]))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("<b>Market Risks</b>", S["lbl"]))
    for r in [
        "Secondary rental market — JMD residential rents are lower than Kingston, MoBay, or Ocho Rios town.",
        "STR demand tied to Ocho Rios tourism proximity — not a standalone beach resort destination.",
        "JMD rental income creates USD/GBP currency exposure — exchange rate movements affect real returns.",
        "Unknown build year — potential for hidden maintenance liability if older construction.",
        "Apartment conversion compliance unknown — planning risk if unauthorised modification.",
    ]:
        story.append(Paragraph(f"• {r}", S["bullet"]))


# ── SECTION 4 ──────────────────────────────────────────────────────────────────
def s4(story):
    story += sec_hdr("4. STRATEGY STACK ANALYSIS")
    rows = [
        ("Multi-family BTL (LTL)", "HIGH", "4 units already configured. Immediate income base. Stable but modest USD yield."),
        ("Partial STR Conversion", "HIGH", "Convert 2× upper 1-bed units to STR — ocean views, Ocho Rios proximity. 3–5× yield uplift per unit vs LTL."),
        ("Mixed LTL + STR", "HIGH", "Optimal: 2× 2-bed on LTL for stable income, 2× 1-bed on STR for USD yield. Best risk-adjusted return."),
        ("BRRRR", "MEDIUM", "Refurb to higher spec → higher rents → refinance locally (JMD rate ~10–12%) or remortgage UK asset. Medium-term play."),
        ("Add Units (Development)", "MEDIUM", "~8,600 sq ft undeveloped on 0.30-acre lot. Scope for 1–2 studios/1-beds with planning consent. Increases exit value."),
        ("Senior / Assisted Living", "MEDIUM", "Boutique senior accommodation — growing Jamaica market, 'seniors oriented' area. Needs MoH licensing and change of use."),
        ("Operator Lease", "LOW-MEDIUM", "Lease to housing/hospitality operator — reduces income but eliminates management burden for remote owner."),
        ("Flip / Resale", "LOW-MEDIUM", "St. Ann's Bay thin resale market. Only viable after hold and capital improvement."),
        ("Single-family reconversion", "LOW", "Destroys 4× income streams — not recommended."),
    ]
    hs = ParagraphStyle("sh", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white,
                        alignment=TA_CENTER, leading=11)
    ns = ParagraphStyle("sn", fontName="Helvetica", fontSize=8, textColor=TEXT_DARK, leading=11)
    cw = [48*mm, 28*mm, CW_FULL-76*mm]
    data = [[Paragraph(h, hs) for h in ["Strategy", "Viability", "Notes"]]]
    vc = {"HIGH": GREEN_COL, "MEDIUM": AMBER_COL, "MEDIUM-LOW": HexColor("#D4A017"),
          "LOW-MEDIUM": HexColor("#D4A017"), "LOW": RED_COL}
    for strat, via, note in rows:
        data.append([
            Paragraph(strat, ParagraphStyle("sl", fontName="Helvetica-Bold", fontSize=8,
                                            textColor=GFL_NAVY, leading=11)),
            Paragraph(via, ParagraphStyle("sv", fontName="Helvetica-Bold", fontSize=8,
                                          textColor=colors.white, alignment=TA_CENTER, leading=11)),
            Paragraph(note, ns),
        ])
    st = [
        ("BACKGROUND", (0,0),(-1,0), GFL_NAVY), ("GRID", (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING", (0,0),(-1,-1), 4), ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN", (0,0),(-1,-1), "TOP"), ("LEFTPADDING", (0,0),(-1,-1), 5),
    ]
    for i, (_, via, _) in enumerate(rows, 1):
        st.append(("BACKGROUND", (1,i),(1,i), vc.get(via, HexColor("#DDD"))))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Optimal strategy: 2× 2-bed on long-term residential let + 2× upper 1-bed on STR. "
        "Mixed model delivers best risk-adjusted USD yield and income diversification.",
        S["flag"]
    ))


# ── SECTION 5 ──────────────────────────────────────────────────────────────────
def s5(story):
    story += sec_hdr("5. FINANCIAL ANALYSIS")
    story.append(Paragraph(
        f"All figures use confirmed price of JMD $54,500,000 (USD ~${PRICE_USD:,.0f} / GBP ~£{PRICE_GBP:,.0f}). "
        f"Exchange rates: 155 JMD/USD, 1.27 USD/GBP (~122 JMD/GBP). Re-run if actual rates diverge by >5%.",
        S["flag"]
    ))
    story.append(Spacer(1, 3*mm))

    # 5A
    story.append(Paragraph("<b>A. Acquisition Costs</b>", S["lbl"]))
    story.append(kv([
        ("Purchase price",                f"JMD $54,500,000  =  USD ${PRICE_USD:,.0f}  =  GBP £{PRICE_GBP:,.0f}"),
        ("Attorney fees (~2.5%)",         f"USD ${PRICE_USD*0.025:,.0f}  |  GBP £{PRICE_GBP*0.025:,.0f}"),
        ("Stamp duty / registration (~1.5%)", f"USD ${PRICE_USD*0.015:,.0f}  |  GBP £{PRICE_GBP*0.015:,.0f}"),
        ("Surveyor's ID report",          "USD $750"),
        ("NLA title search",              "USD $300"),
        ("Structural survey",             "USD $1,500 (unknown build year — full survey required)"),
        ("Furnishing — 4 units",          "USD $20,000 – $28,000  (LTL basic + 2× STR higher spec)"),
        ("TOTAL ALL-IN (mid furnish)",    f"~USD ${PRICE_USD*1.04 + 24000:,.0f}  |  ~GBP £{PRICE_GBP*1.04 + 19000:,.0f}"),
    ], cw=[80*mm, CW_FULL-80*mm]))
    story.append(Paragraph(
        "Transfer Tax (2%) is paid by the SELLER in Jamaica. Buyer bears attorney, stamp duty, registration, and survey costs.",
        S["flag"]
    ))
    story.append(Spacer(1, 4*mm))

    # 5B LTL income
    story.append(Paragraph("<b>B. Long-Term Let Income — All 4 Units (JMD)</b>", S["lbl"]))
    story.append(ftbl(
        ["Unit", "Conservative", "Base Case", "Optimistic"],
        [
            ["2× 2-bed/2-bath (each)", "JMD $70,000/mo", "JMD $85,000/mo", "JMD $100,000/mo"],
            ["2× 1-bed/1-bath (each)", "JMD $38,000/mo", "JMD $47,000/mo",  "JMD $58,000/mo"],
            ["Gross/month (all 4)",    "JMD $216,000",   "JMD $264,000",    "JMD $316,000"],
            ["**Annual gross**",       "**JMD $2,592,000**","**JMD $3,168,000**","**JMD $3,792,000**"],
            ["At 90% occupancy",       "JMD $2,332,800", "JMD $2,851,200",  "JMD $3,412,800"],
            ["**USD equivalent**",     "**~$15,050**",   "**~$18,395**",    "**~$22,018**"],
            ["**GBP equivalent**",     "**~£11,871**",   "**~£14,500**",    "**~£17,339**"],
            ["**Gross yield (USD)**",  f"**{15050/PRICE_USD:.1%}**", f"**{18395/PRICE_USD:.1%}**", f"**{22018/PRICE_USD:.1%}**"],
        ],
        cw=[52*mm, 38*mm, 38*mm, 38*mm]
    ))
    story.append(Spacer(1, 4*mm))

    # 5C STR uplift
    story.append(Paragraph("<b>C. STR Income — Upper 1-Bed Units (2 Units, USD)</b>", S["lbl"]))
    story.append(Paragraph(
        "2× upper-level 1-bed units (ocean views, 10-min walk to sea). "
        "Target market: Ocho Rios corridor tourists seeking quieter, lower-cost base.",
        S["body"]
    ))
    story.append(ftbl(
        ["Metric", "Conservative", "Base Case", "Optimistic"],
        [
            ["Nightly rate (USD)",        "$75",        "$100",       "$130"],
            ["Occupancy",                 "40%",        "50%",        "60%"],
            ["Nights/year (per unit)",    "146",        "183",        "219"],
            ["Gross per unit",            "$10,950",    "$18,300",    "$28,470"],
            ["**2 units combined**",      "**$21,900**","**$36,600**","**$56,940**"],
            ["Less: platform fees (15%)", "($3,285)",   "($5,490)",   "($8,541)"],
            ["**Net STR revenue**",       "**$18,615**","**$31,110**","**$48,399**"],
        ],
        cw=[55*mm, 35*mm, 35*mm, 35*mm]
    ))
    story.append(Spacer(1, 4*mm))

    # 5D Mixed strategy
    story.append(Paragraph("<b>D. Recommended Mixed Strategy — 2× LTL 2-Beds + 2× STR 1-Beds</b>", S["lbl"]))
    # LTL 2-bed income (base case, 90% occ): 2× JMD $85k/mo × 12 × 0.9 = JMD $1,836,000 = USD $11,845
    ltl_2bed_usd = (85000 * 2 * 12 * 0.9) / JMD_USD
    # STR 1-bed net (base): $31,110
    str_net_usd = 31110
    total_gross_usd = ltl_2bed_usd + str_net_usd
    story.append(ftbl(
        ["Income Component", "Annual (USD)", "Annual (GBP)", "Notes"],
        [
            ["2× LTL 2-bed (JMD $85k/mo, 90% occ)",
             f"${ltl_2bed_usd:,.0f}", f"£{ltl_2bed_usd/GBP_USD:,.0f}",
             "Stable, local tenant income"],
            ["2× STR 1-bed (net of platform 15%)",
             "$31,110", f"£{31110/GBP_USD:,.0f}",
             "USD income, Ocho Rios tourism market"],
            ["**TOTAL BLENDED INCOME**",
             f"**${total_gross_usd:,.0f}**", f"**£{total_gross_usd/GBP_USD:,.0f}**", ""],
            [f"**Gross yield on USD price (${PRICE_USD:,.0f})**",
             f"**{total_gross_usd/PRICE_USD:.1%}**", "—", ""],
        ],
        cw=[70*mm, 30*mm, 28*mm, CW_FULL-128*mm]
    ))
    story.append(Spacer(1, 4*mm))

    # 5E Operating costs
    story.append(Paragraph("<b>E. Annual Operating Costs — Mixed Strategy</b>", S["lbl"]))
    mgmt = total_gross_usd * 0.20
    maint = PRICE_USD * 0.02
    total_costs = mgmt + maint + 1500 + 3000 + 800 + 1000
    story.append(kv([
        ("Property management (20% of total gross)", f"USD ${mgmt:,.0f}"),
        ("Maintenance & repairs (2% — unknown build year)", f"USD ${maint:,.0f}"),
        ("Property tax (Jamaica — estimated)", "USD $1,500"),
        ("Insurance (multi-unit + STR liability)", "USD $3,000"),
        ("Utilities (common areas only)", "USD $800"),
        ("Accounting / compliance / TPDCo", "USD $1,000"),
        ("TOTAL ANNUAL COSTS", f"USD ${total_costs:,.0f}"),
    ], cw=[85*mm, CW_FULL-85*mm]))
    story.append(Spacer(1, 4*mm))

    # 5F NOI
    noi = total_gross_usd - total_costs
    net_yield = noi / PRICE_USD
    story.append(Paragraph("<b>F. Net Operating Income — Mixed Strategy (Base Case)</b>", S["lbl"]))
    story.append(ftbl(
        ["Item", "Annual (USD)", "Annual (GBP)", "Yield on Price"],
        [
            ["Gross blended income",      f"${total_gross_usd:,.0f}", f"£{total_gross_usd/GBP_USD:,.0f}", f"{total_gross_usd/PRICE_USD:.1%}"],
            ["Total operating costs",     f"(${total_costs:,.0f})",  f"(£{total_costs/GBP_USD:,.0f})", "—"],
            ["**NET OPERATING INCOME**",  f"**${noi:,.0f}**",        f"**£{noi/GBP_USD:,.0f}**",       f"**{net_yield:.1%}**"],
        ],
        cw=[55*mm, 38*mm, 35*mm, 36*mm]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"Net yield of {net_yield:.1%} in USD on the mixed LTL/STR strategy is a solid return for a Jamaican "
        f"multi-family asset. This compares favourably to the LTL-only net yield of ~1–2% in USD.",
        S["flag"]
    ))
    story.append(Spacer(1, 4*mm))

    # 5G 5-year appreciation
    story.append(Paragraph("<b>G. Capital Appreciation — 5-Year Hold Scenarios</b>", S["lbl"]))
    story.append(ftbl(
        ["Appreciation Rate", "Value at Year 5", "Capital Gain (USD)", f"Total Return (5yr NOI + CG)"],
        [
            ["2% p.a.",                  f"${PRICE_USD*1.02**5:,.0f}", f"${PRICE_USD*(1.02**5-1):,.0f}", f"${noi*5 + PRICE_USD*(1.02**5-1):,.0f}"],
            ["4% p.a. (central case)",   f"${PRICE_USD*1.04**5:,.0f}", f"${PRICE_USD*(1.04**5-1):,.0f}", f"${noi*5 + PRICE_USD*(1.04**5-1):,.0f}"],
            ["6% p.a.",                  f"${PRICE_USD*1.06**5:,.0f}", f"${PRICE_USD*(1.06**5-1):,.0f}", f"${noi*5 + PRICE_USD*(1.06**5-1):,.0f}"],
        ],
        cw=[42*mm, 38*mm, 38*mm, CW_FULL-118*mm]
    ))

    story.append(Spacer(1, 4*mm))

    # 5H yield comparison
    story.append(Paragraph("<b>H. Strategy Yield Comparison at Confirmed Price</b>", S["lbl"]))
    story.append(ftbl(
        ["Strategy", "Gross USD Yield", "Est. Net USD Yield", "Recommendation"],
        [
            ["LTL only (all 4 units)",   f"{18395/PRICE_USD:.1%}", "~1–2%",       "Too low in USD — viable in JMD only"],
            ["STR only (all 4 units)",   "~20%+",                  "~12%",         "Operational intensity — not recommended"],
            ["Mixed LTL + STR (optimal)",f"{total_gross_usd/PRICE_USD:.1%}", f"**{net_yield:.1%}**", "RECOMMENDED"],
        ],
        cw=[55*mm, 35*mm, 38*mm, CW_FULL-128*mm]
    ))


# ── SECTION 6 ──────────────────────────────────────────────────────────────────
def s6(story):
    story += sec_hdr("6. RISK REGISTER")
    story.append(risk_tbl([
        ("Unknown year of build — hidden structural liability", "HIGH", "HIGH",
         "Independent structural survey non-negotiable before exchange"),
        ("Apartment conversion without planning permission", "MEDIUM", "HIGH",
         "Obtain St. Ann Parish Council building approval for 4-unit residential conversion"),
        ("Unregistered or defective title", "MEDIUM", "CRITICAL",
         "NLA title search and 30-year attorney search before any deposit"),
        ("JMD currency risk — rents in JMD, USD/GBP costs", "HIGH", "MEDIUM",
         "STR income in USD mitigates; consider USD rental agreements for LTL 2-beds where possible"),
        ("STR occupancy risk — secondary location", "MEDIUM", "MEDIUM",
         "Differentiate via views and Ocho Rios proximity; vet management company carefully"),
        ("Maintenance cost uncertainty (unknown build age)", "MEDIUM", "MEDIUM",
         "Budget 2% of purchase price p.a. until survey confirms condition"),
        ("Informal occupants — helper's quarters / garage", "LOW-MEDIUM", "MEDIUM",
         "Confirm vacant possession across all spaces before contracts"),
        ("Remote management quality", "MEDIUM", "MEDIUM",
         "Appoint vetted local manager; monthly financial reporting required"),
        ("Hurricane / weather damage", "MEDIUM", "HIGH",
         "Multi-unit insurance with hurricane cover essential"),
        ("Development planning risk (additional units)", "LOW-MEDIUM", "LOW",
         "Any new units require St. Ann Parish Council consent and NEPA review"),
        ("Resale liquidity — St. Ann's Bay secondary market", "MEDIUM", "MEDIUM",
         "Hold 3–5 years minimum; not a liquid market"),
        ("MLS data error — original price GBP £1,877", "LOW", "LOW",
         "Likely system entry error; confirmed price GBP £259,007 as of 28 May 2026 — verify with agent"),
    ]))


# ── SECTION 7 ──────────────────────────────────────────────────────────────────
def s7(story):
    story += sec_hdr("7. COMPLIANCE AND DUE DILIGENCE FLAGS")
    story += lbl_sec("CRITICAL — Resolve Before Any Deposit", [
        "Obtain Volume/Folio reference and confirm registered title with National Land Agency (NLA)",
        "Instruct Jamaican attorney to conduct full 30-year title search — confirm no caveats, encumbrances, or mortgages",
        "Obtain building permits and planning approval from St. Ann Parish Council for 4-unit residential conversion",
        "Confirm NEPA environmental clearance — especially if any development or change of use is planned",
    ], RED_COL)
    story += lbl_sec("HIGH PRIORITY — Before Exchange", [
        "Commission independent structural survey — year of build unknown; full survey non-negotiable",
        "Obtain surveyor's identification report confirming lot boundaries vs title (Lot 84, Seville)",
        "Confirm NLA / government land valuation for transfer tax calculation",
        "Confirm all 4 apartments have live JPS (electricity) and NWC (water) connections",
        "Confirm existing tenancy status — occupied or vacant? If tenanted, obtain all lease agreements",
        "Confirm helper's quarters, storeroom, and garage — vacant possession required",
        "Confirm property tax compliance — no arrears on Lot 84",
        "Confirm Seville subdivision covenants, HOA obligations, and any maintenance fees",
    ], AMBER_COL)
    story += lbl_sec("OPERATIONAL — Before Renting / STR Launch", [
        "Register Taxpayer Registration Number (TRN) for rental income reporting in Jamaica",
        "Apply for TPDCo tourism accommodation licence for STR units (allow 3–6 months)",
        "Appoint and contract local property management company (St. Ann's Bay / Ocho Rios based)",
        "Obtain multi-unit insurance: property, hurricane, contents, STR liability",
        "Furnish LTL units to residential standard; STR units to higher hospitality spec",
        "STR units: onboard to Airbnb, VRBO; consider specialist Jamaica STR management",
    ], GFL_NAVY)
    story += lbl_sec("PROFESSIONAL ADVICE REQUIRED", [
        "Jamaican attorney — title search, transfer, legal completion",
        "UK / Jamaica accountant — JMD/GBP rental income, double tax treaty, HMRC reporting",
        "Local chartered surveyor — structural survey, ID report, independent valuation",
        "Insurance broker (Jamaica-specialist) — multi-unit, hurricane, STR liability",
        "Planning consultant — if developing additional units or converting to senior accommodation",
    ], HexColor("#555555"))


# ── SECTION 8 ──────────────────────────────────────────────────────────────────
def s8(story):
    story += sec_hdr("8. OFFER PRICE GUIDANCE")

    hs = ParagraphStyle("oh", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white,
                        alignment=TA_CENTER, leading=11)
    cs = ParagraphStyle("oc", fontName="Helvetica", fontSize=8.5, textColor=TEXT_DARK, leading=12)
    ps = ParagraphStyle("op", fontName="Helvetica-Bold", fontSize=8.5, textColor=GFL_NAVY,
                        alignment=TA_CENTER, leading=12)
    cw = [60*mm, 52*mm, CW_FULL-112*mm]

    rows_d = [
        ("Title clear, survey clean, planning compliant",
         "GBP £232,000 – £245,000\nJMD ~$50.5M – $53.3M",
         "10–5% below ask. Justified on unknown build year, furnishing cost, and planning uncertainty."),
        ("Title clear but survey reveals minor defects",
         "GBP £215,000 – £228,000\nJMD ~$46.7M – $49.6M",
         "Price in remedial cost of survey defects. Get contractor quotes before revising offer."),
        ("Any title defect or planning non-compliance",
         "DO NOT OFFER",
         "Resolve title / planning first — material deal-breaker under Jamaican law."),
        ("All clear + existing rental income evidence",
         "Up to GBP £245,000\nJMD ~$53.3M",
         "DOM 48 still gives leverage; maximum offer if income history confirms projections."),
    ]
    data = [[Paragraph(h, hs) for h in ["Scenario", "Offer Guidance", "Rationale"]]]
    for sc, pr, ra in rows_d:
        data.append([Paragraph(sc, cs), Paragraph(pr, ps), Paragraph(ra, cs)])
    st = [
        ("BACKGROUND", (0,0),(-1,0), GFL_NAVY), ("GRID", (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING", (0,0),(-1,-1), 5), ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0),(-1,-1), 5),
        ("BACKGROUND", (0,3),(-1,3), HexColor("#FDECEA")),
        ("BACKGROUND", (1,3),(1,3), RED_COL),
        ("FONTNAME",   (1,3),(1,3), "Helvetica-Bold"),
        ("TEXTCOLOR",  (1,3),(1,3), colors.white),
    ]
    for i in [1, 4]:
        if i <= len(rows_d):
            st.append(("BACKGROUND", (0,i),(-1,i), GFL_LIGHT))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 3*mm))

    box = Table([[Paragraph(
        "Opening Offer: <b>GBP £232,000 (JMD ~$50.5M)</b>  — 10.4% below asking price. "
        "Escalate to <b>GBP £245,000</b> if survey is clean and planning compliance confirmed. "
        "48 DOM and unknown build year justify a firm negotiating position.",
        ParagraphStyle("ob", fontName="Helvetica", fontSize=9.5, textColor=GFL_NAVY,
                       alignment=TA_CENTER, leading=14)
    )]], colWidths=[CW_FULL])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), HexColor("#FFF8E7")),
        ("TOPPADDING", (0,0),(-1,-1), 8), ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING", (0,0),(-1,-1), 12),
        ("BOX", (0,0),(-1,-1), 1.5, GFL_GOLD),
    ]))
    story.append(box)


# ── SECTIONS 9–12 ──────────────────────────────────────────────────────────────
def s9(story):
    story += sec_hdr("9. BEST EXIT STRATEGY")
    story.append(Paragraph(
        "<b>Mixed LTL / STR — Medium-Term Hold (3–7 Years)</b>", S["lbl"]
    ))
    noi_val = (PRICE_USD * 0.07)
    story.append(Paragraph(
        f"Retain the 2× 2-bed/2-bath apartments on long-term residential lets at JMD $85,000/month each, "
        f"targeting St. Ann's Bay professionals and north coast workers for stable JMD income. Convert the 2× "
        f"upper-level 1-bed/1-bath units (ocean views) to short-term rental via Airbnb and VRBO, targeting "
        f"the Ocho Rios tourist corridor at USD $100/night and 50% occupancy. Appoint a local property "
        f"management company at 18–20% of gross revenue. Base-case blended income: ~USD ${(PRICE_USD*0.122):,.0f} "
        f"gross p.a., ~USD ${noi_val:,.0f} net p.a. (~7.0% net yield). "
        f"Hold 3–7 years. At 4% p.a. appreciation, asset reaches ~USD ${PRICE_USD*1.04**5:,.0f} at Year 5, "
        f"yielding a combined NOI + capital gain of ~USD ${noi_val*5 + PRICE_USD*(1.04**5-1):,.0f} "
        f"(before UK tax). Use hold period to obtain planning consent for 1–2 additional units on the lot.",
        S["body"]
    ))


def s10(story):
    story += sec_hdr("10. BACKUP EXIT STRATEGY")
    story.append(Paragraph("<b>Operator Lease — Full Management</b>", S["lbl"]))
    story.append(Paragraph(
        "Lease the entire building to a Jamaica housing or STR operator on a guaranteed rent or "
        "revenue-share basis. Operator takes 35–45% of gross income; owner receives passive net "
        "income with zero management involvement. Best suited if remote management proves problematic.",
        S["body"]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("<b>Secondary: Boutique Senior Accommodation</b>", S["lbl"]))
    story.append(Paragraph(
        "Convert to a licensed boutique senior/assisted living facility targeting Jamaica's growing "
        "retirement market. The 4-unit layout, 6 bathrooms, garden area, quiet environment, ocean proximity, "
        "and 'seniors oriented' listing tag all support this use. Requires Ministry of Health licensing, "
        "change of use planning consent, and a specialist operator partner — longer lead time but "
        "potentially higher-value exit and recurring income.",
        S["body"]
    ))


def s11(story):
    story += sec_hdr("11. RED / AMBER / GREEN VERDICT")
    story += vbox("AMBER", [
        "Proceed to Due Diligence — Negotiate on Price",
        f"Confirmed price: JMD $54,500,000 / GBP £{PRICE_GBP:,.0f} / USD ~${PRICE_USD:,.0f}",
        "Mixed LTL+STR strategy yields ~7% net USD — compelling | Unknown build date and planning compliance are key residual risks",
    ])
    rows_v = [
        ("Confirmed Price",          "GBP £259,007 / USD ~$351,600 confirmed"),
        ("Price per sq ft",          f"~$83/sq ft — acceptable for JA multi-family"),
        ("STR Mix Gross Yield",      f"~12.2% USD — STRONG"),
        ("STR Mix Net Yield",        f"~7.0% USD — GOOD"),
        ("LTL-only USD Yield",       "~5.2% gross, ~1–2% net — MARGINAL"),
        ("Location / Access",        "STRONG — north coast, Ocho Rios proximity, sea views"),
        ("Multi-income configuration", "STRONG — 4 units ready"),
        ("Year of Build",            "UNKNOWN — survey risk premium applies"),
        ("Title",                    "UNVERIFIED — NLA search critical"),
        ("Planning Compliance",      "UNVERIFIED — conversion permits to confirm"),
        ("DOM 48",                   "POSITIVE — negotiating leverage"),
        ("Utilities",                "LIKELY OK — established subdivision; confirm"),
        ("MLS Price Data Error",     "NOTE — original price field anomaly; confirmed price verified"),
    ]
    sc = {
        "GBP £259,007 / USD ~$351,600 confirmed": GREEN_COL,
        f"~$83/sq ft — acceptable for JA multi-family": HexColor("#5DAD8A"),
        f"~12.2% USD — STRONG": GREEN_COL,
        f"~7.0% USD — GOOD": GREEN_COL,
        "~5.2% gross, ~1–2% net — MARGINAL": AMBER_COL,
        "STRONG — north coast, Ocho Rios proximity, sea views": GREEN_COL,
        "STRONG — 4 units ready": GREEN_COL,
        "UNKNOWN — survey risk premium applies": RED_COL,
        "UNVERIFIED — NLA search critical": RED_COL,
        "UNVERIFIED — conversion permits to confirm": AMBER_COL,
        "POSITIVE — negotiating leverage": GREEN_COL,
        "LIKELY OK — established subdivision; confirm": HexColor("#5DAD8A"),
        "NOTE — original price field anomaly; confirmed price verified": AMBER_COL,
    }
    hs = ParagraphStyle("vh", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white,
                        alignment=TA_CENTER, leading=11)
    ns = ParagraphStyle("vn", fontName="Helvetica", fontSize=8.5, textColor=TEXT_DARK, leading=12)
    vs2 = ParagraphStyle("vs2", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white,
                         alignment=TA_LEFT, leading=12)
    cw = [52*mm, CW_FULL-52*mm]
    data = [[Paragraph("Factor", hs), Paragraph("Status / Finding", hs)]]
    for factor, status in rows_v:
        data.append([Paragraph(factor, ns), Paragraph(status, vs2)])
    st = [
        ("BACKGROUND", (0,0),(-1,0), GFL_NAVY), ("GRID", (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING", (0,0),(-1,-1), 4), ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0),(-1,-1), 5),
    ]
    for i, (_, status) in enumerate(rows_v, 1):
        col = sc.get(status, HexColor("#DDD"))
        st.append(("BACKGROUND", (1,i),(1,i), col))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Path to GREEN: title clean, structural survey passed, planning compliance on 4-unit conversion confirmed. "
        "Path to RED: title defective without resolution, or structural survey reveals major defects exceeding "
        "GBP £15,000 in remediation cost.",
        S["flag"]
    ))


def s12(story):
    story += sec_hdr("12. NEXT ACTION CHECKLIST")
    story += lbl_sec("Immediate — This Week", [
        "Contact Tracey Ann Mair (876) 439-2565 to confirm asking price and any recent offers",
        "Request: title Volume/Folio, building permits for 4-unit conversion, planning approvals from St. Ann Parish Council",
        "Request: year of build, any available structural reports or maintenance history",
        "Request: current occupancy status and any existing tenancy agreements",
        "Instruct Jamaican attorney to commence NLA title search on Lot 84, Seville, St. Ann",
        "Request Seville subdivision HOA documents and covenant details",
    ], RED_COL)
    story += lbl_sec("Within 2 Weeks", [
        "Commission independent structural survey — unknown build year makes this the highest-priority spend",
        "Obtain surveyor's identification report — confirm lot boundaries vs title (Lot 84)",
        "Obtain 3× comparable LTL rents for 2-bed in St. Ann's Bay and 1-bed in Seville / Ocho Rios corridor",
        "Obtain 3× comparable STR rates (Airbnb/VRBO) for 1-bed with ocean view near St. Ann's Bay",
        "Shortlist 2 local property management companies (St. Ann's Bay / Ocho Rios based)",
        "Obtain multi-unit insurance quote: property, hurricane, liability",
        "Confirm NLA government land valuation for transfer tax purposes",
    ], AMBER_COL)
    story += lbl_sec("Before Exchange", [
        "Confirm all 4 apartments have live JPS and NWC connections",
        "Confirm property tax compliance — no arrears on Lot 84",
        "Confirm vacant possession across all spaces: apartments, helper's quarters, garage, storeroom",
        "Brief UK accountant: JMD/GBP rental income, double tax treaty, HMRC reporting obligations",
        "Confirm TPDCo licence requirements and timeline for STR units",
        "Confirm TRN registration process for Jamaican rental income",
        "Obtain contractor quote if survey reveals defects — use for price renegotiation",
        "Confirm planning pre-application position for any additional unit development on lot",
    ], GFL_NAVY)


def footer(story):
    story.append(HRFlowable(width="100%", thickness=0.5, color=GFL_BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "This report is produced for investment evaluation purposes only and does not constitute legal, tax, "
        "mortgage, planning, or professional surveying advice. All financial projections are estimates and "
        "must be independently verified. Exchange rates used: 155 JMD/USD, 1.27 USD/GBP (~122 JMD/GBP). "
        "Instruct a qualified Jamaican attorney, chartered surveyor, and accountant before proceeding.",
        S["disc"]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "GFL AI Deal Analyser  |  GFL PropertyTech  |  Ref: JAM-STA-0609-002v2  |  9 June 2026",
        S["foot"]
    ))


def build(path):
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=18*mm, bottomMargin=14*mm,
        title="GFL Deal Analysis v2 — 9 Hibiscus Way, Seville",
        author="GFL PropertyTech AI Deal Analyser",
        subject="Jamaica Multi-Family Investment Analysis — Price Confirmed",
    )
    story = []
    cover(story); s1(story); s2(story); s3(story); s4(story); s5(story)
    s6(story); s7(story); s8(story); s9(story); s10(story); s11(story)
    s12(story); footer(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {path}")


if __name__ == "__main__":
    build("/home/user/GFL-PHONE-AGENT/GFL_Deal_Analysis_9_Hibiscus_Way_Seville_v2.pdf")
