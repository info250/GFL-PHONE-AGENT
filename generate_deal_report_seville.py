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


def sty(name, **kw):
    defaults = dict(fontName="Helvetica", fontSize=9, textColor=TEXT_DARK,
                    leading=13, spaceAfter=3)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


STYLES = {
    "title":     sty("title",    fontName="Helvetica-Bold", fontSize=20,
                     textColor=colors.white, alignment=TA_CENTER, leading=24),
    "subtitle":  sty("subtitle", fontSize=11, textColor=GFL_GOLD,
                     alignment=TA_CENTER, leading=14),
    "section":   sty("section",  fontName="Helvetica-Bold", fontSize=12,
                     textColor=colors.white, leading=16, leftIndent=6),
    "body":      sty("body",     alignment=TA_JUSTIFY, leftIndent=4),
    "bullet":    sty("bullet",   leftIndent=14, firstLineIndent=-10),
    "bold_lbl":  sty("bold_lbl", fontName="Helvetica-Bold", textColor=GFL_NAVY),
    "flag":      sty("flag",     fontName="Helvetica-Oblique", fontSize=8,
                     textColor=AMBER_COL, leading=11, leftIndent=4),
    "red_flag":  sty("red_flag", fontName="Helvetica-Bold", fontSize=8.5,
                     textColor=RED_COL, leading=11, leftIndent=4),
    "disclaimer":sty("disc",     fontName="Helvetica-Oblique", fontSize=7.5,
                     textColor=HexColor("#888888"), alignment=TA_CENTER, leading=10),
    "footer":    sty("footer",   fontSize=7, textColor=HexColor("#AAAAAA"),
                     alignment=TA_CENTER, leading=10),
    "v_text":    sty("v_text",   fontName="Helvetica", fontSize=9,
                     textColor=colors.white, alignment=TA_CENTER, leading=13),
    "v_title":   sty("v_title",  fontName="Helvetica-Bold", fontSize=16,
                     textColor=colors.white, alignment=TA_CENTER, leading=20),
}

CW_FULL = W - 28*mm


def sec_hdr(title):
    t = Table([[Paragraph(title, STYLES["section"])]], colWidths=[CW_FULL])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GFL_NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    return [Spacer(1, 5*mm), t, Spacer(1, 3*mm)]


def kv(rows, cw=None):
    if cw is None:
        cw = [65*mm, CW_FULL - 65*mm]
    ks = ParagraphStyle("k", fontName="Helvetica-Bold", fontSize=8.5,
                        textColor=GFL_NAVY, leading=12)
    vs = ParagraphStyle("v", fontName="Helvetica", fontSize=8.5,
                        textColor=TEXT_DARK, leading=12)
    data = [[Paragraph(k, ks), Paragraph(str(v), vs)] for k, v in rows]
    st = [
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("GRID",          (0,0),(-1,-1), 0.3, GFL_BORDER),
    ]
    for i in range(0, len(data), 2):
        st.append(("BACKGROUND", (0,i),(-1,i), GFL_LIGHT))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    return t


def fin_tbl(headers, rows, cw=None):
    if cw is None:
        n = len(headers)
        cw = [CW_FULL / n] * n
    hs = ParagraphStyle("fh", fontName="Helvetica-Bold", fontSize=8.5,
                        textColor=colors.white, alignment=TA_CENTER, leading=12)
    cs = ParagraphStyle("fc", fontName="Helvetica", fontSize=8.5,
                        textColor=TEXT_DARK, alignment=TA_CENTER, leading=12)
    bs = ParagraphStyle("fb", fontName="Helvetica-Bold", fontSize=8.5,
                        textColor=GFL_NAVY, alignment=TA_CENTER, leading=12)
    data = [[Paragraph(h, hs) for h in headers]]
    for row in rows:
        r = []
        for cell in row:
            s = cell.startswith("**")
            r.append(Paragraph(str(cell).replace("**",""), bs if s else cs))
        data.append(r)
    st = [
        ("BACKGROUND",    (0,0),(-1,0), GFL_NAVY),
        ("GRID",          (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]
    for i in range(1, len(data), 2):
        st.append(("BACKGROUND", (0,i),(-1,i), GFL_LIGHT))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    return t


def verdict_box(verdict, lines):
    col = {"GREEN": GREEN_COL, "AMBER": AMBER_COL, "RED": RED_COL}.get(verdict, AMBER_COL)
    inner = [[Paragraph(f"VERDICT: {verdict}", STYLES["v_title"])]]
    for l in lines:
        inner.append([Paragraph(l, STYLES["v_text"])])
    t = Table(inner, colWidths=[CW_FULL])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), col),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
    ]))
    return [Spacer(1, 4*mm), t, Spacer(1, 4*mm)]


def checklist(items):
    cs = ParagraphStyle("cb", fontName="Helvetica", fontSize=10,
                        textColor=GFL_NAVY, leading=13)
    is_ = ParagraphStyle("ci", fontName="Helvetica", fontSize=8.5,
                         textColor=TEXT_DARK, leading=13)
    data = [[Paragraph("☐", cs), Paragraph(item, is_)] for item in items]
    t = Table(data, colWidths=[8*mm, CW_FULL - 8*mm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("LINEBELOW",     (0,0),(-1,-1), 0.2, GFL_BORDER),
    ]))
    return t


