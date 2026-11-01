"""Map raw recognizer output to valid Khojki text and count every repair."""
import re
import unicodedata as ud
from collections import Counter

from khojki.charset import (DANDA, DIGIT_MAP, DO_NOT_USE, DOUBLE_DANDA, LETTERS, MARKS,
                            WORD_SEPARATOR, mark_rank)

SEP = chr(WORD_SEPARATOR)
PUNCT_MAP = {
    "।": chr(DANDA),
    "॥": chr(DOUBLE_DANDA),
    ":": SEP,
}


def _reorder_marks(s: str) -> tuple[str, int]:
    """Sort each run of marks after a letter into nukta, vowel sign, other order."""
    out: list[str] = []
    fixed = 0
    i = 0
    while i < len(s):
        out.append(s[i])
        if ord(s[i]) in LETTERS:
            j = i + 1
            while j < len(s) and ord(s[j]) in MARKS:
                j += 1
            run = list(s[i + 1:j])
            ordered = sorted(run, key=lambda c: mark_rank(ord(c)))
            fixed += ordered != run
            out.extend(ordered)
            i = j
        else:
            i += 1
    return "".join(out), fixed


def normalize(s: str) -> tuple[str, Counter]:
    """Return (normalized text, Counter of repair type -> count)."""
    repairs: Counter = Counter()

    nfc = ud.normalize("NFC", s)
    if nfc != s:
        repairs["nfc"] += 1
    s = nfc

    for bad, good in DO_NOT_USE.items():
        n = s.count(bad)
        if n:
            repairs["decomposed_vowel"] += n
            s = s.replace(bad, good)

    for src, dst in {**DIGIT_MAP, **PUNCT_MAP}.items():
        n = s.count(src)
        if n:
            repairs["digit" if src in DIGIT_MAP else "punctuation"] += n
            s = s.replace(src, dst)

    for name, pattern, repl in [
        ("space_at_separator", f" +(?={SEP})|(?<={SEP}) +", ""),
        ("repeated_separator", f"{SEP}{{2,}}", SEP),
        ("repeated_space", " {2,}", " "),
        ("edge_space", "^ +| +$", ""),
    ]:
        s, n = re.subn(pattern, repl, s)
        if n:
            repairs[name] += n

    s, n = _reorder_marks(s)
    if n:
        repairs["mark_order"] += n
    return s, repairs
