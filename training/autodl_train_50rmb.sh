#!/usr/bin/env bash
set -euo pipefail

# Budget-capped AutoDL verification run for Sera V0.5.
# The checkpoint is saved twice: once in the run directory and once in a
# persistent model directory with a SHA256 manifest and tar.gz archive.

REPO_URL="${REPO_URL:-https://github.com/Selancee/Sera.git}"
WORKDIR="${WORKDIR:-/root/Sera}"
DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp/sera_data}"
RUN_ROOT="${RUN_ROOT:-/root/autodl-tmp/sera_runs}"
MODEL_ROOT="${MODEL_ROOT:-/root/autodl-tmp/sera_models}"
ASAP_URL="${ASAP_URL:-https://github.com/fosfrancesco/asap-dataset.git}"
CONFIG="${CONFIG:-training/configs/sera_v05_50rmb.yaml}"

BUDGET_RMB="${BUDGET_RMB:-50}"
GPU_RMB_PER_HOUR="${GPU_RMB_PER_HOUR:-1.98}"
RESERVED_RMB="${RESERVED_RMB:-8}"
MAX_RUN_HOURS="${MAX_RUN_HOURS:-20}"
MAX_EXAMPLES="${MAX_EXAMPLES:-1200}"
MAX_FILES="${MAX_FILES:-1200}"
EPOCHS="${EPOCHS:-6}"
MODEL_NAME_PREFIX="${MODEL_NAME_PREFIX:-sera_v05_50rmb}"
USE_V05_MULTITASK="${USE_V05_MULTITASK:-1}"

RUN_ID="${MODEL_NAME_PREFIX}_$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${RUN_ROOT}/${RUN_ID}"
FINAL_MODEL_DIR="${MODEL_ROOT}/${RUN_ID}"
MAX_SECONDS=$((MAX_RUN_HOURS * 3600))
TRAIN_EXIT_CODE=0

mkdir -p "${DATA_ROOT}" "${RUN_ROOT}" "${MODEL_ROOT}" "${OUT_DIR}"