def risk_tbl(rows):
    lh_col = {"LOW": HexColor("#D5F5E3"), "LOW-MEDIUM": HexColor("#FDEBD0"),
               "MEDIUM": HexColor("#FAD7A0"), "HIGH": HexColor("#F1948A"),
               "CRITICAL": HexColor("#E74C3C")}
    im_col = {"LOW": HexColor("#D5F5E3"), "MEDIUM": HexColor("#FAD7A0"),
               "HIGH": HexColor("#F1948A"), "CRITICAL": HexColor("#E74C3C")}
    hs = ParagraphStyle("rh", fontName="Helvetica-Bold", fontSize=8,
                        textColor=colors.white, alignment=TA_CENTER, leading=11)
    cs = ParagraphStyle("rc", fontName="Helvetica", fontSize=8,
                        textColor=TEXT_DARK, leading=11)
    ms = ParagraphStyle("rm", fontName="Helvetica-Bold", fontSize=8,
                        textColor=TEXT_DARK, alignment=TA_CENTER, leading=11)
    cw = [58*mm, 24*mm, 22*mm, CW_FULL - 104*mm]
    data = [[Paragraph(h, hs) for h in ["Risk", "Likelihood", "Impact", "Mitigation"]]]
    for risk, lh, im, mit in rows:
        data.append([Paragraph(risk, cs), Paragraph(lh, ms),
                     Paragraph(im, ms), Paragraph(mit, cs)])
    st = [
        ("BACKGROUND",    (0,0),(-1,0), GFL_NAVY),
        ("GRID",          (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
    ]
    for i, (_, lh, im, _) in enumerate(rows, 1):
        st.append(("BACKGROUND", (1,i),(1,i), lh_col.get(lh.upper(), HexColor("#FFF"))))
        st.append(("BACKGROUND", (2,i),(2,i), im_col.get(im.upper(), HexColor("#FFF"))))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    return t


def labelled_section(heading, items, col):
    ls = ParagraphStyle("ls", fontName="Helvetica-Bold", fontSize=9,
                        textColor=colors.white, leading=13)
    lt = Table([[Paragraph(heading, ls)]], colWidths=[CW_FULL])
    lt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), col),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    return [lt, checklist(items), Spacer(1, 3*mm)]


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GFL_NAVY)
    canvas.rect(0, H - 12*mm, W, 12*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.white)
    canvas.drawString(14*mm, H - 8*mm, "GFL AI DEAL ANALYSER  |  9 Hibiscus Way, Seville, St. Ann's Bay")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GFL_GOLD)
    canvas.drawRightString(W - 14*mm, H - 8*mm, f"Page {doc.page}  |  JAM-STA-0609-002")
    canvas.setFillColor(GFL_NAVY)
    canvas.rect(0, 0, W, 8*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#AAAAAA"))
    canvas.drawCentredString(W / 2, 2.5*mm,
        "GFL PropertyTech  |  Investment analysis only — not legal, tax or professional advice")
    canvas.restoreState()


# ── SECTIONS ───────────────────────────────────────────────────────────────────

def cover(story):
    hdr_sty = ParagraphStyle("ht", fontName="Helvetica-Bold", fontSize=20,
                              textColor=colors.white, alignment=TA_CENTER, leading=24)
    t = Table([[Paragraph("GFL AI DEAL ANALYSER", hdr_sty)]], colWidths=[CW_FULL])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GFL_NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=GFL_GOLD))
    story.append(Spacer(1, 6*mm))

    p_sty  = ParagraphStyle("pt", fontName="Helvetica-Bold", fontSize=18,
                             textColor=GFL_NAVY, alignment=TA_CENTER, leading=24)
    s_sty  = ParagraphStyle("ps", fontName="Helvetica", fontSize=12,
                             textColor=TEXT_MID, alignment=TA_CENTER, leading=16)
    pr_sty = ParagraphStyle("pp", fontName="Helvetica-Bold", fontSize=20,
                             textColor=RED_COL, alignment=TA_CENTER, leading=26)

    story.append(Paragraph("9 Hibiscus Way", p_sty))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("Seville, St. Ann's Bay, St. Ann, Jamaica", s_sty))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("ASKING PRICE: NOT PROVIDED", pr_sty))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("MLS# 100907  |  6 Bed / 6 Bath  |  4,245 sq ft  |  0.30 acres", s_sty))
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GFL_BORDER))

    story += verdict_box("AMBER", [
        "Proceed to Due Diligence — Negotiate on Price",
        "Strong multi-family income asset | Development upside | Asking price must be confirmed before full Green",
    ])

    kf = [
        ("Property Type",       "Split-level house, converted to 4 apartments (2×2-bed, 2×1-bed)"),
        ("MLS#",                "100907  |  DOM: 48"),
        ("Location",            "Seville Subdivision, St. Ann's Bay, St. Ann — North Coast Highway"),
        ("Floor Size",          "4,245 sq ft total"),
        ("Lot Size",            "12,887 sq ft (0.2958 acres)"),
        ("Asking Price",        "NOT PROVIDED — request immediately from agent"),
        ("Best Strategy",       "Multi-family BTL with partial STR conversion + development option"),
        ("Estimated Gross Rent","JMD $2,808,000 – $3,120,000 p.a. (~USD $18,100 – $20,130)"),
        ("Indicative Max Price","USD $280,000 – $320,000 (for 6% gross yield target)"),
        ("Year Built",          "Not stated — independent structural survey essential"),
        ("Analysis Date",       "9 June 2026"),
        ("Reference",           "JAM-STA-0609-002"),
    ]
    story.append(kv(kf, cw=[70*mm, CW_FULL - 70*mm]))
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GFL_BORDER))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "This report is for investment evaluation only. It does not constitute legal, tax, mortgage, planning, "
        "or surveying advice. Instruct a qualified Jamaican attorney, chartered surveyor, and accountant "
        "before proceeding. All financial projections are estimates and must be independently verified.",
        STYLES["disclaimer"]
    ))
    story.append(PageBreak())


