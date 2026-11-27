"""Findings and the exception that stops a build.

Every check reports Findings with a fixed severity set in code (spec section 7):
BLOCKING stops the build and nothing is written; WARNING is reported only.
"""
from dataclasses import dataclass, field

BLOCKING = "blocking"
WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    code: str          # stable identifier, for example "V1.unknown-field"
    severity: str      # BLOCKING or WARNING
    message: str       # what is wrong and what to do next
    where: str = ""    # book, file and item, for example "munazara-rashidiya: book.json: theme.light"

    def __str__(self):
        loc = f"{self.where}: " if self.where else ""
        return f"[{self.severity.upper()}] {self.code}: {loc}{self.message}"


class BuildStopped(Exception):
    """Raised when a stage has blocking findings. Carries every finding of that stage."""

    def __init__(self, stage, findings):
        self.stage = stage
        self.findings = list(findings)
        super().__init__(f"build stopped at stage '{stage}':\n" + "\n".join(str(f) for f in self.findings))


@dataclass
class Report:
    findings: list = field(default_factory=list)

    def add(self, finding):
        self.findings.append(finding)

    def extend(self, findings):
        self.findings.extend(findings)

    @property
    def blocking(self):
        return [f for f in self.findings if f.severity == BLOCKING]

    @property
    def warnings(self):
        return [f for f in self.findings if f.severity == WARNING]

    def stop_if_blocking(self, stage, new_findings):
        """Record new findings; raise BuildStopped if any of them blocks."""
        new_findings = list(new_findings)
        self.extend(new_findings)
        blocking = [f for f in new_findings if f.severity == BLOCKING]
        if blocking:
            raise BuildStopped(stage, new_findings)
