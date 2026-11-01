"""Build the synthetic training corpus: data/corpus/corpus.txt (source<TAB>text per line)."""
import argparse
import json
import random
import re
import time
import unicodedata as ud
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from khojki import log_experiment
from khojki.charset import (ABBREVIATION_SIGN, ANUSVARA,CONSONANTS, DANDA, DOUBLE_DANDA, GUJARATI_DIGITS,
                            INDEPENDENT_VOWELS, NOT_IN_FONT, NUKTA, SECTION_MARK, SHADDA,
                            SUKUN, VIRAMA, VOWEL_SIGNS, WORD_SEPARATOR, DOUBLE_SECTION_MARK)
from khojki.normalize import normalize
from khojki.render import has_dotted_circle
from khojki.validate import validate

SOURCE = Path("data/corpus/gujarati_source.txt")
CORPUS = Path("data/corpus/corpus.txt")
GT_DIR = Path("data/gt_lines")
WIKISOURCE = "https://gu.wikisource.org/w/api.php"
CATEGORY = "શ્રેણી:નરસિંહ મહેતા"

SEP = chr(WORD_SEPARATOR)
CONS = sorted(chr(c) for c in CONSONANTS)
SIGNS = sorted(chr(c) for c in VOWEL_SIGNS - NOT_IN_FONT)
IVOWELS = sorted(chr(c) for c in INDEPENDENT_VOWELS)
DIGITS = sorted(chr(c) for c in GUJARATI_DIGITS)


