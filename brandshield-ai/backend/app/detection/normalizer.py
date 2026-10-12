import re
import unicodedata
from typing import List, Tuple
from app.detection.config import (
    DIGRAPH_MAP,
    GENERIC_IMPERSONATION_WORDS,
    HOMOGLYPH_MAP,
)


class NormalizedNameResult:
    def __init__(
        self,
        raw_name: str,
        nfkc_casefolded: str,
        homoglyph_mapped: str,
        compact_full: str,
        core_compact: str,
        tokens: List[str],
        has_homoglyph_or_leetspeak: bool,
        has_spacing_change: bool,
        has_added_generic_words: bool,
        detected_generic_words: List[str],
    ):
        self.raw_name = raw_name
        self.nfkc_casefolded = nfkc_casefolded
        self.homoglyph_mapped = homoglyph_mapped
        self.compact_full = compact_full
        self.core_compact = core_compact
        self.tokens = tokens
        self.has_homoglyph_or_leetspeak = has_homoglyph_or_leetspeak
        self.has_spacing_change = has_spacing_change
        self.has_added_generic_words = has_added_generic_words
        self.detected_generic_words = detected_generic_words


def strip_punctuation_and_whitespace(text: str) -> str:
    """Remove all whitespace and non-alphanumeric punctuation."""
    return re.sub(r"[^a-z0-9]", "", text)


def normalize_candidate_name(raw_name: str, brand_name: str = "") -> NormalizedNameResult:
    """
    Normalization pipeline in exact required order:
    1. NFKC normalization
    2. casefold
    3. confusables/leetspeak mapping (including digraphs and homoglyphs)
    4. strip whitespace/punctuation for the compact form.
    
    Also detects:
    - Homoglyph or leetspeak substitutions
    - Controlled generic impersonation prefixes/suffixes
    - Core name extraction for name similarity calculation
    """
    if not raw_name:
        return NormalizedNameResult(
            raw_name="",
            nfkc_casefolded="",
            homoglyph_mapped="",
            compact_full="",
            core_compact="",
            tokens=[],
            has_homoglyph_or_leetspeak=False,
            has_spacing_change=False,
            has_added_generic_words=False,
            detected_generic_words=[],
        )

    # 1. NFKC
    nfkc_text = unicodedata.normalize("NFKC", raw_name)

    # 2. casefold
    cf_text = nfkc_text.casefold()

    # Check initial tokens before confusable mapping
    raw_tokens = [t for t in re.split(r"[\s\-_.\W]+", cf_text) if t]

    # 3. Confusables / leetspeak map
    mapped_text = cf_text

    # Apply digraphs first (e.g., 'rn' -> 'm', 'vv' -> 'w')
    for digraph, replacement in DIGRAPH_MAP.items():
        mapped_text = mapped_text.replace(digraph, replacement)

    # Apply character-by-character homoglyphs
    char_list = []
    has_homoglyph = False
    for ch in mapped_text:
        if ch in HOMOGLYPH_MAP:
            char_list.append(HOMOGLYPH_MAP[ch])
            has_homoglyph = True
        else:
            char_list.append(ch)

    homoglyph_mapped = "".join(char_list)

    # 4. Compact full string (whitespace and punctuation stripped)
    compact_full = strip_punctuation_and_whitespace(homoglyph_mapped)

    # Detect tokens from mapped text
    tokens = [t for t in re.split(r"[\s\-_.\W]+", homoglyph_mapped) if t]

    # Check for generic impersonation words
    detected_generic_words = []
    core_tokens = []
    for token in tokens:
        if token in GENERIC_IMPERSONATION_WORDS:
            detected_generic_words.append(token)
        else:
            core_tokens.append(token)

    has_added_generic_words = len(detected_generic_words) > 0

    # If all tokens were generic words (rare edge case), preserve core tokens
    if not core_tokens and tokens:
        core_tokens = tokens

    # Derive core compact string
    core_compact = "".join(core_tokens)

    # Detect spacing-only evasion:
    # If the compact version of core name matches the brand name compact form,
    # but the raw core tokens had spaces or punctuation (e.g. "Nova Pay" vs "NovaPay")
    brand_compact = strip_punctuation_and_whitespace(
        unicodedata.normalize("NFKC", brand_name).casefold()
    ) if brand_name else ""

    has_spacing_change = False
    if brand_compact and core_compact == brand_compact:
        if len(core_tokens) > 1 or " " in raw_name or "_" in raw_name or "-" in raw_name:
            has_spacing_change = True

    return NormalizedNameResult(
        raw_name=raw_name,
        nfkc_casefolded=cf_text,
        homoglyph_mapped=homoglyph_mapped,
        compact_full=compact_full,
        core_compact=core_compact,
        tokens=tokens,
        has_homoglyph_or_leetspeak=has_homoglyph,
        has_spacing_change=has_spacing_change,
        has_added_generic_words=has_added_generic_words,
        detected_generic_words=detected_generic_words,
    )
