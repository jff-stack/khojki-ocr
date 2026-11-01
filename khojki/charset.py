"""Khojki character inventory and encoding rules (Unicode core spec 17.0, section 15.7)."""
import unicodedata as ud

BLOCK = range(0x11200, 0x11242)
UNASSIGNED = {0x11212}

INDEPENDENT_VOWELS = frozenset([*range(0x11200, 0x11208), 0x11240])
CONSONANTS = frozenset([*range(0x11208, 0x1122C), 0x1123F]) - UNASSIGNED
VOWEL_SIGNS = frozenset([*range(0x1122C, 0x11234), 0x11241])

ANUSVARA = 0x11234
VIRAMA = 0x11235
NUKTA = 0x11236
SHADDA = 0x11237
SUKUN = 0x1123E
OTHER_MARKS = frozenset([ANUSVARA, VIRAMA, SHADDA, SUKUN])
MARKS = VOWEL_SIGNS | OTHER_MARKS | {NUKTA}

DANDA = 0x11238
DOUBLE_DANDA = 0x11239
WORD_SEPARATOR = 0x1123A
SECTION_MARK = 0x1123B
DOUBLE_SECTION_MARK = 0x1123C
ABBREVIATION_SIGN = 0x1123D
PUNCTUATION = frozenset([DANDA, DOUBLE_DANDA, WORD_SEPARATOR, SECTION_MARK,
                         DOUBLE_SECTION_MARK, ABBREVIATION_SIGN])

LETTERS = INDEPENDENT_VOWELS | CONSONANTS
GUJARATI_DIGITS = frozenset(range(0x0AE6, 0x0AF0))
SPACE = 0x20

ALLOWED = frozenset(cp for cp in BLOCK if cp not in UNASSIGNED) | GUJARATI_DIGITS | {SPACE}

# Table 15-4: atomic vowels and the decomposed sequences that must not be used.
# Longest sequences first so <A, AA, AI> becomes AU, not <AA, AI>.
DO_NOT_USE: dict[str, str] = {
    "\U00011200\U0001122C\U00011231": "\U00011207",
    "\U00011200\U0001122C": "\U00011201",
    "\U00011240\U0001122E": "\U00011202",
    "\U00011206\U0001122C": "\U00011203",
    "\U00011200\U00011231": "\U00011205",
    "\U00011200\U00011233": "\U00011207",
    "\U0001122C\U00011230": "\U00011232",
    "\U0001122C\U00011231": "\U00011233",
}

DIGIT_MAP: dict[str, str] = {
    **{str(d): chr(0x0AE6 + d) for d in range(10)},
    **{chr(0x0966 + d): chr(0x0AE6 + d) for d in range(10)},
}

NOT_IN_FONT = frozenset([0x11241])


def mark_rank(cp: int) -> int:
    """Storage order after a base letter: nukta, vowel sign, other marks."""
    if cp == NUKTA:
        return 0
    return 1 if cp in VOWEL_SIGNS else 2


def describe(cp: int) -> str:
    """Return 'U+XXXX NAME' for a code point."""
    return f"U+{cp:04X} {ud.name(chr(cp), '<unassigned>')}"
