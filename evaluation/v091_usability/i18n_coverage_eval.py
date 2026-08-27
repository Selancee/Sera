from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def locale_coverage() -> dict[str, float]:
    en = json.loads((PROJECT_ROOT / "frontend" / "src" / "i18n" / "locales" / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((PROJECT_ROOT / "frontend" / "src" / "i18n" / "locales" / "zh-CN.json").read_text(encoding="utf-8"))
    all_keys = set(en) | set(zh)
    if not all_keys:
        return {"translation_coverage_rate": 0.0, "zh_cn_translation_coverage_rate": 0.0}
    return {
        "translation_coverage_rate": len(set(en) & set(zh)) / len(all_keys),
        "zh_cn_translation_coverage_rate": sum(1 for key in all_keys if str(zh.get(key, "")).strip()) / len(all_keys),
    }


if __name__ == "__main__":
    print(json.dumps(locale_coverage(), indent=2))
