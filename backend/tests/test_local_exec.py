import json

from app.local_exec.runner import parse_pytest_report


def test_parse_pytest_report_summarizes(tmp_path):
    report = {
        "summary": {"passed": 3, "failed": 1, "total": 4},
        "tests": [
            {
                "nodeid": "tests/test_x.py::test_a",
                "outcome": "failed",
                "call": {"longrepr": "AssertionError: expected 409 got 500"},
            }
        ],
    }
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report))
    result = parse_pytest_report(str(p))
    assert result["passed"] is False
    assert result["totals"] == {"passed": 3, "failed": 1, "total": 4}
    assert result["failures"][0]["nodeid"].endswith("test_a")
    assert "AssertionError" in result["failures"][0]["longrepr"]