def s1_executive(story):
    story += sec_hdr("1. EXECUTIVE SUMMARY")
    story.append(Paragraph(
        "9 Hibiscus Way, Seville is a 4,245 sq ft split-level house in an established St. Ann subdivision, "
        "already converted and operating as four separate residential apartments (two 2-bed/2-bath and two "
        "1-bed/1-bath units). At 48 days on market the property has not yet found a buyer, which provides "
        "negotiating room. The deal presents as a viable income-producing multi-family asset with meaningful "
        "upside via STR conversion of upper-level units (ocean views, proximity to Ocho Rios) and development "
        "potential on the remaining lot area. The primary obstacle to a Green verdict is the <b>absent asking "
        "price</b> and an <b>unknown year of build</b> — both are critical inputs that must be confirmed before "
        "a definitive financial view can be formed. Subject to price, title, and survey, this is a sound "
        "income asset in a well-connected north coast location.",
        STYLES["body"]
    ))


def s2_overview(story):
    story += sec_hdr("2. PROPERTY OVERVIEW")
    rows = [
        ("Address",            "9 Hibiscus Way, Seville, St. Ann's Bay, St. Ann, Jamaica"),
        ("MLS#",               "100907"),
        ("Status",             "Active  |  DOM: 48"),
        ("Asking Price",       "NOT PROVIDED — confirm with agent immediately"),
        ("Style",              "Split-level house"),
        ("Subdivision",        "Seville"),
        ("Bedrooms / Baths",   "6 bed / 6 bath (across 4 apartments)"),
        ("Unit Mix",           "2× 2-bed/2-bath  +  2× 1-bed/1-bath"),
        ("Additional Spaces",  "Laundry room, helper's quarters, storeroom, utility space, large garage"),
        ("Floor Area",         "4,245 sq ft total"),
        ("Lot Size",           "12,887 sq ft (0.2958 acres)"),
        ("Year Built",         "NOT STATED — structural survey essential"),
        ("Condition",          "Modified/converted — condition to be verified by survey"),
        ("Furnishing",         "Unfurnished — furnishing budget required for rental-ready units"),
        ("Views",              "Ocean views from upper level"),
        ("Road Access",        "Paved road  |  North coast highway community"),
        ("Proximity",          "5 min to St. Ann's Bay town  |  20 min to Ocho Rios  |  10 min walk to sea"),
        ("Amenities noted",    "Additional accommodation, garden area, water heater"),
        ("Sale Type",          "For Sale"),
    ]
    story.append(kv(rows, cw=[60*mm, CW_FULL - 60*mm]))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "CRITICAL FLAG: No asking price in listing. Request from agent before any further steps.",
        STYLES["red_flag"]
    ))


