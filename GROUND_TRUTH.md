# Test lines and ground truth

5 test lines. All 5 lines are from page 18 of the sample PDF (1903 Pir Imam Shah, contents page, metal type).

## How these transcriptions were made

1. An AI assistant (Claude) made the first draft of each line. It matched each glyph in the scan to the Unicode chart.
2. Each draft was drawn in Noto Sans Khojki under the scan crop (`*.check.png`). Each glyph was compared by eye, and the draft was corrected.
3. A person checked each line against the scan: open the `*.check.png` file, compare the shapes from left to right, fix the line with `tools/ktype.py`, then run `tools/compare.py` again.

The AI drafted the ground truth and a person checked it. The retro states this.

## Lines

| id | Confidence | Codes (input for ktype.py) | Unicode | Code points |
|---|---|---|---|---|
These are the human-checked lines. The AI drafts are kept in `data/gt_draft/` for comparison.

| id | Confidence | Codes (input for ktype.py) | Unicode | Code points |
|---|---|---|---|---|
| p18_l02 | high | `U pa na+aa+M : pha+i ra sa ta+aa : ta ba : ba+aa ta+aa+M : ba+ii ba : 16` | 𑈃𑈟𑈞𑈬𑈴𑈺𑈠𑈭𑈦𑈩𑈙𑈬𑈺𑈙𑈡𑈺𑈡𑈬𑈙𑈬𑈴𑈺𑈡𑈮𑈡𑈺૧૬ | 28 |
| p18_l03 | high | `AA ga+e : AA da ma : pha+i ra sa ta+aa : sa+aa tha+aa+M : 17` | 𑈁𑈊𑈰𑈺𑈁𑈛𑈤𑈺𑈠𑈭𑈦𑈩𑈙𑈬𑈺𑈩𑈬𑈚𑈬𑈴𑈺૧૭ | 23 |
| p18_l04 | medium | `sa+o : sa ba : ha+u pa : A pa ta+ii : ja+aa ta+aa+M : 18` | 𑈩𑈲𑈺𑈩𑈡𑈺𑈪𑈯𑈟𑈺𑈀𑈟𑈙𑈮𑈺𑈐𑈬𑈙𑈬𑈴𑈺૧૮ | 23 |
| p18_l05 | medium | `va+e ja+u+M ha+ii+M : sa+aa ja+aa : sa+aa+M ha+ii AA+M : tha+ii ya+u ja ta :` | 𑈨𑈰𑈐𑈯𑈴𑈪𑈮𑈴𑈺𑈩𑈬𑈐𑈬𑈺𑈩𑈬𑈴𑈪𑈮𑈁𑈴𑈺𑈚𑈮𑈥𑈯𑈐𑈙𑈺 | 29 |
| p18_l06 | high | `AA pa : na+i ra+M ja na : U pa na+aa+M :` | 𑈁𑈟𑈺𑈞𑈭𑈦𑈴𑈐𑈞𑈺𑈃𑈟𑈞𑈬𑈴𑈺 | 16 |

Total: 119 code points. Full code point lists are in `gt_lines/lines.json`.

## Human check

The human check changed 4 of the 5 lines. Each change was drawn under the scan with `tools/compare.py` before it was accepted.

| Line | Draft | Checked | Evidence in the scan |
|---|---|---|---|
| p18_l02 | kha+i | pha+i | closed loop at the bottom left, which only pha has |
| p18_l02 | ba ta | ba+ii | the long tail below the line is the II sign |
| p18_l03 | kha+i | pha+i | same loop as l02 |
| p18_l03 | kha+M | tha+aa+M | three prongs on top (tha, kha has two), plus a vowel bar under the ring |
| p18_l04 | ma+aa+M | ta+aa+M | same bottom-left loop as the ta in l02 and l03 |
| p18_l04 | na+ii | ta+ii | same ta shape with an II sign |
| p18_l05 | pa+e | va+e | closest match in the font |
| p18_l05 | ha+ii | ha+ii+M | a missed anusvara |
| p18_l05 | pa ta ya | tha+ii ya+u | three glyphs misread |

The hollow ring above the vowel bar is anusvara (U+11234), not the abbreviation sign (U+1123D). Noto Sans Khojki draws the abbreviation sign on the baseline after the letter. The ring sits where anusvara goes, and these words end in "-āṃ", which needs anusvara.

Against the checked lines, the AI draft had 12 edits in 119 code points (10.1% CER). `tools/draft_cer.py` computes this and writes `results/gt_draft_check.json`.

Page 18 manual line count: 16 (`gt_lines/page_counts.json`).

Labelling time: only the first full check was measured. Finding and fixing errors in all 5 lines took about 34 minutes, or about 7 minutes per line. The labeller reported this time; no tool measured it (`results/labelling_manual.json`).

## Glyphs still unsure

1. **p18_l05, glyph 1:** va+e is the closest match, but it is not certain.
2. **p18_l04, word 4:** ta+ii or na+ii.
3. **p18_l04, word 4:** a small dot after A. It was ignored. It can be ink noise or an anusvara.

## Encoding rules used

1. Word separator `:` → U+1123A. It is never a space or an ASCII colon.
2. Page numbers → Gujarati digits U+0AE6–U+0AEF.
3. The wide gap before the page number is not encoded. The line ends with U+1123A, and the digits come after it. Use the same rule in the pipeline output.
4. Vowel signs are atomic code points. There are no decomposed pairs.
5. Order after the base letter: nukta, then vowel sign, then anusvara.
6. All lines are NFC and contain only code points in U+11200–U+11241 and U+0AE6–U+0AEF.

## Findings for the retro

1. **Font coverage:** Noto Sans Khojki v2.005 has no glyph for U+11241 (vowel sign vocalic R). It has U+1123F, U+11240 and the Gujarati digits. Do not put U+11241 in the synthetic training text.
2. **The AI was wrong, and the render check caught it:** in p18_l05, the AI first read glyph 2 as `ja+M`. The scan shows a closed loop below the letter. The render of `ja+u+M` matches the scan, and the render of `ja+M` does not.
3. **AI tool bug:** in the first version of `ktype.py`, the code `o` was used for both vowel sign O and sukun. So `ka+o` gave U+1123E (sukun), not U+11232. A code point test (`unicodedata.name`) found the bug.
4. **Lithograph and handwriting:** the AI could not read the 1896 lithograph line or the handwritten line reliably. Most glyph shapes do not match the font. No ground truth is given for them.

## Tools

- `tools/ktype.py "codes"`: converts short codes to Khojki Unicode. Run `--help` to see the code table. Use `sk` for sukun.
- `tools/compare.py CROP.png "codes" OUT.png`: draws the scan crop above your codes in Noto Sans Khojki.
