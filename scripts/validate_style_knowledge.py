"""Validate and summarize a Sera Composer style knowledge JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sera_edit.composer.style_knowledge import KNOWLEDGE_PATH, StyleKnowledgeBase, StyleKnowledgeError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the versioned Sera Composer style knowledge base.")
    parser.add_argument("--path", type=Path, default=KNOWLEDGE_PATH, help="Path to style knowledge JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        knowledge = StyleKnowledgeBase.load(args.path)
    except StyleKnowledgeError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "valid",
                "knowledge_base_id": knowledge.knowledge_base_id,
                "schema_version": knowledge.schema_version,
                "fingerprint": knowledge.fingerprint,
                "style_count": len(knowledge.style_ids),
                "style_ids": list(knowledge.style_ids),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
