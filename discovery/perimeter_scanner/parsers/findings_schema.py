from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Finding:
    asset_name: str
    target: str
    category: str
    title: str
    severity: str
    score_impact: int
    evidence: str
    recommendation: str
    check_name: str
    status: str = "open"
    port: Optional[int] = None
    protocol: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)