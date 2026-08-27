import json

from scripts.run_reviewer_demo import run_reviewer_demo


def test_reviewer_demo_runs_product_path_without_gold_generation(tmp_path):
    output = tmp_path / "reviewer-demo"
    report = run_reviewer_demo(
        output,
        task_ids=("pitch_001", "conflict_001"),
        languages=("en",),
    )

    assert report["passed"] is True
    assert report["network_used"] is False
    assert report["gold_used_for_generation"] is False
    assert report["results"]["passed"] == 2
    assert report["results"]["failed"] == 0
    assert report["host_openable_output_count"] == 1
    persisted = json.loads((output / "reviewer_demo_report.json").read_text(encoding="utf-8"))
    assert persisted["tasks"] == ["pitch_001", "conflict_001"]
