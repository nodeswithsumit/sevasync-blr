"""
generate_mock_docs.py
Generates 3 crisp, realistic Bengaluru civic document PNGs for SevaSync BLR demo.

Output files (created in ./images/):
  sample_sas_tax_receipt.png   — BBMP SAS Property Tax Receipt (e-Khata mismatch case)
  sample_bescom_bill.png       — BESCOM Electricity Bill   (Gruha Jyothi tenant case)
  sample_sakala_ack.png        — Sakala GSC Acknowledgement (SLA breach case)

Each document has intentional, clearly-visible civic flaws that Vision OCR will catch.

Run:
    pip install Pillow
    python generate_mock_docs.py
"""

from __future__ import annotations

import os
import random
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    raise SystemExit(
        "Pillow is required. Install with:  pip install Pillow"
    )

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUT_DIR = Path(__file__).parent / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1240, 1754  # A4 at 150 dpi
MARGIN = 80

# Colour palette — government document aesthetic
WHITE = (255, 255, 255)
OFF_WHITE = (252, 250, 245)
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (80, 80, 80)
BLACK = (10, 10, 10)
NAVY = (12, 32, 100)
DARK_RED = (160, 20, 20)
LIGHT_BLUE = (220, 235, 255)
LIGHT_YELLOW = (255, 252, 220)
LIGHT_GREEN = (220, 255, 230)
BBMP_BLUE = (0, 60, 136)
BESCOM_RED = (175, 25, 25)
SAKALA_GREEN = (0, 100, 50)

# ---------------------------------------------------------------------------
# Font helpers — fall back to default if system fonts unavailable
# ---------------------------------------------------------------------------

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a monospace-style system font; fallback to Pillow default."""
    candidates_bold = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    candidates_regular = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in (candidates_bold if bold else candidates_regular):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _mono(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Monospace font for reference numbers."""
    candidates = [
        "/System/Library/Fonts/Courier.dfont",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return _font(size)


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def new_doc(bg: tuple = OFF_WHITE) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)
    return img, draw


def header_band(draw: ImageDraw.ImageDraw, color: tuple, text_lines: list[str],
                y_top: int = 0, height: int = 130) -> int:
    """Draw a coloured header band and return the y position below it."""
    draw.rectangle([(0, y_top), (W, y_top + height)], fill=color)
    y = y_top + 14
    for i, line in enumerate(text_lines):
        bold = i == 0
        sz = 28 if i == 0 else 18
        f = _font(sz, bold=bold)
        draw.text((W // 2, y), line, font=f, fill=WHITE, anchor="mt")
        y += sz + 8
    return y_top + height


def divider(draw: ImageDraw.ImageDraw, y: int, color: tuple = LIGHT_GRAY, thickness: int = 2) -> int:
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + thickness)], fill=color)
    return y + thickness + 10


def kv_row(draw: ImageDraw.ImageDraw, y: int, key: str, value: str,
           key_color: tuple = DARK_GRAY, val_color: tuple = BLACK,
           val_bold: bool = False, indent: int = 0) -> int:
    """Draw a key: value row and return new y."""
    x = MARGIN + indent
    kf = _font(20)
    vf = _font(20, bold=val_bold)
    draw.text((x, y), key + ":", font=kf, fill=key_color)
    draw.text((x + 340, y), value, font=vf, fill=val_color)
    return y + 32


def section_title(draw: ImageDraw.ImageDraw, y: int, title: str,
                  color: tuple = NAVY) -> int:
    f = _font(22, bold=True)
    draw.text((MARGIN, y), title, font=f, fill=color)
    return y + 30


def warning_box(draw: ImageDraw.ImageDraw, y: int, text: str,
                bg: tuple = (255, 240, 220), border: tuple = DARK_RED) -> int:
    """Draw a warning/notice box, return new y."""
    wrapped = textwrap.fill(text, width=85)
    lines = wrapped.split("\n")
    box_h = len(lines) * 24 + 20
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + box_h)], fill=bg, outline=border, width=2)
    yy = y + 10
    for line in lines:
        draw.text((MARGIN + 12, yy), line, font=_font(18), fill=DARK_RED)
        yy += 24
    return y + box_h + 15


