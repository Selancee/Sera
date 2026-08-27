"""Validate and smoke-retrieve the Composer V0.4 knowledge repository."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sera_edit.composer.knowledge_repository import ComposerKnowledgeError, ComposerKnowledgeRepository, REGISTRY_PATH
from sera_edit.composer.knowledge_retrieval import retrieve_composer_knowledge


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Composer V0.4 JSONL packs and small-context retrieval.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="Path to knowledge_registry.v0.4.json.")
    parser.add_argument("--token-budget", type=int, default=1800, help="Smoke retrieval token budget.")
    args = parser.parse_args()
    try:
        repository = ComposerKnowledgeRepository(args.registry)
        sample = retrieve_composer_knowledge(
            "为钢琴写一段古典风格变奏，保持动机并形成清晰终止",
            "classical",
            "theory_variation",
            score_document={"global": {"key": "C major", "meter": "4/4"}, "tracks": [{"instrument": "piano"}]},
            target_scope={"measures": [1, 2, 3, 4]},
            token_budget=args.token_budget,
            repository=repository,
        )
    except ComposerKnowledgeError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "valid",
                "corpus": repository.status(),
                "retrieval_smoke": sample["retrieval"],
                "selected_rule_ids": sample["selected_rule_ids"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