def s3_area(story):
    story += sec_hdr("3. AREA AND DEMAND SUMMARY")
    story.append(Paragraph(
        "<b>St. Ann's Bay, St. Ann</b> is the capital of St. Ann Parish on Jamaica's north coast. It sits "
        "between Ocho Rios (20 min east, Jamaica's second-largest tourism hub) and Runaway Bay (15 min west). "
        "The town is a mixed-use urban centre with residential, commercial, health, and educational demand. "
        "Seville is an established residential subdivision offering paved road access and a quiet, family- and "
        "seniors-oriented environment with ocean proximity.",
        STYLES["body"]
    ))
    story.append(Spacer(1, 2*mm))

    demand = [
        ("Residential rental demand", "Steady demand from local professionals, public sector workers, healthcare staff (St. Ann's Bay Hospital nearby), and teachers."),
        ("Tourism spillover", "Ocho Rios proximity (20 min) generates STR demand for guests seeking quieter stays away from the town centre."),
        ("Ocean views / location", "Upper-level sea views add STR appeal; 10-min walk to the sea is a marketable feature on Airbnb."),
        ("Infrastructure", "Paved road access, north coast highway connectivity — strong commuter and access position."),
        ("Seniors market", "Listing notes 'seniors oriented' — supports a boutique senior living / assisted living strategy."),
        ("Ocho Rios economy", "Proximity to Ocho Rios port and tourism economy underpins stable employment and rental demand."),
    ]
    story.append(kv(demand, cw=[55*mm, CW_FULL - 55*mm]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>Demand Risks</b>", STYLES["bold_lbl"]))
    for r in [
        "St. Ann's Bay is a secondary rental market — residential rents are lower than Kingston or Montego Bay, limiting USD yield.",
        "STR demand is heavily dependent on Ocho Rios tourism proximity — direct Negril or Montego Bay beach access it is not.",
        "JMD-denominated rental income creates currency risk for a USD or GBP-based investor.",
        "Unknown year of build — older stock may carry hidden structural or utility costs.",
        "Multi-unit conversion compliance unknown — apartment use may not have formal planning/building permit approval.",
    ]:
        story.append(Paragraph(f"• {r}", STYLES["bullet"]))


def s4_strategy(story):
    story += sec_hdr("4. STRATEGY STACK ANALYSIS")

    rows = [
        ("Multi-family BTL", "HIGH", "Property already configured as 4 apartments — immediate income with minimal setup. Primary strategy."),
        ("Partial STR Conversion", "HIGH", "Convert 1–2 upper-level units to STR (ocean views). STR yield vs LTL can be 3–5× better per unit in JMD."),
        ("BRRRR", "MEDIUM", "Buy, refurbish to higher spec, refinance locally (high JMD rates ~10–12%) or remortgage UK asset. Viable with patience."),
        ("Development — Add Units", "MEDIUM", "0.30 acre lot has remaining buildable space (currently ~33% coverage). Could add 1–2 studio / 1-bed units with planning consent."),
        ("Senior / Assisted Living", "MEDIUM", "Listing flags 'seniors oriented' location. Could operate as boutique senior accommodation — growing Jamaica market. Requires licensing."),
        ("Flip / Resale", "MEDIUM-LOW", "St. Ann's Bay resale market is thin. Only viable after 3–5 year hold and capital improvement."),
        ("Operator Lease", "LOW-MEDIUM", "Lease entire building to a housing operator or property manager — reduces yield but removes management burden."),
        ("Single-Family Reconversion", "LOW", "Converting back to single family would destroy income streams and value — not recommended."),
        ("Villa / Tourism STR (full)", "LOW", "Full STR operation requires reconversion; location is not a primary villa rental market."),
    ]

    hs = ParagraphStyle("sh", fontName="Helvetica-Bold", fontSize=8,
                        textColor=colors.white, alignment=TA_CENTER, leading=11)
    ns = ParagraphStyle("sn", fontName="Helvetica", fontSize=8,
                        textColor=TEXT_DARK, leading=11)
    cw = [50*mm, 28*mm, CW_FULL - 78*mm]
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
        ("BACKGROUND",    (0,0),(-1,0), GFL_NAVY),
        ("GRID",          (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
    ]
    for i, (_, via, _) in enumerate(rows, 1):
        st.append(("BACKGROUND", (1,i),(1,i), vc.get(via, HexColor("#DDD"))))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Recommended strategy: Multi-family BTL as base, convert 1–2 upper-level units to STR to "
        "maximise USD yield, with a medium-term development option on remaining lot.",
        STYLES["flag"]
    ))


def s5_financials(story):
    story += sec_hdr("5. FINANCIAL ANALYSIS")
    story.append(Paragraph(
        "ASKING PRICE NOT PROVIDED. Financial analysis uses yield-based price sensitivity. "
        "All JMD figures converted at 155 JMD/USD. Re-run fully once asking price confirmed.",
        STYLES["red_flag"]
    ))
    story.append(Spacer(1, 3*mm))

    # 5A
    story.append(Paragraph("<b>A. Acquisition Cost Estimates (USD)</b>", STYLES["bold_lbl"]))
    story.append(Paragraph(
        "Note: Transfer Tax (2% of sale price) is paid by the seller in Jamaica. "
        "Buyer bears stamp duty, registration, attorney fees, and survey costs.",
        STYLES["flag"]
    ))
    story.append(kv([
        ("Purchase price",                    "TBC — see sensitivity table below"),
        ("Jamaican attorney fees (~2.5%)",    "~2.5% of purchase price"),
        ("Stamp duty / registration (~1.5%)", "~1.5% of purchase price"),
        ("Surveyor's ID report",              "USD $750"),
        ("NLA title search",                  "USD $300"),
        ("Structural survey",                 "USD $1,000 – $1,500"),
        ("Furnishing / fit-out (4 units)",    "USD $15,000 – $25,000 (unfurnished — STR units need more)"),
        ("TOTAL ACQUISITION COSTS (ex price)","~4% of purchase price + USD $17,550–$27,550"),
    ], cw=[85*mm, CW_FULL - 85*mm]))
    story.append(Spacer(1, 4*mm))

    # 5B Rental income
    story.append(Paragraph("<b>B. Rental Income Projection (Long-Term Let — JMD)</b>", STYLES["bold_lbl"]))
    story.append(fin_tbl(
        ["Unit", "Conservative", "Base Case", "Optimistic"],
        [
            ["2× 2-bed/2-bath (each)",  "JMD $70,000/mo",   "JMD $85,000/mo",   "JMD $100,000/mo"],
            ["2× 1-bed/1-bath (each)",  "JMD $38,000/mo",   "JMD $47,000/mo",   "JMD $58,000/mo"],
            ["Gross/month (all 4)",     "JMD $216,000",      "JMD $264,000",      "JMD $316,000"],
            ["**Annual gross**",        "**JMD $2,592,000**","**JMD $3,168,000**","**JMD $3,792,000**"],
            ["At 90% occupancy",        "JMD $2,332,800",    "JMD $2,851,200",    "JMD $3,412,800"],
            ["**USD equivalent**",      "**~$15,050**",      "**~$18,395**",      "**~$22,018**"],
        ],
        cw=[50*mm, 38*mm, 38*mm, 38*mm]
    ))
    story.append(Spacer(1, 3*mm))

    # 5C STR uplift
    story.append(Paragraph("<b>C. STR Uplift — Upper Units (2× 1-bed, Ocean View)</b>", STYLES["bold_lbl"]))
    story.append(Paragraph(
        "Converting 2 upper-level 1-bed units to STR (Airbnb/VRBO, Ocho Rios market) could significantly "
        "increase income. Ocho Rios/St. Ann STR rates for a 1-bed unit: USD $75–$130/night.",
        STYLES["body"]
    ))
    story.append(fin_tbl(
        ["Metric", "Conservative", "Base Case", "Optimistic"],
        [
            ["Nightly rate (USD)",       "$75",         "$100",        "$130"],
            ["Occupancy",                "40%",         "50%",         "60%"],
            ["Nights/year (per unit)",   "146",         "183",         "219"],
            ["Revenue per unit",         "$10,950",     "$18,300",     "$28,470"],
            ["**2 STR units combined**", "**$21,900**", "**$36,600**", "**$56,940**"],
            ["Less: platform fees (15%)", "($3,285)",   "($5,490)",    "($8,541)"],
            ["**Net STR revenue**",      "**$18,615**", "**$31,110**", "**$48,399**"],
        ],
        cw=[55*mm, 35*mm, 35*mm, 35*mm]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Mixed strategy (2× LTL 2-bed + 2× STR 1-bed) base case total income: "
        "USD $11,661 (LTL 2-beds) + USD $31,110 (STR 1-beds) = ~USD $42,771 gross p.a.",
        STYLES["flag"]
    ))
    story.append(Spacer(1, 4*mm))

    # 5D Operating costs
    story.append(Paragraph("<b>D. Annual Operating Costs (LTL Only Scenario)</b>", STYLES["bold_lbl"]))
    story.append(kv([
        ("Property management (10% of gross LTL)", "USD $1,500 – $1,840"),
        ("Maintenance & repairs (2% — older build)", "USD $6,000 – $8,000 (age unknown — conservative)"),
        ("Property tax (Jamaica)",                   "USD $1,200 – $1,800"),
        ("Insurance (multi-unit residential)",       "USD $2,500 – $3,500"),
        ("Utilities (common areas only)",            "USD $600 – $1,200"),
        ("Accounting / compliance",                  "USD $800"),
        ("TOTAL OPERATING COSTS",                    "~USD $12,600 – $17,140"),
    ], cw=[85*mm, CW_FULL - 85*mm]))
    story.append(Spacer(1, 4*mm))

    # 5E NOI
    story.append(Paragraph("<b>E. Net Operating Income (LTL — All 4 Units)</b>", STYLES["bold_lbl"]))
    story.append(fin_tbl(
        ["Scenario", "Gross Revenue (USD)", "Operating Costs", "**NOI**"],
        [
            ["Conservative", "$15,050", "$17,140", "**($2,090)**"],
            ["Base Case",    "$18,395", "$14,870", "**$3,525**"],
            ["Optimistic",   "$22,018", "$12,600", "**$9,418**"],
        ],
        cw=[40*mm, 50*mm, 48*mm, CW_FULL - 138*mm]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "LTL-only conservative scenario is cashflow negative at USD exchange rates — driven by currency "
        "conversion. In JMD terms, the same property is comfortably cashflow positive. "
        "STR conversion of upper units is strongly recommended to maximise USD returns.",
        STYLES["flag"]
    ))
    story.append(Spacer(1, 4*mm))

    # 5F Price sensitivity / yield
    story.append(Paragraph("<b>F. Price / Yield Sensitivity (Base Case NOI: USD $3,525 LTL | USD $18,000+ with STR mix)</b>",
                           STYLES["bold_lbl"]))
    story.append(fin_tbl(
        ["Asking Price", "Price/sq ft", "LTL Gross Yield", "STR Mix Gross Yield", "Recommendation"],
        [
            ["USD $200,000", "$47/sq ft", "9.2%", "21.4%", "Strong buy"],
            ["USD $250,000", "$59/sq ft", "7.4%", "17.1%", "**Good value**"],
            ["USD $300,000", "$71/sq ft", "6.1%", "14.3%", "Acceptable"],
            ["USD $350,000", "$82/sq ft", "5.3%", "12.2%", "Marginal"],
            ["USD $400,000", "$94/sq ft", "4.6%", "10.7%", "Negotiate down"],
            ["USD $450,000", "$106/sq ft", "4.1%", "9.5%", "Avoid without pool/dev upside"],
        ],
        cw=[32*mm, 28*mm, 32*mm, 38*mm, CW_FULL - 130*mm]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "STR mix gross yield uses USD $42,771 base-case blended income (2× LTL + 2× STR). "
        "Target purchase price: USD $250,000–$300,000 for a compelling risk-adjusted return.",
        STYLES["flag"]
    ))


def s6_risks(story):
    story += sec_hdr("6. RISK REGISTER")
    story.append(risk_tbl([
        ("Asking price unknown", "CRITICAL", "CRITICAL", "Request price from agent before any further analysis or site visit"),
        ("Unknown year of build — hidden structural risk", "HIGH", "HIGH", "Independent structural survey non-negotiable given unknown age"),
        ("Apartment conversion without planning permission", "MEDIUM", "HIGH", "Obtain St. Ann Parish Council building approval for conversion to 4 units"),
        ("Unregistered or defective title", "MEDIUM", "CRITICAL", "NLA title search and 30-year attorney search before any deposit"),
        ("JMD currency risk (rents in JMD, costs in USD/GBP)", "HIGH", "MEDIUM", "STR income in USD mitigates; consider USD-only rental agreements where possible"),
        ("Maintenance cost uncertainty (old build)", "MEDIUM", "MEDIUM", "Budget 2–2.5% of purchase price p.a. until post-survey condition confirmed"),
        ("Vacancy risk — St. Ann's Bay secondary market", "MEDIUM", "MEDIUM", "Mixed LTL/STR strategy reduces reliance on single income stream"),
        ("Remote management quality", "MEDIUM", "MEDIUM", "Appoint vetted local property manager; require monthly reporting"),
        ("Helper's quarters / garage — unauthorised occupation", "LOW-MEDIUM", "MEDIUM", "Confirm no informal occupants before purchase; clear legally if needed"),
        ("Development upside — planning risk", "LOW-MEDIUM", "LOW", "Any additional units require St. Ann Parish Council planning consent and NEPA review"),
        ("Hurricane / weather damage", "MEDIUM", "HIGH", "Multi-unit insurance essential; confirm flood zone and storm exposure"),
        ("St. Ann's Bay resale liquidity", "MEDIUM", "MEDIUM", "Hold 3–5 years minimum; not a liquid resale market"),
    ]))


def s7_compliance(story):
    story += sec_hdr("7. COMPLIANCE AND DUE DILIGENCE FLAGS")
    story += labelled_section("CRITICAL — Resolve Before Any Deposit", [
        "Obtain asking price from agent — not stated in listing",
        "Obtain Volume/Folio reference and confirm registered title with National Land Agency (NLA)",
        "Instruct Jamaican attorney to conduct full 30-year title search",
        "Confirm no encumbrances, caveats, mortgages, or disputes on title",
        "Obtain building permits and planning approval for conversion to 4 residential apartments from St. Ann Parish Council",
        "Confirm NEPA clearance and any environmental obligations",
    ], RED_COL)
    story += labelled_section("HIGH PRIORITY — Before Exchange", [
        "Commission independent structural survey — year of build unknown; defects must be quantified",
        "Obtain surveyor's identification report confirming lot boundaries match title",
        "Confirm NLA / government land valuation for transfer tax calculation",
        "Confirm utility connections: JPS (electricity), NWC (water), internet — confirm all 4 units connected",
        "Confirm property tax compliance — no arrears",
        "Confirm helper's quarters and garage occupancy status — no informal tenants",
        "Obtain details of any existing tenancy agreements — confirm vacant possession or assignment of leases",
        "Confirm road is NWA-maintained or private — establish maintenance responsibility",
        "Confirm HOA / Seville subdivision covenants and annual fees",
    ], AMBER_COL)
    story += labelled_section("OPERATIONAL — Before Renting / STR Launch", [
        "Register Taxpayer Registration Number (TRN) for Jamaican rental income",
        "TPDCo tourism accommodation licence required for any STR units",
        "Appoint and contract local property management company",
        "Obtain multi-unit insurance: property, hurricane, contents, liability",
        "Furnish units to target market standard (STR units to higher specification)",
        "STR units: onboard to Airbnb, VRBO, and specialist Jamaica platforms",
    ], GFL_NAVY)
    story += labelled_section("PROFESSIONAL ADVICE REQUIRED", [
        "Jamaican attorney — title search, transfer, and legal completion",
        "UK / Jamaica accountant — rental income tax, JMD/GBP reporting, double tax treaty",
        "Local chartered surveyor — structural survey, ID report, valuation",
        "Insurance broker (Jamaica-specialist) — multi-unit, hurricane, STR liability",
        "Planning consultant — if adding units or changing use to senior/assisted living",
    ], HexColor("#555555"))


def s8_offer(story):
    story += sec_hdr("8. OFFER PRICE GUIDANCE")

    hs = ParagraphStyle("oh", fontName="Helvetica-Bold", fontSize=8,
                        textColor=colors.white, alignment=TA_CENTER, leading=11)
    cs = ParagraphStyle("oc", fontName="Helvetica", fontSize=8.5,
                        textColor=TEXT_DARK, leading=12)
    ps = ParagraphStyle("op", fontName="Helvetica-Bold", fontSize=8.5,
                        textColor=GFL_NAVY, alignment=TA_CENTER, leading=12)

    rows_data = [
        ("Title clear, survey clean, full planning compliance, price ≤ USD $280,000", "USD $260,000 – $275,000", "Excellent yield, development upside, strong buy"),
        ("Title clear, survey clean, price USD $280,000 – $350,000", "Negotiate to USD $275,000 – $310,000", "Use unknown age and missing compliance as leverage"),
        ("Any title defect or planning non-compliance on conversion", "DO NOT OFFER", "Resolve title / planning first — material deal-breaker"),
        ("Listing price > USD $400,000", "Pass unless STR mix income confirmed with evidence", "Yields become marginal above $400k without STR uplift"),
    ]
    cw = [75*mm, 45*mm, CW_FULL - 120*mm]
    data = [[Paragraph(h, hs) for h in ["Scenario", "Offer Guidance", "Rationale"]]]
    for s, p, r in rows_data:
        data.append([Paragraph(s, cs), Paragraph(p, ps), Paragraph(r, cs)])
    st = [
        ("BACKGROUND",    (0,0),(-1,0), GFL_NAVY),
        ("GRID",          (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("BACKGROUND",    (0,3),(-1,3), HexColor("#FDECEA")),
        ("BACKGROUND",    (1,3),(1,3), RED_COL),
        ("FONTNAME",      (1,3),(1,3), "Helvetica-Bold"),
        ("TEXTCOLOR",     (1,3),(1,3), colors.white),
    ]
    for i in [1, 3]:
        if i != 3:
            st.append(("BACKGROUND", (0,i),(-1,i), GFL_LIGHT))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 3*mm))

    box = Table([[Paragraph(
        "Target Offer Range: <b>USD $260,000 – $295,000</b> — subject to confirmed asking price, "
        "clean title, structural survey passed, and planning compliance confirmed. "
        "48 DOM gives leverage to negotiate.",
        ParagraphStyle("ob", fontName="Helvetica", fontSize=9.5,
                       textColor=GFL_NAVY, alignment=TA_CENTER, leading=14)
    )]], colWidths=[CW_FULL])
    box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), HexColor("#FFF8E7")),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("BOX",           (0,0),(-1,-1), 1.5, GFL_GOLD),
    ]))
    story.append(box)


