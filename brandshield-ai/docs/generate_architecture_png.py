"""
Generate high-resolution presentation architecture diagram for BrandShield AI.
Outputs: brandshield-ai/docs/architecture.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

def create_architecture_diagram(output_path: str):
    # Dimensions: 1920x1080 (Full HD presentation slide format)
    width = 1920
    height = 1080
    bg_color = (15, 23, 42)  # Tailwind slate-900
    card_bg = (30, 41, 59)   # Tailwind slate-800
    border_color = (51, 65, 85) # Tailwind slate-700
    text_white = (248, 250, 252)
    text_muted = (148, 163, 184)
    accent_blue = (56, 189, 248)  # Sky-400
    accent_teal = (45, 212, 191)  # Teal-400
    accent_amber = (251, 191, 36) # Amber-400
    accent_red = (248, 113, 113)  # Rose-400
    accent_purple = (192, 132, 252) # Purple-400
    accent_green = (74, 222, 128) # Green-400

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Use default fonts or load system font if available
    try:
        font_title = ImageFont.truetype("arial.ttf", 34)
        font_subtitle = ImageFont.truetype("arial.ttf", 18)
        font_header = ImageFont.truetype("arialbd.ttf", 20)
        font_body = ImageFont.truetype("arial.ttf", 15)
        font_bold = ImageFont.truetype("arialbd.ttf", 15)
        font_small = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font_title = font_subtitle = font_header = font_body = font_bold = font_small = ImageFont.load_default()

    # Draw Title Header
    draw.text((60, 40), "BrandShield AI — System Architecture & Data Flow", fill=text_white, font=font_title)
    draw.text((60, 85), "End-to-End Digital Risk Protection: Ingestion, Pre-Scoring Safety Guard, Detection Engine & Campaign Graph", fill=accent_blue, font=font_subtitle)
    draw.line([(60, 120), (1860, 120)], fill=(71, 85, 105), width=2)

    def draw_card(x, y, w, h, title, title_color, border_col=border_color):
        draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=card_bg, outline=border_col, width=2)
        draw.text((x + 16, y + 14), title, fill=title_color, font=font_header)
        draw.line([(x + 16, y + 42), (x + w - 16, y + 42)], fill=(51, 65, 85), width=1)

    # 1. DATA SOURCES (Left Column)
    draw_card(60, 150, 360, 870, "1. DATA SOURCES & INGESTION", accent_teal)
    sources = [
        ("Apple iTunes Search API", "Live public endpoint: itunes.apple.com\nEntity: software (iOS / iPadOS apps)\nRate limit: ~20 req/min, 8s timeout\nExtracts: bundleId, developer, icon URL", accent_blue),
        ("Bluesky Public XRPC Search", "Live public endpoint: public.api.bsky.app\nXRPC: app.bsky.actor.searchActors\nExtracts: did, handle, displayName, avatar\nRate limit: ~300 req/5m, 8s timeout", accent_blue),
        ("Analyst Manual Submission", "Direct submission via UI modal\nCustom suspicious handles/listing URLs\nTagged: source_type='manual'", text_muted),
        ("Repeatable Synthetic Demo Seed", "NovaPay v1 benchmark dataset\nOffline test cases & ground truth\nTagged: source_type='demo'", accent_amber),
    ]
    sy = 210
    for s_title, s_desc, s_color in sources:
        draw.rounded_rectangle([80, sy, 400, sy + 135], radius=8, fill=(15, 23, 42), outline=(51, 65, 85), width=1)
        draw.text((95, sy + 10), s_title, fill=s_color, font=font_bold)
        lines = s_desc.split("\n")
        ly = sy + 35
        for l in lines:
            draw.text((95, ly), l, fill=text_muted, font=font_small)
            ly += 22
        sy += 155

    # 2. CONNECTORS & PRE-PROCESSING (Middle-Left Column)
    draw_card(460, 150, 360, 420, "2. INGESTION & BOUNDARIES", accent_blue)
    draw.text((480, 210), "Security & Network Boundaries", fill=text_white, font=font_bold)
    boundary_items = [
        "- Fixed Hostname Allowlisting (No arbitrary SSRF)",
        "- Bounded Timeouts (8.0s) & Max 2 retries",
        "- 2 MB Maximum Response Payload Size Cap",
        "- Graceful Degradation (No fake data substitution)",
        "- Unicode NFKC Normalization & Homoglyphs",
        "- Clean Domain & Subdomain Extraction",
    ]
    by = 245
    for item in boundary_items:
        draw.text((480, by), item, fill=text_muted, font=font_body)
        by += 32

    # 3. OFFICIAL-ASSET SAFETY GUARD (Middle-Left Column, Bottom)
    draw_card(460, 600, 360, 420, "3. OFFICIAL-ASSET SAFETY GUARD", accent_green, border_col=accent_green)
    draw.text((480, 655), "CRITICAL GUARANTEE: PRE-SCORING CHECK", fill=accent_green, font=font_bold)
    guard_items = [
        "Checks candidate BEFORE any risk scoring:",
        "- Exact verified Bluesky handle & DID match",
        "- Exact Apple App Store bundle ID match",
        "- Verified Developer / Publisher ID match",
        "- Registered corporate domain safe-list match",
        "",
        "Outcome 1: OFFICIAL_EXCLUDED",
        "  -> Score = 0; Quarantined from alert counts.",
        "Outcome 2: REVIEW_REQUIRED",
        "  -> Conflicting identity triggers analyst audit.",
    ]
    gy = 690
    for item in guard_items:
        col = accent_green if "OFFICIAL_EXCLUDED" in item or "CRITICAL" in item else text_muted
        draw.text((480, gy), item, fill=col, font=font_body)
        gy += 28

    # 4. DETERMINISTIC DETECTION ENGINE (Middle-Right Column)
    draw_card(860, 150, 460, 870, "4. DETERMINISTIC DETECTION ENGINE", accent_purple)
    draw.text((885, 210), "Explainable Multi-Signal Scoring (Max 100)", fill=text_white, font=font_bold)
    engine_families = [
        ("Name Similarity & Evasion (Max 40)", "Levenshtein distance (0-35 pts) + Homoglyph replacement / prefix bonus (+5 pts). Subject to strict Name-Only Ceiling!"),
        ("Look-Alike Domain (Max 25)", "Phishing hostnames in links or bios (25 pts). Exact registered official domains score 0 risk."),
        ("App Publisher Mismatch (Max 20)", "Unverified developer ID publishing official brand name (20 pts). Missing publisher adds 8 pts warning."),
        ("Scam Urgency Language (Max 15)", "Targeted crypto/fintech scam patterns: 'giveaway refund', 'claim bonus', 'verify 2fa'."),
        ("Perceptual Logo Hash (Max 15)", "64-bit perceptual image hashing (pHash) against verified brand logo (Hamming distance < 10)."),
        ("Description Semantic Overlap (Max 10)", "Bio text token containment & unauthorized support impersonation phrases."),
    ]
    ey = 245
    for f_title, f_desc in engine_families:
        draw.rounded_rectangle([880, ey, 1300, ey + 82], radius=6, fill=(15, 23, 42), outline=(51, 65, 85), width=1)
        draw.text((895, ey + 8), f_title, fill=accent_purple, font=font_bold)
        draw.text((895, ey + 32), f_desc[:65], fill=text_muted, font=font_small)
        draw.text((895, ey + 52), f_desc[65:], fill=text_muted, font=font_small)
        ey += 95

    # Severity bands box
    draw.rounded_rectangle([880, 840, 1300, 1000], radius=8, fill=(15, 23, 42), outline=border_color, width=1)
    draw.text((895, 850), "Standard Severity Bands & Actions", fill=text_white, font=font_bold)
    draw.text((895, 880), "• Critical (85 - 100): Immediate takedown escalation", fill=accent_red, font=font_body)
    draw.text((895, 910), "• High (70 - 84): Urgent analyst triage required", fill=accent_amber, font=font_body)
    draw.text((895, 940), "• Medium (40 - 69): Suspicious candidate watchlist", fill=accent_blue, font=font_body)
    draw.text((895, 970), "• Low (< 40): Benign variant / Safe-listed property", fill=accent_green, font=font_body)

    # 5. CAMPAIGN GRAPH & STORAGE & UI (Right Column)
    draw_card(1360, 150, 500, 420, "5. CAMPAIGN GRAPH & CLUSTERING", accent_amber)
    draw.text((1385, 210), "Concrete Shared Indicator Graph", fill=text_white, font=font_bold)
    camp_items = [
        "- Links candidates ONLY on explicit indicators:",
        "  * Identical non-generic external domain",
        "  * Identical publisher / developer ID",
        "  * Identical contact email / phone",
        "  * Exact perceptual logo hash match",
        "- Generic domain filtering (GitHub, Bitly excluded)",
        "- Objective labeling: POTENTIAL_COORDINATION",
        "- Connected clustering derived dynamically from data",
    ]
    cy = 245
    for item in camp_items:
        draw.text((1385, cy), item, fill=text_muted, font=font_body)
        cy += 30

    draw_card(1360, 600, 500, 420, "6. STORAGE & ANALYST UI", accent_blue)
    draw.text((1385, 655), "MongoDB Atlas Persistence", fill=text_white, font=font_bold)
    draw.text((1385, 685), "• brandshield_dev (Active App / Live DRP)", fill=accent_teal, font=font_body)
    draw.text((1385, 715), "• brandshield_test (Strictly Isolated Pytest Suite)", fill=accent_teal, font=font_body)
    draw.text((1385, 745), "• Collections: brands, candidates, investigations, audit", fill=text_muted, font=font_small)

    draw.text((1385, 795), "React + TypeScript Web Interface", fill=text_white, font=font_bold)
    ui_items = [
        "• Real-time Dashboard with source health cards",
        "• Brand Profile manager with official asset registration",
        "• Social & App monitoring with live search & seed",
        "• Interactive Impersonation Campaign Graph view",
        "• Granular Evidence Trail drawer with audit points",
        "• Analyst triage: status transitions & persistent notes",
    ]
    uy = 825
    for item in ui_items:
        draw.text((1385, uy), item, fill=text_muted, font=font_small)
        uy += 26

    # Flow arrows (clean visual indicator arrows)
    draw.polygon([(420, 360), (450, 360), (435, 375)], fill=accent_teal)
    draw.polygon([(420, 810), (450, 810), (435, 825)], fill=accent_green)
    draw.polygon([(820, 600), (850, 600), (835, 615)], fill=accent_purple)
    draw.polygon([(1320, 360), (1350, 360), (1335, 375)], fill=accent_amber)
    draw.polygon([(1320, 810), (1350, 810), (1335, 825)], fill=accent_blue)

    # Save PNG
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Architecture diagram saved successfully to: {output_path}")

if __name__ == "__main__":
    out1 = "d:/BrandShield Ai/brandshield-ai/docs/architecture.png"
    create_architecture_diagram(out1)
