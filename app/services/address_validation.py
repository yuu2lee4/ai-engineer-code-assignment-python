"""Address validation helper scaffold for the interview task."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AddressValidationResult:
    """NER-inspired summary of an address validation attempt.

    Attributes:
        extracted_entities: Canonical address components detected by the validator.
        is_valid: Flag indicating whether the address meets the minimum formatting rules.
        issues: Machine-readable list of validation issue codes/descriptions.
        explanation: Human-friendly sentences that describe the findings.
    """

    extracted_entities: Dict[str, str] = field(default_factory=dict)
    is_valid: bool = False
    issues: List[str] = field(default_factory=list)
    explanation: List[str] = field(default_factory=list)


def validate_address_format(address_payload: Dict[str, Optional[str]]) -> AddressValidationResult:
    """Analyze the normalized address payload and extract structured signals.

    TODO: Implement an address-format validator that uses NER or heuristic rules to:
        * Detect street/locality/postal/country fiedls in the Address
        * Identify malformed components (non-alphanumeric postal codes).
        * Populate AddressValidationResult with extracted entities, issues, and explanations.

    Args:
        address_payload: Address dictionary emitted by the normalization step.

    Returns:
        AddressValidationResult describing detected entities and format problems.
    """

    raise NotImplementedError("Implement the address validation logic for the interview task.")
