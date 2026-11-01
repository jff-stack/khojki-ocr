# Retro

## 1. Pipeline

Page PNG → line segmentation inside the printed frame (projection profile) → kraken model trained from scratch on synthetic lines → normalisation → validator → render score. Training text is <!-- VAL:corpus_lines -->2071<!-- /VAL:corpus_lines --> lines of transliterated Gujarati poems, generated syllables and punctuation, rendered in Noto Sans Khojki with scan-like damage.

## 2. Results

On the 5 test lines (<!-- VAL:n_cp -->119<!-- /VAL:n_cp --> code points), CER is <!-- VAL:cer_b -->21.8% (26/119)<!-- /VAL:cer_b --> with hand crops and <!-- VAL:cer_a -->18.5% (22/119)<!-- /VAL:cer_a --> with the pipeline's crops. Held-out synthetic CER is <!-- VAL:val_cer_damaged -->0.3%<!-- /VAL:val_cer_damaged -->, so nearly all the error comes from the difference between the font and 1903 metal type. Segmentation found <!-- VAL:auto_lines -->16<!-- /VAL:auto_lines --> lines on page 18; I counted <!-- VAL:manual_lines -->16<!-- /VAL:manual_lines -->.

## 3. Error breakdown by stage

Recognition <!-- VAL:stage_recognition -->26 (100%)<!-- /VAL:stage_recognition -->, line detection <!-- VAL:stage_line_detection -->-4 (0%)<!-- /VAL:stage_line_detection --> (the automatic crops did slightly better than mine), Unicode mapping <!-- VAL:stage_mapping -->0 (0%)<!-- /VAL:stage_mapping -->. The errors are extra or missing vowel signs, letter swaps and misread page digits.

## 4. Experiments that failed

- Clean renders only: no learning in 10 minutes. After 20 minutes (<!-- VAL:epochs_clean -->2<!-- /VAL:epochs_clean --> epochs, synthetic val CER <!-- VAL:val_cer_clean -->29.2%<!-- /VAL:val_cer_clean -->) it scored <!-- VAL:cer_clean -->99.2% (118/119)<!-- /VAL:cer_clean --> on real lines. It also trained far less than the damaged model, so this does not isolate the effect of damage.
- The damaged model gets <!-- VAL:gate_on_damaged -->99.82%<!-- /VAL:gate_on_damaged --> character accuracy on damaged synthetic lines and <!-- VAL:gate_on_clean -->-28.54%<!-- /VAL:gate_on_clean --> on clean white renders. It learned the paper texture too.
- My first corpus put shadda after vowel signs, which the font draws as dotted circles.
- The render score does not track CER (Spearman <!-- VAL:spearman -->-0.718<!-- /VAL:spearman -->, 5 lines).

## 5. Encoding decisions

U+1123A as the word separator, Gujarati digits, atomic vowel signs only (all eight Table 15-4 sequences repaired), nukta → vowel sign → anusvara, NFC. The page-number gap is not encoded. The ring above the vowel bar is anusvara.

## 6. Bottleneck

Real labelled lines. The kraken documentation suggests at least 800 lines for a new model, and Reul et al. report under 1% CER on early printed books with about 1,000. The next step is to transcribe 800 to 1,000 lines of 1903-type print and fine-tune this model on them.

## 7. Scale

A page takes <!-- VAL:sec_per_page -->8.0<!-- /VAL:sec_per_page --> s on <!-- VAL:device -->cpu<!-- /VAL:device -->, so a few hundred pages fit in one overnight run (estimate). Labelling costs more than compute. My check was not timed. At 1 to 2 minutes per line (estimate), 1,000 lines is 17 to 33 hours of skilled work (estimate). Lithographs and handwriting need their own segmentation and data.

## 8. AI tools

An AI drafted the ground truth. A person checked it against rendered glyphs and changed <!-- VAL:draft_lines_changed -->4 of 5<!-- /VAL:draft_lines_changed --> lines: the draft had <!-- VAL:draft_cer -->10.1% (12/119)<!-- /VAL:draft_cer --> CER. The mistakes were plausible letter swaps (kha/pha/tha, ma/ta) and missed marks, which would otherwise have been scored as model errors. `AI_ERRORS.md` lists seven cases, each caught by rendering, `unicodedata.name()` or the spec itself.
