#!/usr/bin/env python3
"""ktype.py - type Khojki fast with short ASCII codes.

You look at the scan, you type short codes, the tool writes correct Khojki Unicode.
This is faster than clicking the chart, and the output is always valid.

SYNTAX
  One syllable = one token. Separate tokens with spaces.
  Join parts of one syllable with '+':   ka+aa   ka+i+M   ja+.+u
  ":"   word separator (the colon-like mark between words)
  "|"   danda       "||"  double danda
  0-9   Gujarati digits (Khojki has no digits of its own)
  ?     unsure glyph (kept as U+FFFD so you can find it later)

CONSONANTS (inherent a): ka kha ga gga gha nga ca cha ja jja nya tta ttha dda ddha
  nna ta tha da ddda dha na pa pha ba bba bha ma ya ra la va sa ha lla qa
INDEPENDENT VOWELS: A AA I U E AI O AU SI(short i)
VOWEL SIGNS (after '+'): aa i ii u e ai o au r(vocalic r)
MARKS (after '+'): M anusvara   ~ virama   . nukta   W shadda   sk sukun
OTHER: $ section mark   $$ double section mark   @ abbreviation sign

EXAMPLES
  python ktype.py "ka+aa ra : ma+i+M | 1 2"
  python ktype.py -o data/gt_lines/l01.gt.txt      (interactive: type, Enter)
  python ktype.py --show data/gt_lines/l01.gt.txt  (list code points)
"""
import argparse
import sys
import unicodedata as ud

C = {  # consonants
    "ka": 0x11208, "kha": 0x11209, "ga": 0x1120A, "gga": 0x1120B, "gha": 0x1120C,
    "nga": 0x1120D, "ca": 0x1120E, "cha": 0x1120F, "ja": 0x11210, "jja": 0x11211,
    "nya": 0x11213, "tta": 0x11214, "ttha": 0x11215, "dda": 0x11216, "ddha": 0x11217,
    "nna": 0x11218, "ta": 0x11219, "tha": 0x1121A, "da": 0x1121B, "ddda": 0x1121C,
    "dha": 0x1121D, "na": 0x1121E, "pa": 0x1121F, "pha": 0x11220, "ba": 0x11221,
    "bba": 0x11222, "bha": 0x11223, "ma": 0x11224, "ya": 0x11225, "ra": 0x11226,
    "la": 0x11227, "va": 0x11228, "sa": 0x11229, "ha": 0x1122A, "lla": 0x1122B,
    "qa": 0x1123F,
}
IV = {  # independent vowels
    "A": 0x11200, "AA": 0x11201, "I": 0x11202, "U": 0x11203, "E": 0x11204,
    "AI": 0x11205, "O": 0x11206, "AU": 0x11207, "SI": 0x11240,
}
VS = {  # vowel signs
    "aa": 0x1122C, "i": 0x1122D, "ii": 0x1122E, "u": 0x1122F, "e": 0x11230,
    "ai": 0x11231, "o": 0x11232, "au": 0x11233, "r": 0x11241,
}
MK = {"M": 0x11234, "~": 0x11235, ".": 0x11236, "W": 0x11237, "sk": 0x1123E}
PUNCT = {":": 0x1123A, "|": 0x11238, "||": 0x11239, "$": 0x1123B, "$$": 0x1123C,
         "@": 0x1123D, "?": 0xFFFD}
# Storage order after the base letter: nukta, vowel sign, other marks.
ORDER = {0x11236: 0}


def _rank(cp):
    if cp == 0x11236:
        return 0
    if cp in VS.values():
        return 1
    return 2


def encode_token(tok):
    if tok in PUNCT:
        return chr(PUNCT[tok])
    if tok.isdigit():
        return "".join(chr(0x0AE6 + int(d)) for d in tok)
    parts = tok.split("+")
    base, extras = parts[0], parts[1:]
    if base in C:
        out = [C[base]]
    elif base in IV:
        out = [IV[base]]
        if any(e in VS for e in extras):
            raise ValueError(f"'{tok}': a vowel sign cannot follow an independent vowel")
    else:
        raise ValueError(f"unknown base '{base}' in '{tok}'")
    signs = []
    for e in extras:
        if e in VS:
            signs.append(VS[e])
        elif e in MK:
            signs.append(MK[e])
        else:
            raise ValueError(f"unknown sign '{e}' in '{tok}'")
    if sum(1 for s in signs if s in VS.values()) > 1:
        raise ValueError(f"'{tok}': more than one vowel sign")
    signs.sort(key=_rank)
    return "".join(chr(c) for c in out + signs)


def encode(line):
    s = "".join(encode_token(t) for t in line.split())
    return ud.normalize("NFC", s)


def show(s):
    for ch in s:
        print(f"U+{ord(ch):04X}  {ch}  {ud.name(ch, '?')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("codes", nargs="?", help="codes for one line (omit for interactive mode)")
    ap.add_argument("-o", "--out", help="write the result to this .gt.txt file")
    ap.add_argument("--show", metavar="FILE", help="print the code points in FILE")
    a = ap.parse_args()

    if a.show:
        show(open(a.show, encoding="utf-8").read().strip())
        return
    line = a.codes if a.codes is not None else input("codes> ")
    try:
        s = encode(line)
    except ValueError as e:
        sys.exit(f"error: {e}")
    print(s)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(s + "\n")
        print(f"saved {a.out}  ({len(s)} code points)")


if __name__ == "__main__":
    main()
