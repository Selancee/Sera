#!/usr/bin/env bash
set -euo pipefail

# Run from an uploaded Sera source tree. This script does not git clone or pull.
# It saves model artifacts both in the run directory and in a persistent model
# directory so the verification checkpoint can be recovered after the session.

WORKDIR="${WORKDIR:-$(pwd)}"
RUN_ROOT="${RUN_ROOT:-/root/autodl-tmp/sera_runs}"
MODEL_ROOT="${MODEL_ROOT:-/root/autodl-tmp/sera_models}"
BUDGET_RMB="${BUDGET_RMB:-47}"
GPU_RMB_PER_HOUR="${GPU_RMB_PER_HOUR:-2.88}"
MAX_RUN_HOURS="${MAX_RUN_HOURS:-12}"
MAX_EXAMPLES="${MAX_EXAMPLES:-1200}"
MAX_FILES="${MAX_FILES:-1200}"
EPOCHS="${EPOCHS:-6}"
MODEL_NAME_PREFIX="${MODEL_NAME_PREFIX:-sera_v05_50rmb}"
CONFIG="${CONFIG:-training/configs/sera_v05_50rmb.yaml}"

RUN_ID="${MODEL_NAME_PREFIX}_$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${RUN_ROOT}/${RUN_ID}"
FINAL_MODEL_DIR="${MODEL_ROOT}/${RUN_ID}"
MAX_SECONDS=$((MAX_RUN_HOURS * 3600))
TRAIN_EXIT_CODE=0

mkdir -p "${RUN_ROOT}" "${MODEL_ROOT}" "${OUT_DIR}" "${FINAL_MODEL_DIR}"

finalize_model() {
  set +e
  mkdir -p "${FINAL_MODEL_DIR}"
  for file_name in \
    model.pt \
    vocab.json \
    training_metrics.json \
    training_config_snapshot.json \
    samples.json \
    train.log \
    run_status.json \
    README.md; do
    if [ -f "${OUT_DIR}/${file_name}" ]; then
      cp -f "${OUT_DIR}/${file_name}" "${FINAL_MODEL_DIR}/${file_name}"
    fi
  done

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
(model_dir / "model_card.json").write_text(json.dumps({
    "model_name": "${RUN_ID}",
    "sera_version": "v0.5-50rmb-uploaded-source",
    "budget_rmb": float("${BUDGET_RMB}"),
    "gpu_rmb_per_hour": float("${GPU_RMB_PER_HOUR}"),
    "max_run_hours": int("${MAX_RUN_HOURS}"),
    "max_examples": int("${MAX_EXAMPLES}"),
    "checkpoint": "model.pt",
    "vocab": "vocab.json",
    "sha256_manifest": "sha256_manifest.txt",
}, ensure_ascii=False, indent=2), encoding="utf-8")
PY
  ln -sfn "${FINAL_MODEL_DIR}" "${MODEL_ROOT}/latest_50rmb"
  tar -C "${MODEL_ROOT}" -czf "${MODEL_ROOT}/${RUN_ID}.tar.gz" "${RUN_ID}"
  echo "[Sera] Persistent model copy: ${FINAL_MODEL_DIR}"
  echo "[Sera] Model archive: ${MODEL_ROOT}/${RUN_ID}.tar.gz"
}

trap finalize_model EXIT

cd "${WORKDIR}"
echo "[Sera] Uploaded-source 50 RMB verification"
echo "[Sera] workdir=${WORKDIR}"
echo "[Sera] out_dir=${OUT_DIR}"
echo "[Sera] final_model_dir=${FINAL_MODEL_DIR}"
echo "[Sera] budget=${BUDGET_RMB} RMB, gpu_price=${GPU_RMB_PER_HOUR} RMB/hour, max_hours=${MAX_RUN_HOURS}"

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

TRAIN_TOKENS="data/tokenized_v05/multitask_dataset.jsonl"
if [ ! -s "${TRAIN_TOKENS}" ]; then
  python training/tasks/build_multitask_dataset.py \
    --input_dirs examples/scores \
    --output "${TRAIN_TOKENS}" \
    --max_files "${MAX_FILES}"
fi

RUN_CONFIG="${OUT_DIR}/sera_v05_50rmb.resolved.yaml"
python - <<PY
from pathlib import Path
import yaml

source = Path("${CONFIG}")
config = yaml.safe_load(source.read_text(encoding="utf-8")) if source.exists() else {}
config = config or {}
config.setdefault("data", {})
config.setdefault("training", {})
config["data"]["dataset_path"] = "${TRAIN_TOKENS}"
config["data"]["train_tokens"] = "${TRAIN_TOKENS}"
config["data"]["max_examples"] = int("${MAX_EXAMPLES}")
config["training"]["num_epochs"] = int("${EPOCHS}")
config["budget"] = {
    "target_rmb": float("${BUDGET_RMB}"),
    "gpu_price_rmb_per_hour": float("${GPU_RMB_PER_HOUR}"),
    "max_train_hours": int("${MAX_RUN_HOURS}"),
}
Path("${RUN_CONFIG}").write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
PY

cat > "${OUT_DIR}/run_status.json" <<EOF
{
  "run_id": "${RUN_ID}",
  "budget_rmb": ${BUDGET_RMB},
  "gpu_rmb_per_hour": ${GPU_RMB_PER_HOUR},
  "max_run_hours": ${MAX_RUN_HOURS},
  "max_examples": ${MAX_EXAMPLES},
  "epochs": ${EPOCHS},
  "out_dir": "${OUT_DIR}",
  "final_model_dir": "${FINAL_MODEL_DIR}"
}
EOF

set +e
timeout "${MAX_SECONDS}" python training/train_symbolic_model.py \
  --tokens "${TRAIN_TOKENS}" \
  --config "${RUN_CONFIG}" \
  --out "${OUT_DIR}" \
  --device auto \
  --max-examples "${MAX_EXAMPLES}" 2>&1 | tee "${OUT_DIR}/train.log"
TRAIN_EXIT_CODE=${PIPESTATUS[0]}
set -e

cat > "${OUT_DIR}/README.md" <<EOF
# Sera 50 RMB Uploaded-Source Verification

- run_id: ${RUN_ID}
- budget_rmb: ${BUDGET_RMB}
- gpu_rmb_per_hour: ${GPU_RMB_PER_HOUR}
- max_run_hours: ${MAX_RUN_HOURS}
- max_examples: ${MAX_EXAMPLES}
- epochs: ${EPOCHS}
- train_exit_code: ${TRAIN_EXIT_CODE}
- out_dir: ${OUT_DIR}
- final_model_dir: ${FINAL_MODEL_DIR}
- archive: ${MODEL_ROOT}/${RUN_ID}.tar.gz
EOF

finalize_model
trap - EXIT

if [ "${TRAIN_EXIT_CODE}" -ne 0 ] && [ ! -f "${OUT_DIR}/model.pt" ]; then
  exit "${TRAIN_EXIT_CODE}"
fi

echo "[Sera] Done."
echo "[Sera] Run id: ${RUN_ID}"
echo "[Sera] Remote model dir: ${FINAL_MODEL_DIR}"
