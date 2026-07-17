"""Typed exceptions for Lucid core library code."""


class LucidCoreError(Exception):
    """Base exception for Lucid core failures."""


class LucidConfigError(LucidCoreError):
    """Raised when local configuration or credentials are missing."""


class LucidApiError(LucidCoreError):
    """Raised for Lucid API failures."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class LucidParseError(LucidCoreError):
    """Raised when Lucid data cannot be parsed."""


class MermaidParseError(LucidCoreError):
    """Raised when Mermaid input cannot be parsed safely."""

