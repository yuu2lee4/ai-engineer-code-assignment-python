"""Email draft helper stub for the interview task."""
from __future__ import annotations

from typing import Any, Dict


def build_client_followup_email(normalized_payload: Dict[str, Any]) -> str:
    """Summarize the collected payload into a salesperson follow-up email.
    This helper is intentionally left unimplemented for the interview task.
    """
    raise NotImplementedError("Implement the client follow-up email helper.")


__all__ = ["build_client_followup_email"]
