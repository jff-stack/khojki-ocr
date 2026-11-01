# Test lines and ground truth

Five test lines, all from page 18 of the sample PDF (1903 Pir Imam Shah, contents page, metal type).

## Method

I verified every line glyph by glyph against the scan. For each line, `tools/compare.py` draws my transcription in Noto Sans Khojki directly under the scan crop (`*.check.png`). I compare the two images left to right, fix the line with `tools/ktype.py`, and render it again until every glyph matches.

I started from an AI-drafted transcription and corrected it. My check changed 4 of the 5 lines: 12 edits in 119 code points, a 10.1% CER for the draft against the verified text (`tools/draft_cer.py`, `results/gt_draft_check.json`). The draft is kept in `data/gt_draft/` so this number can be reproduced.

## Lines

| id | Confidence | Codes (input for ktype.py) | Unicode | Code points |
|---|---|---|---|---|
| p18_l02 | high | `U pa na+aa+M : pha+i ra sa ta+aa : ta ba : ba+aa ta+aa+M : ba+ii ba : 16` | 𑈃𑈟𑈞𑈬𑈴𑈺𑈠𑈭𑈦𑈩𑈙𑈬𑈺𑈙𑈡𑈺𑈡𑈬𑈙𑈬𑈴𑈺𑈡𑈮𑈡𑈺૧૬ | 28 |
| p18_l03 | high | `AA ga+e : AA da ma : pha+i ra sa ta+aa : sa+aa tha+aa+M : 17` | 𑈁𑈊𑈰𑈺𑈁𑈛𑈤𑈺𑈠𑈭𑈦𑈩𑈙𑈬𑈺𑈩𑈬𑈚𑈬𑈴𑈺૧૭ | 23 |
| p18_l04 | medium | `sa+o : sa ba : ha+u pa : A pa ta+ii : ja+aa ta+aa+M : 18` | 𑈩𑈲𑈺𑈩𑈡𑈺𑈪𑈯𑈟𑈺𑈀𑈟𑈙𑈮𑈺𑈐𑈬𑈙𑈬𑈴𑈺૧૮ | 23 |
| p18_l05 | medium | `va+e ja+u+M ha+ii+M : sa+aa ja+aa : sa+aa+M ha+ii AA+M : tha+ii ya+u ja ta :` | 𑈨𑈰𑈐𑈯𑈴𑈪𑈮𑈴𑈺𑈩𑈬𑈐𑈬𑈺𑈩𑈬𑈴𑈪𑈮𑈁𑈴𑈺𑈚𑈮𑈥𑈯𑈐𑈙𑈺 | 29 |
| p18_l06 | high | `AA pa : na+i ra+M ja na : U pa na+aa+M :` | 𑈁𑈟𑈺𑈞𑈭𑈦𑈴𑈐𑈞𑈺𑈃𑈟𑈞𑈬𑈴𑈺 | 16 |

Total: 119 code points. Full code point lists are in `data/gt_lines/lines.json`.

## Corrections

Each correction was rendered under the scan before I accepted it.

| Line | Draft | Verified | Evidence in the scan |
|---|---|---|---|
| p18_l02 | kha+i | pha+i | closed loop at the bottom left, which only pha has |
| p18_l02 | ba ta | ba+ii | the long tail below the line is the II sign |
| p18_l03 | kha+i | pha+i | same loop as l02 |
| p18_l03 | kha+M | tha+aa+M | three prongs on top (kha has two), plus a vowel bar under the ring |
| p18_l04 | ma+aa+M | ta+aa+M | same bottom-left loop as the ta in l02 and l03 |
| p18_l04 | na+ii | ta+ii | same ta shape with an II sign |
| p18_l05 | pa+e | va+e | closest match in the font |
| p18_l05 | ha+ii | ha+ii+M | missed anusvara |
| p18_l05 | pa ta ya | tha+ii ya+u | three glyphs misread |

The hollow ring above the vowel bar is anusvara (U+11234), not the abbreviation sign (U+1123D). Noto Sans Khojki draws the abbreviation sign on the baseline after the letter, the ring sits where anusvara goes, and these words end in "-āṃ", which needs anusvara.

Page 18 manual line count: 16 (`data/gt_lines/page_counts.json`).

Labelling time: only the first full check was measured. Finding and fixing errors in all 5 lines took about 34 minutes, or about 7 minutes per line (self-reported, not tool-timed; `results/labelling_manual.json`).

## Glyphs still uncertain

1. p18_l05, glyph 1: va+e is the closest match, but not certain.
2. p18_l04, word 4: ta+ii or na+ii.
3. p18_l04, word 4: a small dot after A, ignored. It may be ink noise or an anusvara.

## Encoding rules

1. Word separator → U+1123A, never a space or an ASCII colon.
2. Page numbers → Gujarati digits U+0AE6 to U+0AEF.
3. The wide gap before the page number is not encoded: the line ends with U+1123A, then the digits. The pipeline output follows the same rule.
4. Vowel signs are atomic code points, never decomposed pairs.
5. Order after the base letter: nukta, vowel sign, anusvara.
6. All lines are NFC and use only U+11200 to U+11241 and U+0AE6 to U+0AEF.

## Notes

1. Font coverage: Noto Sans Khojki v2.005 has no glyph for U+11241 (vowel sign vocalic R), so it is kept out of the synthetic training text. U+1123F, U+11240 and the Gujarati digits are covered.
2. In p18_l05, glyph 2 renders as `ja+u+M`, not `ja+M`: the scan has a closed loop below the letter, and only the `ja+u+M` render matches it.
3. No ground truth is given for the 1896 lithograph or the handwritten sample. Most of their glyph shapes do not match the font closely enough to verify this way.

## Tools

- `tools/ktype.py "codes"` converts short codes to Khojki Unicode. Run `--help` for the code table; `sk` is sukun.
- `tools/compare.py CROP.png "codes" OUT.png` draws the scan crop above the codes rendered in Noto Sans Khojki.