def s9_best_exit(story):
    story += sec_hdr("9. BEST EXIT STRATEGY")
    story.append(Paragraph(
        "<b>Multi-Family BTL + Partial STR Conversion — Medium-Term Hold (3–7 Years)</b>",
        STYLES["bold_lbl"]
    ))
    story.append(Paragraph(
        "Retain 2× 2-bed/2-bath units as long-term residential lets targeting St. Ann's Bay "
        "professionals and workers at JMD $85,000/month each. Convert 2× 1-bed upper-level units "
        "(ocean views) to short-term rental (Airbnb/VRBO), targeting the Ocho Rios tourist market "
        "at USD $100/night, 50% occupancy. Mixed-strategy base-case gross income: ~USD $42,771 p.a. "
        "Appoint a local management company at 18–20% of gross revenue.",
        STYLES["body"]
    ))
    story.append(Paragraph(
        "Hold for 3–7 years. During hold period, explore planning consent for additional unit(s) on "
        "remaining lot area (~8,640 sq ft undeveloped). Exit via sale to owner-occupier seeking "
        "income-generating property, or to a local investor. At a modest 3% p.a. capital appreciation, "
        "a USD $275,000 purchase reaches ~$319,000 at Year 5.",
        STYLES["body"]
    ))


def s10_backup(story):
    story += sec_hdr("10. BACKUP EXIT STRATEGY")
    story.append(Paragraph(
        "<b>Operator Lease / Full Management Lease</b>",
        STYLES["bold_lbl"]
    ))
    story.append(Paragraph(
        "Lease the entire building to a Jamaica housing or serviced accommodation operator on a "
        "guaranteed rent or net revenue share. Reduces management complexity for a remote owner. "
        "Typical operator take: 30–40% of gross income for full management.",
        STYLES["body"]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "<b>Secondary: Senior / Assisted Living Facility</b>",
        STYLES["bold_lbl"]
    ))
    story.append(Paragraph(
        "The 'seniors oriented' listing tag and the quiet, established subdivision environment suggest "
        "potential as a boutique senior accommodation facility. The 4-unit layout, multiple bathrooms, "
        "garden space, and north coast location align with Jamaica's growing senior care market. "
        "Requires Ministry of Health licensing, planning change of use, and specialist operator — "
        "a longer lead time strategy but potentially higher value exit.",
        STYLES["body"]
    ))


