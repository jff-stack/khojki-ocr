#!/usr/bin/env bash
# usage: tools/train.sh DATA_DIR RUN_NAME MINUTES [DEVICE]
set -euo pipefail
data=$1 name=$2 minutes=$3 device=${4:-cuda:0}
ketos=${KETOS:-.venv/bin/ketos}
out=models/runs/$name
mkdir -p "$out" results
start=$(date +%s)
timeout --signal=INT "${minutes}m" "$ketos" -d "$device" --workers 8 --threads 4 -s 42 \
    train -f path -B 32 -u NFC -p 0.9 -q early --lag 5 --min-epochs 3 -N 100 \
    -o "$out" "$data"/*.png 2>&1 | tee "results/train_$name.log" || true
echo "train_minutes=$(( ($(date +%s) - start) / 60 ))" | tee -a "results/train_$name.log"
