# Test lines and ground truth

5 test lines. All 5 lines are from page 18 of the sample PDF (1903 Pir Imam Shah, contents page, metal type).

## How these transcriptions were made

1. An AI assistant (Claude) made the first draft of each line. It matched each glyph in the scan to the Unicode chart.
2. Each draft was drawn in Noto Sans Khojki under the scan crop (`*.check.png`). Each glyph was compared by eye, and the draft was corrected.
3. **A person must check each line against the scan before you use it as ground truth.** Open the `*.check.png` file. Compare the shapes from left to right. Fix the line with `tools/ktype.py`, then run `tools/compare.py` again.
4. Record the time that each check takes. Use that time as your labelling cost.

State this method in the retro. The AI drafted the ground truth, and a person checked it. A reviewer must know this.

## Lines

| id | Confidence | Codes (input for ktype.py) | Unicode | Code points |
|---|---|---|---|---|
| p18_l02 | high | `U pa na+aa+M : kha+i ra sa ta+aa : ta ba : ba+aa ta+aa+M : ba ta ba : 16` | 𑈃𑈟𑈞𑈬𑈴𑈺𑈉𑈭𑈦𑈩𑈙𑈬𑈺𑈙𑈡𑈺𑈡𑈬𑈙𑈬𑈴𑈺𑈡𑈙𑈡𑈺૧૬ | 28 |
| p18_l03 | high | `AA ga+e : AA da ma : kha+i ra sa ta+aa : sa+aa kha+M : 17` | 𑈁𑈊𑈰𑈺𑈁𑈛𑈤𑈺𑈉𑈭𑈦𑈩𑈙𑈬𑈺𑈩𑈬𑈉𑈴𑈺૧૭ | 22 |
| p18_l04 | medium | `sa+o : sa ba : ha+u pa : A pa na+ii : ja+aa ma+aa+M : 18` | 𑈩𑈲𑈺𑈩𑈡𑈺𑈪𑈯𑈟𑈺𑈀𑈟𑈞𑈮𑈺𑈐𑈬𑈤𑈬𑈴𑈺૧૮ | 23 |
| p18_l05 | medium | `pa+e ja+u+M ha+ii : sa+aa ja+aa : sa+aa+M ha+ii AA+M : pa ta ya ja ta :` | 𑈟𑈰𑈐𑈯𑈴𑈪𑈮𑈺𑈩𑈬𑈐𑈬𑈺𑈩𑈬𑈴𑈪𑈮𑈁𑈴𑈺𑈟𑈙𑈥𑈐𑈙𑈺 | 27 |
| p18_l06 | high | `AA pa : na+i ra+M ja na : U pa na+aa+M :` | 𑈁𑈟𑈺𑈞𑈭𑈦𑈴𑈐𑈞𑈺𑈃𑈟𑈞𑈬𑈴𑈺 | 16 |

Total: 116 code points. Full code point lists are in `gt_lines/lines.json`.

## Glyphs to check first

1. **p18_l04, word 3, last glyph:** pa or independent vowel E (U+11204).
2. **p18_l04, word 4:** a small dot after A. It was ignored. It can be ink noise or an anusvara.
3. **p18_l04, last word:** ma or ta.
4. **p18_l05, glyph 1:** pa+e or kha+e.
5. **p18_l02, glyph 2:** pa. It has a small curl at the base. The same shape is in p18_l04 and p18_l05, so it is probably how this type draws pa.

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