write_json_status() {
  local phase="$1"
  python - <<PY
import json
from pathlib import Path

payload = {
    "phase": "${phase}",
    "run_id": "${RUN_ID}",
    "budget_rmb": float("${BUDGET_RMB}"),
    "gpu_rmb_per_hour": float("${GPU_RMB_PER_HOUR}"),
    "reserved_rmb": float("${RESERVED_RMB}"),
    "max_run_hours": int("${MAX_RUN_HOURS}"),
    "max_seconds": int("${MAX_SECONDS}"),
    "max_examples": int("${MAX_EXAMPLES}"),
    "max_files": int("${MAX_FILES}"),
    "epochs": int("${EPOCHS}"),
    "out_dir": "${OUT_DIR}",
    "final_model_dir": "${FINAL_MODEL_DIR}",
    "repo_url": "${REPO_URL}",
}
Path("${OUT_DIR}/run_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY
}

finalize_model() {
  set +e
  mkdir -p "${FINAL_MODEL_DIR}"
  if [ -d "${OUT_DIR}" ]; then
    for file_name in \
      model.pt \
      vocab.json \
      training_metrics.json \
      training_config_snapshot.json \
      samples.json \
      train.log \
      run_status.json \
      baseline_score_eval.json \
      README.md; do
      if [ -f "${OUT_DIR}/${file_name}" ]; then
        cp -f "${OUT_DIR}/${file_name}" "${FINAL_MODEL_DIR}/${file_name}"
      fi
    done
    if [ -f "${OUT_DIR}/sha256_manifest.txt" ]; then
      cp -f "${OUT_DIR}/sha256_manifest.txt" "${FINAL_MODEL_DIR}/sha256_manifest.txt"
    fi
  fi

  python - <<PY
import hashlib
import json
from pathlib import Path

model_dir = Path("${FINAL_MODEL_DIR}")
model_dir.mkdir(parents=True, exist_ok=True)
manifest_lines = []
for path in sorted(model_dir.iterdir()):
    if not path.is_file() or path.name == "sha256_manifest.txt":
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_lines.append(f"{digest}  {path.name}")
(model_dir / "sha256_manifest.txt").write_text("\\n".join(manifest_lines) + ("\\n" if manifest_lines else ""), encoding="utf-8")
card = {
    "model_name": "${RUN_ID}",
    "sera_version": "v0.5-50rmb-tech-verify",
    "task": "symbolic local fragment / MusicXML token verification",
    "budget_rmb": float("${BUDGET_RMB}"),
    "max_run_hours": int("${MAX_RUN_HOURS}"),
    "max_examples": int("${MAX_EXAMPLES}"),
    "checkpoint": "model.pt",
    "vocab": "vocab.json",
    "sha256_manifest": "sha256_manifest.txt",
    "fallback_runtime": "Sera uses rule-based/hybrid fallback when checkpoint is unavailable.",
}
(model_dir / "model_card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
PY

  if [ -d "${FINAL_MODEL_DIR}" ]; then
    ln -sfn "${FINAL_MODEL_DIR}" "${MODEL_ROOT}/latest_50rmb"
    tar -C "${MODEL_ROOT}" -czf "${MODEL_ROOT}/${RUN_ID}.tar.gz" "${RUN_ID}"
  fi
  echo "[Sera] Persistent model copy: ${FINAL_MODEL_DIR}"
  echo "[Sera] Model archive: ${MODEL_ROOT}/${RUN_ID}.tar.gz"
}

trap finalize_model EXIT
write_json_status "started"

echo "[Sera] 50 RMB technical verification run"
echo "[Sera] budget=${BUDGET_RMB} RMB, reserved=${RESERVED_RMB} RMB, gpu_price=${GPU_RMB_PER_HOUR} RMB/hour"
echo "[Sera] max_run_hours=${MAX_RUN_HOURS}, max_examples=${MAX_EXAMPLES}, epochs=${EPOCHS}"
echo "[Sera] workdir=${WORKDIR}"
echo "[Sera] out_dir=${OUT_DIR}"
echo "[Sera] final_model_dir=${FINAL_MODEL_DIR}"

if [ ! -d "${WORKDIR}/.git" ]; then
  git clone "${REPO_URL}" "${WORKDIR}"
else
  git -C "${WORKDIR}" pull --ff-only
fi

cd "${WORKDIR}"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyyaml
if ! python - <<'PY'
try:
    import torch  # noqa: F401
except ImportError:
    raise SystemExit(1)
PY
then
  python -m pip install torch --index-url https://download.pytorch.org/whl/cu121
fi

if [ ! -d "${DATA_ROOT}/asap-dataset/.git" ]; then
  git clone --depth 1 "${ASAP_URL}" "${DATA_ROOT}/asap-dataset"
else
  git -C "${DATA_ROOT}/asap-dataset" pull --ff-only
fi

TRAIN_TOKENS="data/tokenized_v05/multitask_dataset.jsonl"
if [ "${USE_V05_MULTITASK}" = "1" ] && [ -f "training/tasks/build_multitask_dataset.py" ]; then
  echo "[Sera] Building V0.5 multitask dataset..."
  if ! python training/tasks/build_multitask_dataset.py \
    --input_dirs examples/scores "${DATA_ROOT}/asap-dataset" \
    --output "${TRAIN_TOKENS}" \
    --max_files "${MAX_FILES}"; then
    echo "[Sera] V0.5 multitask dataset failed; falling back to coarse MusicXML tokens."
    TRAIN_TOKENS=""
  fi
fi

if [ -z "${TRAIN_TOKENS}" ] || [ ! -s "${TRAIN_TOKENS}" ]; then
  echo "[Sera] Building fallback MusicXML token dataset..."
  python training/build_dataset.py \
    --sources examples/scores "${DATA_ROOT}/asap-dataset" \
    --out data/processed/musicxml_dataset.jsonl \
    --max-examples "${MAX_EXAMPLES}"
  python training/tokenize_musicxml.py \
    --dataset data/processed/musicxml_dataset.jsonl \
    --out data/processed/musicxml_tokens.jsonl
  TRAIN_TOKENS="data/processed/musicxml_tokens.jsonl"
fi

RUN_CONFIG="${OUT_DIR}/sera_v05_50rmb.resolved.yaml"
python - <<PY
from pathlib import Path
import yaml

source = Path("${CONFIG}")
if source.exists():
    config = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
else:
    config = {}
config.setdefault("model", {})
config.setdefault("data", {})
config.setdefault("training", {})
config["data"]["dataset_path"] = "${TRAIN_TOKENS}"
config["data"]["train_tokens"] = "${TRAIN_TOKENS}"
config["data"]["max_examples"] = int("${MAX_EXAMPLES}")
config["training"]["num_epochs"] = int("${EPOCHS}")
config["budget"] = {
    "target_rmb": float("${BUDGET_RMB}"),
    "gpu_price_rmb_per_hour": float("${GPU_RMB_PER_HOUR}"),
    "reserved_rmb": float("${RESERVED_RMB}"),
    "max_train_hours": int("${MAX_RUN_HOURS}"),
}
Path("${RUN_CONFIG}").write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
PY

set +e
timeout "${MAX_SECONDS}" python training/train_symbolic_model.py \
  --tokens "${TRAIN_TOKENS}" \
  --config "${RUN_CONFIG}" \
  --out "${OUT_DIR}" \
  --device auto \
  --max-examples "${MAX_EXAMPLES}" 2>&1 | tee "${OUT_DIR}/train.log"
TRAIN_EXIT_CODE=${PIPESTATUS[0]}
set -e

if [ "${TRAIN_EXIT_CODE}" -eq 124 ]; then
  echo "[Sera] Training reached max time budget and was stopped by timeout."
elif [ "${TRAIN_EXIT_CODE}" -ne 0 ]; then
  echo "[Sera] Training exited with code ${TRAIN_EXIT_CODE}."
else
  echo "[Sera] Training finished inside budget."
fi

if [ -f "training/evaluate_model.py" ]; then
  python training/evaluate_model.py \
    --scores examples/scores \
    --out "${OUT_DIR}/baseline_score_eval.json" || true
fi

cat > "${OUT_DIR}/README.md" <<EOF
# Sera 50 RMB AutoDL Technical Verification

- run_id: ${RUN_ID}
- budget_rmb: ${BUDGET_RMB}
- max_run_hours: ${MAX_RUN_HOURS}
- max_examples: ${MAX_EXAMPLES}
- epochs: ${EPOCHS}
- train_tokens: ${TRAIN_TOKENS}
- output_dir: ${OUT_DIR}
- persistent_model_dir: ${FINAL_MODEL_DIR}
- archive: ${MODEL_ROOT}/${RUN_ID}.tar.gz
- train_exit_code: ${TRAIN_EXIT_CODE}

Required runtime artifacts:
- model.pt
- vocab.json

Audit artifacts:
- training_metrics.json
- training_config_snapshot.json
- samples.json
- train.log
- sha256_manifest.txt
- model_card.json
EOF

write_json_status "finished"
finalize_model
trap - EXIT

if [ "${TRAIN_EXIT_CODE}" -ne 0 ] && [ ! -f "${OUT_DIR}/model.pt" ]; then
  exit "${TRAIN_EXIT_CODE}"
fi

echo "[Sera] Done."
echo "[Sera] Remote run dir: ${OUT_DIR}"
echo "[Sera] Remote model dir: ${FINAL_MODEL_DIR}"
