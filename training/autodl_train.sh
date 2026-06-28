#!/usr/bin/env bash
set -euo pipefail

# AutoDL entrypoint for a budget-constrained Sera symbolic training run.
# TODO: add resumable experiment tracking when longer PDMX runs are scheduled.

REPO_URL="${REPO_URL:-https://github.com/Selancee/Sera.git}"
WORKDIR="${WORKDIR:-/root/Sera}"
DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp/sera_data}"
RUN_ROOT="${RUN_ROOT:-/root/autodl-tmp/sera_runs}"
MAX_EXAMPLES="${MAX_EXAMPLES:-600}"
EPOCHS="${EPOCHS:-5}"
ASAP_URL="${ASAP_URL:-https://github.com/fosfrancesco/asap-dataset.git}"

echo "[Sera] repo=${REPO_URL}"
echo "[Sera] workdir=${WORKDIR}"
echo "[Sera] data_root=${DATA_ROOT}"
echo "[Sera] run_root=${RUN_ROOT}"
mkdir -p "${DATA_ROOT}" "${RUN_ROOT}"

if [ ! -d "${WORKDIR}/.git" ]; then
  git clone "${REPO_URL}" "${WORKDIR}"
else
  git -C "${WORKDIR}" pull --ff-only
fi

cd "${WORKDIR}"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if ! python - <<'PY'
try:
    import torch  # noqa: F401
except ImportError:
    raise SystemExit(1)
PY
then
  python -m pip install torch --index-url https://download.pytorch.org/whl/cu121
fi
python -m pip install pyyaml

if [ ! -d "${DATA_ROOT}/asap-dataset/.git" ]; then
  git clone --depth 1 "${ASAP_URL}" "${DATA_ROOT}/asap-dataset"
else
  git -C "${DATA_ROOT}/asap-dataset" pull --ff-only
fi

RUN_ID="autodl_$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${RUN_ROOT}/${RUN_ID}"
mkdir -p "${OUT_DIR}"

python training/build_dataset.py \
  --sources examples/scores "${DATA_ROOT}/asap-dataset" \
  --out data/processed/musicxml_dataset.jsonl \
  --max-examples "${MAX_EXAMPLES}"

python training/tokenize_musicxml.py \
  --dataset data/processed/musicxml_dataset.jsonl \
  --out data/processed/musicxml_tokens.jsonl

RUN_CONFIG="${OUT_DIR}/sera_symbolic_small.yaml"
cp training/configs/sera_symbolic_small.yaml "${RUN_CONFIG}"
python - <<PY
from pathlib import Path
path = Path("${RUN_CONFIG}")
text = path.read_text(encoding="utf-8")
text = text.replace("epochs: 5", "epochs: ${EPOCHS}")
path.write_text(text, encoding="utf-8")
PY

python training/train_symbolic_model.py \
  --tokens data/processed/musicxml_tokens.jsonl \
  --config "${RUN_CONFIG}" \
  --out "${OUT_DIR}" \
  --device auto \
  --max-examples "${MAX_EXAMPLES}" | tee "${OUT_DIR}/train.log"

python training/evaluate_model.py \
  --scores examples/scores \
  --out "${OUT_DIR}/baseline_score_eval.json"

cat > "${OUT_DIR}/README.md" <<EOF
# Sera AutoDL Training Run

- run_id: ${RUN_ID}
- dataset: Sera generated examples + ASAP GitHub MusicXML files
- max_examples: ${MAX_EXAMPLES}
- epochs: ${EPOCHS}
- output_dir: ${OUT_DIR}

Artifacts:
- model.pt
- vocab.json
- training_metrics.json
- samples.json
- baseline_score_eval.json
- train.log
EOF

echo "[Sera] Training run complete: ${OUT_DIR}"
echo "[Sera] To publish lightweight records, copy README.md/training_metrics.json/samples.json into docs/training_runs/ and commit."
