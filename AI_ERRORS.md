# AI errors log

A dated record of places where an AI tool (chat assistant, coding assistant or
transliteration library) was wrong about Khojki, and how each mistake was caught.
Entries 1 to 3 come from the ground-truth drafting work described in `GROUND_TRUTH.md`.

| # | Date | Tool | What the AI believed | What is true | How it was caught |
|---|---|---|---|---|---|
| 1 | 2026-10-31 | Chat assistant (GT draft) | p18_l05 glyph 2 is `ja+M` (U+11210 U+11234) | The scan shows a closed loop below the letter: `ja+u+M` (U+11210 U+1122F U+11234) | Render check: `ja+u+M` drawn in Noto Sans Khojki matched the scan crop; `ja+M` did not |
| 2 | 2026-10-31 | Coding assistant (`ktype.py` v1) | Code `o` could mean both vowel sign O and sukun | `ka+o` must give U+11208 U+11232 (KHOJKI VOWEL SIGN O); sukun is U+1123E and now has its own code `sk` | Unit test comparing `unicodedata.name()` of the output with the expected name |
| 3 | 2026-10-31 | Assumption in early plan | Noto Sans Khojki covers the whole block | v2.005 has no glyph for U+11241 KHOJKI VOWEL SIGN VOCALIC R | `tools/check_font.py` reads the font cmap; see `results/font_coverage.txt` |
| 4 | 2026-10-31 | Coding assistant (`corpus.py` v1) | Shadda and virama can follow a vowel sign, as in "nukta, vowel sign, other marks" | With Noto Sans Khojki and HarfBuzz, virama or shadda after any mark other than nukta is drawn with a dotted circle (U+25CC). The synthetic data would have taught the model broken glyphs | Visual check of `results/synth_samples.png`, then an exhaustive render test of every KA + mark sequence. The generator now puts shadda/virama only on bare consonants and `corpus.py` drops lines that would break shaping |
| 5 | 2026-10-31 | Coding assistant (prompt summary) | Table 15-4 has three do-not-use pairs (A+AA, AA+E, AA+AI) | The Unicode 17.0 core spec lists eight sequences, including <U+11240, U+1122E> for I, <U+11206, U+1122C> for U and the three-part <U+11200, U+1122C, U+11231> for AU | Read the spec text from unicode.org before writing `charset.DO_NOT_USE`; one test per sequence |
