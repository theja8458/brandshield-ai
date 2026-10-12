"""BrandShield AI Detection Engine Configuration.

Contains all weights, caps, thresholds, scam-keyword lists, and generic-word lists.
Deterministic and explainable scoring for both social media and app store monitoring.
"""

from typing import Dict, List, Set

# =====================================================================
# SIGNAL WEIGHTS (MAXIMUM POINTS PER SIGNAL)
# =====================================================================

# Max points for normalized name similarity
MAX_NAME_SIMILARITY: int = 35

# Evasion bonuses (take the LARGEST applicable bonus, do NOT sum)
EVASION_BONUS_HOMOGLYPH_LEETSPEAK: int = 8  # e.g., N0vaPay -> +8
EVASION_BONUS_ADDED_SCAM_WORD: int = 6      # e.g., NovaPay Support -> +6
EVASION_BONUS_SPACING_ONLY: int = 3         # e.g., Nova Pay -> +3

# Independent signal families
MAX_LOOKALIKE_DOMAIN: int = 25       # Link/website domain similar but not equal to official
MAX_PUBLISHER_MISMATCH: int = 20     # Trusted publisher ID differs = 20
PUBLISHER_MISSING_POINTS: int = 8    # Publisher data missing = 8 + missing evidence warning
MAX_SCAM_LANGUAGE: int = 15          # Bio / description keywords (giveaway, refund, DM to claim)
MAX_IMAGE_SIMILARITY: int = 15       # Perceptual hash distance to official logo (ONLY when real image exists)
MAX_DESCRIPTION_SIMILARITY: int = 10 # Token-set similarity vs brand description

# =====================================================================
# ANTI-DOUBLE-COUNTING & CAPS
# =====================================================================

# The name family consists of (name_similarity + largest evasion_bonus).
# It is strictly capped at 40 points.
NAME_FAMILY_CAP: int = 40

# Overall risk score maximum cap
TOTAL_SCORE_CAP: int = 100

# =====================================================================
# SEVERITY THRESHOLDS
# =====================================================================

THRESHOLD_CRITICAL: int = 85  # Score >= 85
THRESHOLD_HIGH: int = 70      # Score 70 - 84
THRESHOLD_MEDIUM: int = 40    # Score 40 - 69
# Low: Score < 40

# Minimum score to classify as POTENTIAL_THREAT
POTENTIAL_THREAT_THRESHOLD: int = 40

# =====================================================================
# NAME SIMILARITY BANDS (Applied to Normalized Compact String)
# =====================================================================

SIMILARITY_BAND_EXACT_COMPACT: int = 35  # Exact compact match, but unregistered
SIMILARITY_BAND_HIGH: int = 30           # Similarity >= 0.90
SIMILARITY_BAND_MEDIUM: int = 20         # Similarity 0.80 - 0.89
SIMILARITY_BAND_LOW_TOKEN: int = 8       # Similarity 0.70 - 0.79 (ONLY if a brand token is contained)
SIMILARITY_BAND_NONE: int = 0            # Similarity < 0.70

# Threshold for domain lookalike detection (RapidFuzz normalized similarity)
DOMAIN_LOOKALIKE_SIMILARITY_THRESHOLD: float = 0.72

# =====================================================================
# CONTROLLED WORD LISTS
# =====================================================================

# Controlled list of generic impersonation prefixes/suffixes used for core-name extraction
GENERIC_IMPERSONATION_WORDS: List[str] = [
    "support",
    "help",
    "official",
    "care",
    "refund",
    "login",
    "rewards",
    "giveaway",
    "agent",
    "security",
    "service",
    "desk",
    "team",
]

# Scam language keywords searched in candidate bios and descriptions
SCAM_LANGUAGE_KEYWORDS: List[str] = [
    "giveaway",
    "dm to claim",
    "dm for help",
    "claim to refund",
    "refund",
    "support agent",
    "recharge",
    "free money",
    "claim rewards",
    "customer care number",
    "whatsapp us",
    "send eth",
    "crypto help",
    "verify wallet",
    "validate seed",
    "urgent action required",
    "account suspended",
]

# =====================================================================
# HOMOGLYPHS & CONFUSABLES MAP
# =====================================================================

HOMOGLYPH_MAP: Dict[str, str] = {
    # Digits to letters (leetspeak)
    "0": "o",
    "1": "l",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "@": "a",
    "$": "s",
    # Cyrillic homoglyphs
    "а": "a",  # U+0430
    "с": "c",  # U+0441
    "е": "e",  # U+0435
    "о": "o",  # U+043E
    "р": "p",  # U+0440
    "х": "x",  # U+0445
    "у": "y",  # U+0443
    "і": "i",  # U+0456
    "ѕ": "s",  # U+0455
    "ј": "j",  # U+0458
    # Greek homoglyphs
    "α": "a",  # U+03B1
    "ο": "o",  # U+03BF
    "ν": "v",  # U+03BD
    "ρ": "p",  # U+03C1
    "τ": "t",  # U+03C4
    "υ": "u",  # U+03C5
    "ι": "i",  # U+03B9
}

# Digraph confusable substitutions
DIGRAPH_MAP: Dict[str, str] = {
    "rn": "m",
    "vv": "w",
    "cl": "d",
}