def s11_verdict(story):
    story += sec_hdr("11. RED / AMBER / GREEN VERDICT")
    story += verdict_box("AMBER", [
        "Proceed to Due Diligence — Negotiate on Price",
        "Strong multi-family income asset | Development and STR upside | Price confirmation and title verification required",
    ])

    rows_v = [
        ("Asking Price",            "MISSING",    "Not provided in listing — request before any action"),
        ("Location / Connectivity", "STRONG",     "North coast highway, 20 min to Ocho Rios, sea views"),
        ("Income Asset (4 units)",  "STRONG",     "Already configured for multiple income streams"),
        ("Floor Size / Lot",        "GOOD",       "4,245 sq ft building + 0.30 acre lot with development potential"),
        ("STR Potential",           "MEDIUM",     "Upper-level ocean view units viable for Ocho Rios STR market"),
        ("USD Yield (LTL only)",    "MARGINAL",   "JMD rents weak in USD — STR mix essential for acceptable USD return"),
        ("Year of Build",           "UNKNOWN",    "Not stated — structural survey essential before exchange"),
        ("Title",                   "UNVERIFIED", "NLA title search required; conversion planning compliance unknown"),
        ("Planning Compliance",     "UNVERIFIED", "Apartment conversion permits to be confirmed"),
        ("Utilities",               "LIKELY OK",  "Established subdivision — confirm all 4 units connected"),
        ("DOM 48",                  "POSITIVE",   "48 days on market provides negotiating leverage"),
    ]

    sc_col = {
        "MISSING": RED_COL, "STRONG": GREEN_COL, "GOOD": HexColor("#5DAD8A"),
        "MEDIUM": AMBER_COL, "MARGINAL": AMBER_COL, "UNKNOWN": RED_COL,
        "UNVERIFIED": AMBER_COL, "LIKELY OK": HexColor("#5DAD8A"), "POSITIVE": GREEN_COL,
    }
    hs = ParagraphStyle("vh", fontName="Helvetica-Bold", fontSize=8,
                        textColor=colors.white, alignment=TA_CENTER, leading=11)
    ns = ParagraphStyle("vn", fontName="Helvetica", fontSize=8.5,
                        textColor=TEXT_DARK, leading=12)
    ss = ParagraphStyle("vs", fontName="Helvetica-Bold", fontSize=8.5,
                        textColor=colors.white, alignment=TA_CENTER, leading=12)
    cw = [52*mm, 28*mm, CW_FULL - 80*mm]
    data = [[Paragraph(h, hs) for h in ["Factor", "Status", "Notes"]]]
    for factor, status, note in rows_v:
        data.append([Paragraph(factor, ns), Paragraph(status, ss), Paragraph(note, ns)])
    st = [
        ("BACKGROUND",    (0,0),(-1,0), GFL_NAVY),
        ("GRID",          (0,0),(-1,-1), 0.3, GFL_BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
    ]
    for i, (_, status, _) in enumerate(rows_v, 1):
        st.append(("BACKGROUND", (1,i),(1,i), sc_col.get(status, HexColor("#DDD"))))
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Issue GREEN once: asking price confirmed and acceptable, title clean, structural survey passed, "
        "apartment conversion planning compliance confirmed. "
        "Issue RED if: title defective without clear resolution path, survey reveals major structural "
        "defects, or asking price exceeds USD $400,000 without strong STR income evidence.",
        STYLES["flag"]
    ))


