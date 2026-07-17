"""Exception types for the Lucid CES compiler."""

from __future__ import annotations

class LucidCesError(Exception):
    """Base exception class for all lucid_ces errors."""
    pass

class LucidCesParseError(LucidCesError):
    """Raised when parsing of the Lucid graph or labels fails."""
    pass

class LucidCesCompileError(LucidCesError):
    """Raised when semantic compilation fails."""
    pass

class LucidCesValidationError(LucidCesError):
    """Raised when semantic validation fails."""
    pass

class LucidCesDiffError(LucidCesError):
    """Raised when diffing the design IR against a runtime export fails."""
    pass
