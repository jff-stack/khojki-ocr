"""Validate Khojki text against the encoding rules. CLI exits 1 if any file has errors."""
import sys
import unicodedata as ud

from khojki.charset import (ALLOWED, DO_NOT_USE, LETTERS, MARKS, SECTION_MARK,
                            VOWEL_SIGNS, describe, mark_rank)

REPLACEMENT = 0xFFFD


def validate(s: str) -> list[str]:
    """Return a list of human-readable errors; an empty list means the text is valid."""
    errors: list[str] = []
    if ud.normalize("NFC", s) != s:
        errors.append("text is not NFC")

    for i, ch in enumerate(s):
        cp = ord(ch)
        if cp == REPLACEMENT:
            errors.append(f"pos {i}: U+FFFD unsure glyph left in text")
        elif cp not in ALLOWED:
            errors.append(f"pos {i}: illegal code point {describe(cp)}")

    for i, ch in enumerate(s):
        if ord(ch) not in MARKS:
            continue
        j = i - 1
        while j >= 0 and ord(s[j]) in MARKS:
            j -= 1
        if j < 0 or ord(s[j]) not in LETTERS:
            where = "at start" if j < 0 else f"after {describe(ord(s[j]))}"
            errors.append(f"pos {i}: orphan mark {describe(ord(ch))} {where}")

    for bad, good in DO_NOT_USE.items():
        start = s.find(bad)
        while start != -1:
            seq = " ".join(f"U+{ord(c):04X}" for c in bad)
            errors.append(f"pos {start}: decomposed vowel <{seq}>, use {describe(ord(good))}")
            start = s.find(bad, start + 1)

    i = 0
    while i < len(s):
        if ord(s[i]) in LETTERS:
            j = i + 1
            while j < len(s) and ord(s[j]) in MARKS:
                j += 1
            ranks = [mark_rank(ord(c)) for c in s[i + 1:j]]
            if ranks != sorted(ranks):
                errors.append(f"pos {i}: marks out of order (nukta, vowel sign, other)")
            vowels = sum(1 for c in s[i + 1:j] if ord(c) in VOWEL_SIGNS)
            if vowels > 1 and not any(bad in s[i:j] for bad in DO_NOT_USE):
                errors.append(f"pos {i}: {vowels} vowel signs on one letter")
            i = j
        else:
            i += 1

    for i in range(1, len(s) - 1):
        if ord(s[i]) == SECTION_MARK and (ord(s[i - 1]) in LETTERS | MARKS) \
                and ord(s[i + 1]) in LETTERS:
            errors.append(f"pos {i}: U+1123B section mark used as a word separator")
    return errors


def main(paths: list[str]) -> int:
    """Validate each file line by line and print errors; return the exit code."""
    failed = False
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f.read().splitlines(), 1):
                for err in validate(line):
                    print(f"{path}:{n}: {err}")
                    failed = True
    if not failed:
        print(f"ok: {len(paths)} file(s) valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
