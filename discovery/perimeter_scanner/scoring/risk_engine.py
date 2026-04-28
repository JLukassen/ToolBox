from collections import defaultdict
from .severity_rules import risk_label


def calculate_score(findings: list[dict]) -> dict:
    starting_score = 100
    total_impact = sum(max(0, f.get("score_impact", 0)) for f in findings)
    final_score = max(0, starting_score - total_impact)

    category_summary = defaultdict(int)
    severity_summary = defaultdict(int)

    for finding in findings:
        category_summary[finding.get("category", "unknown")] += finding.get("score_impact", 0)
        severity_summary[finding.get("severity", "info")] += 1

    top_findings = sorted(
        findings,
        key=lambda f: f.get("score_impact", 0),
        reverse=True
    )[:5]

    return {
        "score": final_score,
        "risk_label": risk_label(final_score),
        "total_findings": len(findings),
        "category_summary": dict(category_summary),
        "severity_summary": dict(severity_summary),
        "top_findings": top_findings,
    }