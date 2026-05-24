import json
import subprocess
import tempfile


def clone_branch(repo_url: str, branch: str, target_dir: str | None = None) -> dict:
    target = target_dir or tempfile.mkdtemp(prefix="aeo-")
    subprocess.run(
        ["git", "clone", "--depth", "1", "-b", branch, repo_url, target],
        check=True, capture_output=True, text=True, timeout=300,
    )
    return {"path": target}


def run_tests(repo_path: str, test_path: str = "tests/") -> dict:
    report_file = f"{repo_path}/.aeo_report.json"
    subprocess.run(
        ["pytest", test_path, "--json-report", f"--json-report-file={report_file}", "-q"],
        cwd=repo_path, capture_output=True, text=True, timeout=600,
    )
    return parse_pytest_report(report_file)


def run_linter(repo_path: str) -> dict:
    proc = subprocess.run(
        ["ruff", "check", ".", "--output-format=json"],
        cwd=repo_path, capture_output=True, text=True, timeout=120,
    )
    violations = json.loads(proc.stdout) if proc.stdout.strip() else []
    return {"passed": len(violations) == 0, "violations": violations}


def parse_pytest_report(report_path: str) -> dict:
    with open(report_path) as f:
        data = json.load(f)
    summary = data.get("summary", {})
    failures = [
        {"nodeid": t["nodeid"], "longrepr": t.get("call", {}).get("longrepr", "")}
        for t in data.get("tests", [])
        if t.get("outcome") == "failed"
    ]
    return {"passed": summary.get("failed", 0) == 0, "totals": summary, "failures": failures}
