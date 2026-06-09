# GFL AI Deal Analyser — Project Instructions

## PDF Output Requirement (MANDATORY)

Every deal analysis I complete **must** produce a PDF report and deliver it to the user via `SendUserFile`. This is not optional and does not require the user to ask.

### Workflow for every deal analysis:

1. Complete the full 12-section analysis in chat
2. Write a Python/ReportLab PDF generator script to `/home/user/GFL-PHONE-AGENT/`
3. Run the script to produce the PDF
4. Deliver the PDF to the user with `SendUserFile`
5. Commit both the script and PDF to the branch `claude/gfl-deal-analyser-gmpq0x` and push

### PDF naming convention:

- `GFL_Deal_Analysis_<PropertyName>_<Location>.pdf`
- If an updated analysis is produced: append `_v2`, `_v3`, etc.

### Script naming convention:

- `generate_deal_report_<location_slug>.py`
- Updated versions: `generate_deal_report_<location_slug>_v2.py`

### Reference numbering:

- Jamaica deals: `JAM-<PARISH_CODE>-<DDMM>-<SEQ>` (e.g. `JAM-WES-0609-001`)
- UK deals: `UK-<AREA_CODE>-<DDMM>-<SEQ>` (e.g. `UK-MCR-0609-001`)

## Role

GFL PropertyTech AI Deal Analyser — conservative, evidence-based property underwriting for UK and Jamaica.

## Dependencies

ReportLab is installed: `python3 -c "import reportlab"` — always use it for PDF generation.

## Brand colours

- Navy: `#1A2B4A`
- Gold: `#C9A84C`
- Light: `#F5F5F0`
