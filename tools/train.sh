#!/usr/bin/env bash
# usage: tools/train.sh DATA_DIR RUN_NAME MINUTES [DEVICE] [EPOCHS]
# Trains a kraken VGSL model from scratch with early stopping and a hard time cap.
set -euo pipefail
data=$1 name=$2 minutes=$3 device=${4:-cuda:0} epochs=${5:-100}
BATCH=${BATCH:-16}
ketos=${KETOS:-.venv/bin/ketos}
out=models/runs/$name
log=results/train_$name.log
mkdir -p "$out" results
start=$(date +%s)
# script(1) gives ketos a pseudo-terminal so its per-epoch progress lines reach the log
script -qfec "timeout --signal=INT ${minutes}m $ketos -d $device --workers 8 --threads 4 -s 42 \
    train -f path -B $BATCH -u NFC -p 0.9 -q early --lag 5 --min-epochs 3 -N $epochs \
    -o $out $data/*.png" /dev/null | tr '\r' '\n' | grep --line-buffered -E "stage|val_|best|Aborted|Error|error|Saving|Moving" > "$log" || true
echo "train_minutes=$(( ($(date +%s) - start) / 60 ))" >> "$log"