def stamp_circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
                 text: str, color: tuple = NAVY) -> None:
    """Draw a circular official stamp (intentionally slightly blurry)."""
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=color, width=3)
    draw.ellipse([(cx - r + 5, cy - r + 5), (cx + r - 5, cy + r - 5)], outline=color, width=1)
    lines = text.split("\n")
    yy = cy - len(lines) * 11
    for line in lines:
        draw.text((cx, yy), line, font=_font(14), fill=color, anchor="mt")
        yy += 22


def handwritten_correction(draw: ImageDraw.ImageDraw, x: int, y: int,
                            text: str, color: tuple = (180, 0, 0)) -> None:
    """Simulate a handwritten correction — slightly tilted, pen-like."""
    f = _font(19)
    # Draw a strikethrough on some phantom text to simulate correction
    draw.text((x, y), text, font=f, fill=color)
    # Add a slightly wobbly underline to suggest handwriting
    for dx in range(0, len(text) * 10, 3):
        jitter = random.randint(-1, 1)
        draw.point((x + dx, y + 22 + jitter), fill=color)


def add_subtle_noise(img: Image.Image, strength: int = 8) -> Image.Image:
    """Add very subtle paper texture noise."""
    import random as rnd
    pixels = img.load()
    for _ in range(W * H // 20):
        px = rnd.randint(0, W - 1)
        py = rnd.randint(0, H - 1)
        r, g, b = pixels[px, py]
        delta = rnd.randint(-strength, strength)
        pixels[px, py] = (
            max(0, min(255, r + delta)),
            max(0, min(255, g + delta)),
            max(0, min(255, b + delta)),
        )
    return img


# ---------------------------------------------------------------------------
# Document 1 — BBMP SAS Property Tax Receipt (e-Khata mismatch case)
# ---------------------------------------------------------------------------

def generate_sas_tax_receipt() -> None:
    img, draw = new_doc(OFF_WHITE)

    # Header
    y = header_band(draw, BBMP_BLUE, [
        "BRUHAT BENGALURU MAHANAGARA PALIKE (BBMP)",
        "Greater Bengaluru Authority — Revenue Department",
        "SAS Property Tax Receipt & e-Khata Extract  |  2024-25",
    ], height=140)

    # Sub-header strip
    draw.rectangle([(0, y), (W, y + 36)], fill=LIGHT_BLUE)
    draw.text((MARGIN, y + 8), "ARO Office: BTM Layout  |  Zone: Bommanahalli  |  Ward No. 175",
              font=_font(18), fill=NAVY)
    y += 50

    # Reference numbers
    y = section_title(draw, y, "DOCUMENT REFERENCE")
    y = kv_row(draw, y, "Receipt No", "BBMP/BTM/2024-25/0078923", val_bold=True)
    y = kv_row(draw, y, "SAS Property ID (PID)", "SAS-BLR-560048-78923", val_bold=True,
               val_color=BBMP_BLUE)
    y = kv_row(draw, y, "e-Aasthi Property ID", "EAASTHI-BLR-2024-078923")
    y = kv_row(draw, y, "Assessment Year", "2024-2025")
    y = kv_row(draw, y, "Date of Issuance", datetime.now().strftime("%d-%m-%Y"))
    y = divider(draw, y + 5)

    # Property Owner (Document Owner — name on official record)
    y = section_title(draw, y, "REGISTERED PROPERTY OWNER DETAILS")
    y = kv_row(draw, y, "Owner Name (as per Khata)", "RAMESH KUMAR S", val_bold=True,
               val_color=DARK_RED)
    y = kv_row(draw, y, "Father/Spouse Name", "S/o Sri Subbaiah Kumar")
    y = kv_row(draw, y, "Aadhaar (last 4)", "XXXX XXXX 4729")
    y = kv_row(draw, y, "Mobile", "9845XXXXXX")
    y = divider(draw, y + 5)

    # Property Details
    y = section_title(draw, y, "PROPERTY DETAILS")
    y = kv_row(draw, y, "Site Address", "No. 42, 5th Main, 1st Stage, BTM Layout")
    y = kv_row(draw, y, "Locality / Ward", "BTM Layout, Ward No. 175")
    y = kv_row(draw, y, "PIN Code", "560048")
    y = kv_row(draw, y, "BBMP Zone", "Bommanahalli Zone")
    y = kv_row(draw, y, "Built-up Area (Assessed)", "1,320 sq.ft.", val_bold=True, val_color=NAVY)
    y = kv_row(draw, y, "Property Type", "Residential — Independent House")
    y = kv_row(draw, y, "Site Area", "1,800 sq.ft. (30' x 60')")
    y = divider(draw, y + 5)

    # Tax details
    y = section_title(draw, y, "TAX ASSESSMENT SUMMARY  (2024-25)")
    y = kv_row(draw, y, "Annual Value (GAV)", "Rs. 72,000")
    y = kv_row(draw, y, "Property Tax (20% of GAV)", "Rs. 14,400")
    y = kv_row(draw, y, "Penalty / Interest", "Rs. 0")
    y = kv_row(draw, y, "Total Tax Paid", "Rs. 14,400", val_bold=True, val_color=NAVY)
    y = kv_row(draw, y, "Payment Date", "15-06-2024")
    y = kv_row(draw, y, "Payment Mode", "Online — BBMP Citizen Portal")
    y = divider(draw, y + 5)

    # ⚠ INTENTIONAL FLAW 1 — Name mismatch annotation
    y = warning_box(draw, y,
        "⚠ NOTICE: Applicant name on mutation application 'R. Kumar' does NOT match "
        "registered owner name 'Ramesh Kumar S' in BBMP records. "
        "Initial abbreviation detected. Sworn Affidavit required.")
    y += 5

    # ⚠ INTENTIONAL FLAW 2 — Wrong ward claimed stamp
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + 40)], fill=(255, 230, 230), outline=DARK_RED, width=2)
    draw.text((MARGIN + 12, y + 10),
              "⚠ Ward 'Koramangala' claimed on application DOES NOT match PID 560048 → BTM Layout",
              font=_font(18), fill=DARK_RED)
    y += 55

    # ⚠ INTENTIONAL FLAW 3 — Area mismatch
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + 40)], fill=(255, 230, 230), outline=DARK_RED, width=2)
    draw.text((MARGIN + 12, y + 10),
              "⚠ Application built-up area 1,150 sqft ≠ BBMP assessed area 1,320 sqft  [Δ = 12.9%]",
              font=_font(18), fill=DARK_RED)
    y += 60

    # Stamp
    stamp_circle(draw, W - 160, H - 220, 85,
                 "BBMP\nBTM LAYOUT\nARO OFFICE\nAUTHENTICATED", BBMP_BLUE)

    # Footer
    draw.rectangle([(0, H - 70), (W, H)], fill=BBMP_BLUE)
    draw.text((W // 2, H - 45),
              "This is a computer-generated receipt. For queries: bbmpeaasthi.kar.nic.in | Helpline: 080-22221188",
              font=_font(16), fill=WHITE, anchor="mm")

    img = add_subtle_noise(img)
    path = OUT_DIR / "sample_sas_tax_receipt.png"
    img.save(path, "PNG", dpi=(150, 150))
    print(f"  ✓  {path}")


# ---------------------------------------------------------------------------
# Document 2 — BESCOM Electricity Bill (Gruha Jyothi tenant case)
# ---------------------------------------------------------------------------

def generate_bescom_bill() -> None:
    img, draw = new_doc(OFF_WHITE)

    # Header
    y = header_band(draw, BESCOM_RED, [
        "BANGALORE ELECTRICITY SUPPLY COMPANY LIMITED (BESCOM)",
        "Consumer Bill — Domestic Connection  |  HT/LT Division: HSR Layout",
        "Bill Period: October 2024  (Gruha Jyothi Scheme Reference Copy)",
    ], height=140)

    draw.rectangle([(0, y), (W, y + 36)], fill=(255, 220, 220))
    draw.text((MARGIN, y + 8),
              "Sub-Division: HSR Layout  |  Section: Sector 2  |  Division: South-East Bengaluru",
              font=_font(18), fill=BESCOM_RED)
    y += 50

    # Consumer details
    y = section_title(draw, y, "CONSUMER ACCOUNT DETAILS")
    y = kv_row(draw, y, "Consumer Name (Account)", "PRIYA SURESH", val_bold=True, val_color=BESCOM_RED)
    y = kv_row(draw, y, "RR Number (Account No.)", "KA2BLR0056ABC", val_bold=True, val_color=DARK_RED)
    # Handwritten correction note
    handwritten_correction(draw, MARGIN + 340, y - 2,
                           "← Alpha-numeric! Convert to 10-digit numeric", (180, 0, 0))
    y += 10
    y = kv_row(draw, y, "Consumer No.", "14205800067")
    y = kv_row(draw, y, "Meter No.", "MET-HSR-2056789")
    y = kv_row(draw, y, "Connection Type", "Domestic LT 1-Phase")
    y = kv_row(draw, y, "Supply Address", "Flat 302, Prestige Sunrise, 7th Cross, Sector 2, HSR Layout")
    y = kv_row(draw, y, "PIN Code", "560047")
    y = divider(draw, y + 5)

    # Billing details
    y = section_title(draw, y, "BILLING DETAILS — OCTOBER 2024")
    y = kv_row(draw, y, "Previous Reading (Sep)", "12,450 kWh")
    y = kv_row(draw, y, "Present Reading (Oct)", "12,703 kWh")
    y = kv_row(draw, y, "Units Consumed", "253 kWh", val_bold=True, val_color=DARK_RED)
    y = kv_row(draw, y, "Billing Days", "31 days")
    y = kv_row(draw, y, "Tariff Slab", "Slab 1: 0–100 units @ Rs. 3.65/unit")
    y = kv_row(draw, y, "", "Slab 2: 101–200 units @ Rs. 5.50/unit")
    y = kv_row(draw, y, "", "Slab 3: 201–300 units @ Rs. 6.95/unit")
    y = kv_row(draw, y, "Energy Charges", "Rs. 1,476.85")
    y = kv_row(draw, y, "Fixed Charges", "Rs. 50.00")
    y = kv_row(draw, y, "Electricity Tax (6%)", "Rs. 91.61")
    y = kv_row(draw, y, "TOTAL AMOUNT DUE", "Rs. 1,618.46", val_bold=True, val_color=NAVY)
    y = kv_row(draw, y, "Due Date", "20-Nov-2024")
    y = divider(draw, y + 5)

    # Gruha Jyothi status
    y = section_title(draw, y, "GRUHA JYOTHI SCHEME STATUS", color=SAKALA_GREEN)
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + 36)],
                   fill=(255, 230, 220), outline=DARK_RED, width=2)
    draw.text((MARGIN + 12, y + 8),
              "INELIGIBLE THIS CYCLE — Consumption 253 units exceeds 200-unit ceiling",
              font=_font(19, bold=True), fill=DARK_RED)
    y += 50

    # ⚠ FLAW 1
    y = warning_box(draw, y,
        "⚠ GRUHA JYOTHI ALERT: Consumption of 253 units in October 2024 exceeds the scheme "
        "ceiling of 200 units. Subsidy NOT applicable for this billing cycle. "
        "Scheme G.O. DE 48 EEB 2023, Clause 4(ii).")
    # ⚠ FLAW 2
    y = warning_box(draw, y,
        "⚠ ACCOUNT NUMBER ALERT: RR Number 'KA2BLR0056ABC' is an alpha-numeric legacy format. "
        "Gruha Jyothi DBT linkage requires 10-digit numeric account number. "
        "Visit BESCOM subdivision office for conversion.")
    # ⚠ FLAW 3
    y = warning_box(draw, y,
        "⚠ TENANT APPLICATION: Applicant 'Suresh Babu' differs from account holder 'Priya Suresh'. "
        "Tenant applications require Registered Rental Agreement + Owner Consent Letter.")

    # Stamp
    stamp_circle(draw, W - 160, H - 200, 85,
                 "BESCOM\nHSR LAYOUT\nSUB-DIVISION\nAUTHORISED", BESCOM_RED)

    # Footer
    draw.rectangle([(0, H - 70), (W, H)], fill=BESCOM_RED)
    draw.text((W // 2, H - 45),
              "BESCOM Helpline: 1912  |  bescom.karnataka.gov.in  |  SMS 'BESCOM <Consumer No.>' to 58888",
              font=_font(16), fill=WHITE, anchor="mm")

    img = add_subtle_noise(img)
    path = OUT_DIR / "sample_bescom_bill.png"
    img.save(path, "PNG", dpi=(150, 150))
    print(f"  ✓  {path}")


# ---------------------------------------------------------------------------
# Document 3 — Sakala GSC Acknowledgement (SLA breach case)
# ---------------------------------------------------------------------------

def generate_sakala_ack() -> None:
    img, draw = new_doc(OFF_WHITE)

    # Header
    y = header_band(draw, SAKALA_GREEN, [
        "GOVERNMENT OF KARNATAKA — SAKALA SERVICES GUARANTEE",
        "Department of Personnel & Administrative Reforms (DPAR)",
        "Service Request Acknowledgement — GSC Tracking Receipt",
    ], height=140)

    draw.rectangle([(0, y), (W, y + 36)], fill=LIGHT_GREEN)
    draw.text((MARGIN, y + 8),
              "Karnataka Sakala Services Act 2011 (Amended Oct 2026)  |  DPAR 56 SAK 2026",
              font=_font(18), fill=SAKALA_GREEN)
    y += 50

    # GSC Reference
    y = section_title(draw, y, "SAKALA SERVICE REQUEST DETAILS")
    y = kv_row(draw, y, "GSC Tracking ID", "GSC2026BLR001234", val_bold=True, val_color=SAKALA_GREEN)
    y = kv_row(draw, y, "Application Date", "01-04-2026", val_bold=True)
    y = kv_row(draw, y, "Service Name", "BBMP e-Khata Transfer / Mutation")
    y = kv_row(draw, y, "Department", "BBMP Revenue — Mahadevapura Zone")
    y = kv_row(draw, y, "ARO Office", "ARO Mahadevapura — Whitefield")
    y = kv_row(draw, y, "Prescribed SLA", "15 Working Days (under Sakala Act Schedule-I)")
    y = kv_row(draw, y, "SLA Deadline", "22-04-2026", val_bold=True, val_color=DARK_RED)
    y = divider(draw, y + 5)

    # Applicant details
    y = section_title(draw, y, "APPLICANT DETAILS")
    y = kv_row(draw, y, "Applicant Name", "KAVITHA REDDY", val_bold=True)
    y = kv_row(draw, y, "Aadhaar (last 4)", "XXXX XXXX 8812")
    y = kv_row(draw, y, "Mobile", "9731XXXXXX")
    y = kv_row(draw, y, "Address", "No. 18, 3rd Floor, Rainbow Apt, ITPL Main Road")
    y = kv_row(draw, y, "PIN Code / Ward", "560066  /  Whitefield")
    y = divider(draw, y + 5)

    # Status section — OVERDUE
    y = section_title(draw, y, "CURRENT STATUS — SLA BREACH ALERT", color=DARK_RED)
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + 55)],
                   fill=(255, 220, 220), outline=DARK_RED, width=3)
    draw.text((MARGIN + 12, y + 8),
              "STATUS: OVERDUE — SLA BREACH DETECTED",
              font=_font(24, bold=True), fill=DARK_RED)
    sla_deadline = datetime(2026, 4, 1) + timedelta(days=15)
    days_overdue = (datetime.now() - sla_deadline).days
    days_overdue = max(days_overdue, 45)  # floor for demo
    draw.text((MARGIN + 12, y + 36),
              f"Days Elapsed: {days_overdue}+ working days  |  SLA: 15 days  |  Overdue by: {days_overdue - 15}+ days",
              font=_font(18), fill=DARK_RED)
    y += 70

    # Appeal ladder
    y = section_title(draw, y, "ESCALATION / APPEAL LADDER (Sakala Act, Oct 2026)")
    appeal_steps = [
        ("Step 1 — First Appellate Authority (FAA)",
         "ARO Mahadevapura — Whitefield  |  File online: sakala.kar.nic.in  |  SLA: 7 days",
         SAKALA_GREEN),
        ("Step 2 — Second Appellate Authority (SAA)",
         "Joint Commissioner BBMP (Revenue)  |  File if FAA fails in 7 days  |  SLA: 14 days",
         NAVY),
        ("Step 3 — Competent Authority (CA)",
         "Deputy Commissioner, Bengaluru Urban  |  Compensation: Rs. 500/day penalty  |  SLA: 30 days",
         DARK_GRAY),
    ]
    for step_title, step_body, step_color in appeal_steps:
        draw.rectangle([(MARGIN, y), (W - MARGIN, y + 60)],
                       fill=WHITE, outline=step_color, width=2)
        draw.text((MARGIN + 12, y + 8), step_title, font=_font(19, bold=True), fill=step_color)
        draw.text((MARGIN + 12, y + 32), step_body, font=_font(17), fill=DARK_GRAY)
        y += 70

    y += 10
    # Penalty notice box
    y = warning_box(draw, y,
        "PENALTY NOTICE (Oct 2026 Amendment): If the department fails to dispose the application "
        "after FAA escalation, Rs. 500 per day of delay will be deducted from the defaulting "
        "officer's salary and paid as compensation to the citizen. Cite G.O. DPAR 56 SAK 2026.",
        bg=LIGHT_YELLOW, border=NAVY)

    # Handwritten "ESCALATE" annotation
    handwritten_correction(draw, MARGIN, y + 5, "→ FILE FAA APPEAL IMMEDIATELY", (160, 0, 0))
    y += 40

    # Stamp
    stamp_circle(draw, W - 160, H - 200, 85,
                 "SAKALA\nDPAR\nKARNATAKA\nAUTHENTICATED", SAKALA_GREEN)

    # Footer
    draw.rectangle([(0, H - 70), (W, H)], fill=SAKALA_GREEN)
    draw.text((W // 2, H - 45),
              "Sakala Helpline: 1902  |  sakala.kar.nic.in  |  SMS: SAKALA <GSC_ID> STATUS to 51969",
              font=_font(16), fill=WHITE, anchor="mm")

    img = add_subtle_noise(img)
    path = OUT_DIR / "sample_sakala_ack.png"
    img.save(path, "PNG", dpi=(150, 150))
    print(f"  ✓  {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("SevaSync BLR — Generating mock civic document PNGs...")
    print(f"Output directory: {OUT_DIR.resolve()}")
    print()

    generate_sas_tax_receipt()
    generate_bescom_bill()
    generate_sakala_ack()

    print()
    print("Done. 3 PNG files generated successfully.")
    print("Upload these via the Vision OCR drop-zone in the SevaSync BLR UI for demo.")