def s12_checklist(story):
    story += sec_hdr("12. NEXT ACTION CHECKLIST")
    story += labelled_section("Immediate — Today", [
        "Contact agent (MLS# 100907) to obtain asking price — this is the single most urgent action",
        "Request year of build and any available property condition report",
        "Request copies of: title/Volume/Folio, building permits for apartment conversion, any planning approvals",
        "Request existing tenancy agreements and current occupancy status of all 4 units",
        "Request details of Seville subdivision covenants, HOA, and maintenance fees",
    ], RED_COL)
    story += labelled_section("Within 1 Week", [
        "Instruct Jamaican attorney to commence NLA title search",
        "Commission structural survey — year of build unknown, this is non-negotiable",
        "Obtain surveyor's identification report confirming lot boundaries vs title",
        "Obtain 2–3 STR market comparable rates for 1-bed ocean view units near St. Ann's Bay / Ocho Rios corridor",
        "Obtain 2–3 LTL comparable rents for 2-bed and 1-bed units in St. Ann's Bay / Seville",
        "Identify and shortlist 2 local property management companies",
    ], AMBER_COL)
    story += labelled_section("Before Exchange", [
        "Confirm NLA / government land valuation for transfer tax",
        "Confirm all 4 units have live JPS and NWC connections",
        "Confirm St. Ann Parish Council planning approval for 4-unit residential use",
        "Confirm property tax compliance — no arrears",
        "Confirm helper's quarters and garage status — no informal occupants",
        "Brief UK accountant on Jamaica multi-unit rental income and HMRC reporting",
        "Confirm TRN registration and TPDCo licensing process for any STR units",
        "Obtain multi-unit insurance quote: property, hurricane, liability",
        "Assess lot development potential — obtain planning pre-application advice from St. Ann Parish Council",
    ], GFL_NAVY)


