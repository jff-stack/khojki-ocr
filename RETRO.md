# Retro

## 1. Pipeline

Page PNG → line segmentation inside the printed frame (projection profile) → kraken model trained from scratch on synthetic lines → normalisation → validator → render score. Training text is <!-- VAL:corpus_lines -->2071<!-- /VAL:corpus_lines --> lines (transliterated Gujarati poems, syllables, punctuation) rendered in Noto Sans Khojki with scan-like damage.

## 2. Results

On the 5 test lines (<!-- VAL:n_cp -->119<!-- /VAL:n_cp --> code points), CER is <!-- VAL:cer_b -->21.8% (26/119)<!-- /VAL:cer_b --> with hand crops and <!-- VAL:cer_a -->18.5% (22/119)<!-- /VAL:cer_a --> with the pipeline's crops. Held-out synthetic CER is <!-- VAL:val_cer_damaged -->0.3%<!-- /VAL:val_cer_damaged -->, so the error is the gap between the font and 1903 metal type. Segmentation found <!-- VAL:auto_lines -->16<!-- /VAL:auto_lines --> lines on page 18; I counted <!-- VAL:manual_lines -->16<!-- /VAL:manual_lines -->.

## 3. Error breakdown by stage

Recognition <!-- VAL:stage_recognition -->26 (100%)<!-- /VAL:stage_recognition -->, line detection <!-- VAL:stage_line_detection -->-4 (0%)<!-- /VAL:stage_line_detection --> (automatic crops beat mine), Unicode mapping <!-- VAL:stage_mapping -->0 (0%)<!-- /VAL:stage_mapping -->. The errors are extra or missing vowel signs, letter swaps and misread page digits.

## 4. Experiments that failed

- Clean renders only: no learning in 10 minutes. After 20 minutes (<!-- VAL:epochs_clean -->2<!-- /VAL:epochs_clean --> epochs, synthetic val CER <!-- VAL:val_cer_clean -->29.2%<!-- /VAL:val_cer_clean -->) it scored <!-- VAL:cer_clean -->99.2% (118/119)<!-- /VAL:cer_clean --> on real lines. It trained too little to isolate the effect of damage.
- The damaged model gets <!-- VAL:gate_on_damaged -->99.82%<!-- /VAL:gate_on_damaged --> character accuracy on damaged synthetic lines and <!-- VAL:gate_on_clean -->-28.54%<!-- /VAL:gate_on_clean --> on clean white renders.
- The render score does not track CER (Spearman <!-- VAL:spearman -->-0.718<!-- /VAL:spearman -->, 5 lines).

## 5. Encoding decisions

Vowel signs are the atomic code points U+1122C to U+11233; the eight decomposed sequences in Unicode Table 15-4 are repaired. Word separator U+1123A, digits Gujarati U+0AE6 to U+0AEF, NFC, mark order nukta, vowel sign, anusvara. The ring above the vowel bar is anusvara U+11234. `validate.py` flags illegal code points, orphan marks, mark order, stacked vowel signs and do-not-use sequences, reported per line.

## 6. Bottleneck

Real labelled lines. kraken's docs suggest at least 800 lines for a new model, and Reul et al. report under 1% CER on early printed books with about 1,000. Next: transcribe 800 to 1,000 lines of 1903-type print and fine-tune on them.

## 7. Scale

Page 18 took <!-- VAL:sec_per_page -->8.0<!-- /VAL:sec_per_page --> s on <!-- VAL:device -->cpu<!-- /VAL:device -->: about <!-- VAL:min_sample_pages -->6<!-- /VAL:min_sample_pages --> minutes for the 45 sample pages and <!-- VAL:hours_1000_pages -->2.2<!-- /VAL:hours_1000_pages --> hours per 1,000 pages (estimate). Labelling costs far more: my first full check took about <!-- VAL:first_check_min -->34<!-- /VAL:first_check_min --> minutes, <!-- VAL:first_check_per_line -->7<!-- /VAL:first_check_per_line --> per line (self-reported), so 1,000 lines is about <!-- VAL:est_hours_1000 -->117<!-- /VAL:est_hours_1000 --> hours (estimate). Handwriting has no printed frame and uneven baselines: it needs a trained layout model and labelled lines per hand, as font-rendered data will not transfer.

## 8. AI tools

I verified every test line glyph by glyph against rendered text. Starting from an AI draft, my check changed <!-- VAL:draft_lines_changed -->4 of 5<!-- /VAL:draft_lines_changed --> lines: the draft had <!-- VAL:draft_cer -->10.1% (12/119)<!-- /VAL:draft_cer --> CER. Its errors (kha/pha/tha and ma/ta swaps, missed marks) would otherwise have been scored as model errors. `AI_ERRORS.md` lists seven cases.