def _api(**params) -> dict:
    params["format"] = "json"
    req = urllib.request.Request(f"{WIKISOURCE}?{urllib.parse.urlencode(params)}",
                                 headers={"User-Agent": "khojki-ocr/1.0 (research exercise)"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("unreachable")


def fetch_gujarati(out: Path = SOURCE) -> None:
    """Download Narsinh Mehta poems (15th c., public domain) from Gujarati Wikisource."""
    lines = [f"# Narsinh Mehta (c. 1414-1481), {WIKISOURCE.split('/w/')[0]}, {CATEGORY}"]
    cont: dict = {}
    while True:
        r = _api(action="query", generator="categorymembers", gcmtitle=CATEGORY,
                 gcmnamespace=0, gcmlimit=50, prop="revisions", rvprop="content",
                 rvslots="main", **cont)
        for page in sorted(r["query"]["pages"].values(), key=lambda p: p["title"]):
            if "revisions" not in page:
                continue
            text = page["revisions"][0]["slots"]["main"]["*"]
            lines.append(f"## {page['title']}")
            lines += [ln for ln in (_clean_wikitext(t) for t in text.splitlines()) if ln]
        if "continue" not in r:
            break
        cont = r["continue"]
        time.sleep(2)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clean_wikitext(line: str) -> str:
    """Strip templates, links and markup; keep lines that are mostly Gujarati letters."""
    line = re.sub(r"\{\{[^}]*\}\}|<[^>]+>|\[\[[^|\]]*\||\]\]|\[\[|'''?|^[*#:;=]+|=+$", "", line)
    line = re.sub(r"[^઀-૿ ]", " ", line)
    line = re.sub(r"\s+", " ", line).strip()
    letters = sum(1 for c in line if "અ" <= c <= "હ")
    return line if letters >= 6 else ""


def gujarati_lines(n: int, rng: random.Random) -> tuple[list[str], Counter, Counter]:
    """Convert Gujarati source lines to Khojki; return lines, repair counts, rejection reasons."""
    from aksharamukha import transliterate

    src = [ln for ln in SOURCE.read_text(encoding="utf-8").splitlines() if ln and ln[0] != "#"]
    src = list(dict.fromkeys(src))
    rng.shuffle(src)
    out, repairs, rejected = [], Counter(), Counter()
    for line in src:
        if len(out) >= n:
            break
        khojki = transliterate.process("Gujarati", "Khojki", line)
        khojki = khojki.replace(" ", SEP)
        fixed, rep = normalize(khojki)
        repairs.update(rep)
        errors = validate(fixed)
        if errors:
            rejected[errors[0].split(":", 1)[1].split("U+")[0].strip()] += 1
            continue
        if any(ord(c) in NOT_IN_FONT for c in fixed):
            rejected["contains U+11241 (not in font)"] += 1
            continue
        out.append(fixed)
    return out, repairs, rejected


def _syllable(rng: random.Random, base: str | None = None, sign: str | None = None) -> str:
    """One random akshara: letter + optional nukta, vowel sign, mark."""
    if base is None:
        base = rng.choice(IVOWELS) if rng.random() < 0.12 else rng.choice(CONS)
    s = base
    is_cons = ord(base) in CONSONANTS
    if is_cons and rng.random() < 0.04:
        s += chr(NUKTA)
    if sign is None and is_cons and rng.random() < 0.55:
        sign = rng.choice(SIGNS)
    if sign:
        s += sign
    r = rng.random()
    if r < 0.12:
        s += chr(ANUSVARA)
    elif r < 0.15 and is_cons and not sign:
        s += chr(VIRAMA)
    elif r < 0.17 and is_cons and not sign:
        s += chr(SHADDA)
    elif r < 0.18 and is_cons and not sign:
        s += chr(SUKUN)
    return s


def generated_lines(per_cell: int, rng: random.Random) -> list[str]:
    """Lines where every consonant x vowel-sign pair appears at least per_cell times."""
    cells = [c + v for c in CONS for v in SIGNS] * per_cell
    rng.shuffle(cells)
    syllables = []
    for cell in cells:
        syllables.append(_syllable(rng, base=cell[0], sign=cell[1]))
        for _ in range(rng.randint(0, 2)):
            syllables.append(_syllable(rng))
    lines, i = [], 0
    while i < len(syllables):
        words = []
        for _ in range(rng.randint(2, 6)):
            k = rng.randint(1, 4)
            words.append("".join(syllables[i:i + k]))
            i += k
        lines.append(SEP.join(w for w in words if w))
    return lines


def _number(rng: random.Random) -> str:
    return "".join(rng.choice(DIGITS) for _ in range(rng.randint(1, 3)))


def punctuation_lines(n: int, words: list[str], rng: random.Random) -> list[str]:
    """Lines with separators, dandas, section marks, verse numbers and contents entries."""
    out = []
    for _ in range(n):
        ws = rng.sample(words, rng.randint(2, 5))
        kind = rng.random()
        if kind < 0.4:
            line = SEP.join(ws) + SEP + _number(rng)
        elif kind < 0.6:
            line = SEP.join(ws) + chr(DOUBLE_DANDA) + SEP + _number(rng) + SEP + chr(DOUBLE_DANDA)
        elif kind < 0.75:
            line = SEP.join(ws) + rng.choice([chr(DANDA), chr(DOUBLE_DANDA)])
        elif kind < 0.82:
            line = SEP.join(ws) + SEP + chr(SECTION_MARK)
        elif kind < 0.9:
            line = SEP.join(ws[:-1]) + SEP + ws[-1] + chr(ABBREVIATION_SIGN)
        else:
            line = chr(DOUBLE_SECTION_MARK) + SEP.join(ws) + SEP + _number(rng) + SEP
        out.append(line)
    return out


def check_leakage(lines: list[str], gt_dir: Path = GT_DIR) -> None:
    """Fail if any corpus line equals or contains a whole ground-truth line."""
    gts = [p.read_text(encoding="utf-8").strip() for p in sorted(gt_dir.glob("*.gt.txt"))]
    for line in lines:
        for gt in gts:
            if gt and gt in line:
                raise SystemExit(f"LEAKAGE: corpus line contains ground truth line:\n{line}")


def coverage(lines: list[str]) -> dict:
    """Share of renderable allowed code points that appear in the corpus."""
    seen = {ord(c) for ln in lines for c in ln}
    target = {cp for cp in range(0x11200, 0x11242) if ud.name(chr(cp), "")} - NOT_IN_FONT
    target |= GUJARATI_DIGITS
    return {"covered": len(seen & target), "target": len(target),
            "missing": [f"U+{cp:04X}" for cp in sorted(target - seen)]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gujarati", type=int, default=300)
    ap.add_argument("--per-cell", type=int, default=20)
    ap.add_argument("--punct", type=int, default=600)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--fetch", action="store_true", help="re-download the Gujarati source")
    a = ap.parse_args()

    start = time.time()
    rng = random.Random(a.seed)
    if a.fetch or not SOURCE.exists():
        fetch_gujarati()

    guj, repairs, rejected = gujarati_lines(a.gujarati, rng)
    gen = generated_lines(a.per_cell, rng)
    vocab = [w for ln in guj + gen for w in ln.split(SEP) if 2 <= len(w) <= 10]
    punct = punctuation_lines(a.punct, vocab, rng)

    tagged = [("gujarati", s) for s in guj] + [("generated", s) for s in gen] \
        + [("punctuation", s) for s in punct]
    for _, s in tagged:
        errors = validate(s)
        if errors:
            raise SystemExit(f"invalid corpus line {s!r}: {errors}")
    shaped = [(src, s) for src, s in tagged if not has_dotted_circle(s)]
    dropped = Counter(src for src, _ in tagged) - Counter(src for src, _ in shaped)
    tagged = shaped
    check_leakage([s for _, s in tagged])

    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    CORPUS.write_text("".join(f"{src}\t{s}\n" for src, s in tagged), encoding="utf-8")

    cov = coverage([s for _, s in tagged])
    stats = {
        "lines": dict(Counter(src for src, _ in tagged)),
        "total": len(tagged),
        "coverage_pct": round(100 * cov["covered"] / cov["target"], 1),
        "coverage": cov,
        "gujarati_repairs": dict(repairs),
        "gujarati_rejected": dict(rejected),
        "dropped_dotted_circle": dict(dropped),
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/corpus_stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False),
                                                 encoding="utf-8")
    log_experiment("corpus", f"guj={a.gujarati} per_cell={a.per_cell} punct={a.punct} seed={a.seed}",
                   "codepoint_coverage_pct", stats["coverage_pct"], (time.time() - start) / 60)
    print(json.dumps(stats, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
