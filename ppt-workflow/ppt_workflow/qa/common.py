from dataclasses import dataclass, field


@dataclass
class CheckResult:
    issues: list[dict] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    evaluated: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def add(self, rule, message, *, severity="error", slide_id=None, element_id=None, bbox=None, **details):
        issue = {"rule": rule, "severity": severity, "message": message,
                 "slide_id": slide_id, "element_id": element_id,
                 "evidence": [message]}
        if bbox is not None:
            issue["bbox_in"] = [round(v, 4) for v in bbox]
        if details:
            issue["details"] = details
        self.issues.append(issue)

    @property
    def status(self):
        if any(i["severity"] == "error" for i in self.issues):
            return "failed"
        return "unverified" if self.unknown else "passed"
