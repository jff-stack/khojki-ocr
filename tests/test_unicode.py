import json
import unicodedata as ud
from pathlib import Path

import pytest

import ktype
from khojki.charset import (ALLOWED, BLOCK, DO_NOT_USE, GUJARATI_DIGITS, MARKS,
                            UNASSIGNED)
from khojki.normalize import normalize
from khojki.validate import validate

GT_DIR = Path(__file__).resolve().parents[1] / "data" / "gt_lines"
GT_FILES = sorted(GT_DIR.glob("*.gt.txt"))
KA = "\U00011208"
SEP = "\U0001123A"


def names(s: str) -> list[str]:
    return [ud.name(c) for c in s]


def test_unicode_database_knows_khojki_extensions():
    assert ud.name("\U0001123F") == "KHOJKI LETTER QA"
    assert ud.name("\U00011240") == "KHOJKI LETTER SHORT I"
    assert ud.name("\U00011241") == "KHOJKI VOWEL SIGN VOCALIC R"


def test_expected_names():
    expected = {
        0x11201: "KHOJKI LETTER AA",
        0x1122C: "KHOJKI VOWEL SIGN AA",
        0x11232: "KHOJKI VOWEL SIGN O",
        0x11233: "KHOJKI VOWEL SIGN AU",
        0x11234: "KHOJKI SIGN ANUSVARA",
        0x11235: "KHOJKI SIGN VIRAMA",
        0x11236: "KHOJKI SIGN NUKTA",
        0x11237: "KHOJKI SIGN SHADDA",
        0x11238: "KHOJKI DANDA",
        0x11239: "KHOJKI DOUBLE DANDA",
        0x1123A: "KHOJKI WORD SEPARATOR",
        0x1123B: "KHOJKI SECTION MARK",
        0x1123C: "KHOJKI DOUBLE SECTION MARK",
        0x1123D: "KHOJKI ABBREVIATION SIGN",
        0x1123E: "KHOJKI SIGN SUKUN",
        0x0AE6: "GUJARATI DIGIT ZERO",
    }
    for cp, name in expected.items():
        assert ud.name(chr(cp)) == name


def test_unassigned_and_allowed():
    assert ud.name(chr(0x11212), None) is None
    assert UNASSIGNED == {cp for cp in BLOCK if ud.name(chr(cp), None) is None}
    assert 0x11212 not in ALLOWED
    assert GUJARATI_DIGITS <= ALLOWED


def test_marks_match_unicode_categories():
    combining = {cp for cp in BLOCK if ud.category(chr(cp)) in ("Mn", "Mc")}
    assert MARKS == combining


@pytest.mark.parametrize("path", GT_FILES, ids=lambda p: p.name)
def test_ground_truth_is_valid(path):
    text = path.read_text(encoding="utf-8").strip()
    assert validate(text) == []
    assert normalize(text) == (text, {})


def test_ktype_reproduces_ground_truth():
    lines = json.loads((GT_DIR / "lines.json").read_text(encoding="utf-8"))
    for line in lines:
        gt = (GT_DIR / f"{line['id']}.gt.txt").read_text(encoding="utf-8").strip()
        assert ktype.encode(line["codes"]) == gt


def test_ktype_vowel_sign_o_is_not_sukun():
    assert names(ktype.encode("ka+o")) == ["KHOJKI LETTER KA", "KHOJKI VOWEL SIGN O"]
    assert names(ktype.encode("ka+sk")) == ["KHOJKI LETTER KA", "KHOJKI SIGN SUKUN"]


def test_ktype_orders_marks():
    assert ktype.encode("ja+M+u+.") == "\U00011210\U00011236\U0001122F\U00011234"


@pytest.mark.parametrize("bad,good", DO_NOT_USE.items(),
                         ids=lambda s: "-".join(f"{ord(c):X}" for c in s))
def test_decomposed_vowels_are_rejected_and_repaired(bad, good):
    text = (KA + bad) if ord(bad[0]) in MARKS else bad
    assert any("decomposed" in e for e in validate(text))
    fixed, repairs = normalize(text)
    assert good in fixed and bad not in fixed
    assert repairs["decomposed_vowel"] >= 1
    assert validate(fixed) == []


def test_validator_flags_bad_input():
    assert any("orphan" in e for e in validate("\U0001122C" + KA))
    assert any("orphan" in e for e in validate(KA + SEP + "\U00011234"))
    assert any("illegal" in e for e in validate(KA + "a"))
    assert any("U+FFFD" in e for e in validate(KA + "�"))
    assert any("section mark" in e for e in validate(KA + "\U0001123B" + KA))
    assert any("NFC" in e for e in validate("é"))
    assert any("order" in e for e in validate(KA + "\U00011234\U0001122C"))


def test_normalize_maps_digits_punctuation_and_spacing():
    raw = KA + " : " + KA + "::" + KA + "।" + "1" + "१"
    fixed, repairs = normalize(raw)
    assert fixed == KA + SEP + KA + SEP + KA + "\U00011238" + "૧૧"
    assert repairs["digit"] == 2
    assert repairs["punctuation"] == 4
    assert repairs["repeated_separator"] == 1
    assert validate(fixed) == []


def test_normalize_reorders_marks():
    fixed, repairs = normalize(KA + "\U00011234\U0001122F\U00011236")
    assert fixed == KA + "\U00011236\U0001122F\U00011234"
    assert repairs["mark_order"] == 1