def footer(story):
    story.append(HRFlowable(width="100%", thickness=0.5, color=GFL_BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "This report is produced for investment evaluation purposes only and does not constitute legal, tax, "
        "mortgage, planning, or professional surveying advice. All financial projections are estimates based on "
        "assumed and available data and must be independently verified. Instruct a qualified Jamaican attorney, "
        "chartered surveyor, and accountant before proceeding with any transaction.",
        STYLES["disclaimer"]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "GFL AI Deal Analyser  |  GFL PropertyTech  |  Ref: JAM-STA-0609-002  |  9 June 2026",
        STYLES["footer"]
    ))


def build(path):
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=18*mm, bottomMargin=14*mm,
        title="GFL Deal Analysis — 9 Hibiscus Way, Seville",
        author="GFL PropertyTech AI Deal Analyser",
        subject="Jamaica Multi-Family Investment Analysis",
    )
    story = []
    cover(story)
    s1_executive(story)
    s2_overview(story)
    s3_area(story)
    s4_strategy(story)
    s5_financials(story)
    s6_risks(story)
    s7_compliance(story)
    s8_offer(story)
    s9_best_exit(story)
    s10_backup(story)
    s11_verdict(story)
    s12_checklist(story)
    footer(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {path}")


if __name__ == "__main__":
    build("/home/user/GFL-PHONE-AGENT/GFL_Deal_Analysis_9_Hibiscus_Way_Seville.pdf")
