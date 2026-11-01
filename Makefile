VENV ?= .venv
PY := $(VENV)/bin/python
KETOS := $(VENV)/bin/ketos
PAGES ?= 18
MODEL ?= models/khojki_best.mlmodel
SYNTH_N ?= 10000
CLEAN_N ?= 4000
DEVICE ?= cuda:0

.PHONY: setup pages synth train train-clean run eval report test all clean-results

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	$(PY) -c "from PIL import features; assert features.check_feature('raqm'), 'Pillow has no raqm: install libraqm/libfribidi'"
	$(PY) tools/check_font.py

pages:
	$(PY) tools/pdf_to_pages.py

synth:
	$(PY) -m khojki.corpus
	$(PY) -m khojki.render --n $(SYNTH_N) --out data/synth/damaged
	$(PY) -m khojki.render --n $(CLEAN_N) --out data/synth/clean --clean

train:
	KETOS=$(KETOS) tools/train.sh data/synth/damaged damaged 35 $(DEVICE)
	$(PY) tools/train_summary.py
	$(KETOS) convert -o models/khojki_best.mlmodel --weights-format coreml \
		$$($(PY) -c "import json;print(json.load(open('results/train_summary.json'))['damaged']['best_checkpoint'])")

train-clean:
	KETOS=$(KETOS) tools/train.sh data/synth/clean clean 20 $(DEVICE)
	$(PY) tools/train_summary.py
	$(KETOS) convert -o models/khojki_clean.mlmodel --weights-format coreml \
		$$($(PY) -c "import json;print(json.load(open('results/train_summary.json'))['clean']['best_checkpoint'])")

run:
	$(PY) pipeline.py $(foreach p,$(PAGES),data/pages/page_$(p).png) --model $(MODEL) --out results/out/

eval:
	$(PY) -m khojki.evaluate --model $(MODEL)

report:
	$(PY) tools/make_tables.py

test:
	$(PY) -m pytest -q

all: run eval report test
