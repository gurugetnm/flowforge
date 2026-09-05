"""Validation result schemas."""

import uuid

from pydantic import BaseModel

from app.engine.validator import Issue, Severity, ValidationReport


class ValidationIssue(BaseModel):
    code: str
    severity: Severity
    message: str
    node_id: uuid.UUID | None = None
    node_label: str | None = None
    field: str | None = None

    @classmethod
    def from_issue(cls, issue: Issue) -> "ValidationIssue":
        return cls(
            code=issue.code.value,
            severity=issue.severity,
            message=issue.message,
            node_id=issue.node_id,
            node_label=issue.node_label,
            field=issue.field,
        )


class ValidationResponse(BaseModel):
    """Whether the workflow can run, and everything worth fixing."""

    is_valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]

    @classmethod
    def from_report(cls, report: ValidationReport) -> "ValidationResponse":
        return cls(
            is_valid=report.is_valid,
            errors=[ValidationIssue.from_issue(issue) for issue in report.errors],
            warnings=[ValidationIssue.from_issue(issue) for issue in report.warnings],
        )
