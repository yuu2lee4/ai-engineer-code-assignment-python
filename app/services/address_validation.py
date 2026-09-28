"""Address validation helper scaffold for the interview task."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYS_PROMPT = '''
You extract address entities from free-form addresses.

Extract only information explicitly present in the address.

Identify address components such as:
- street
- locality/city
- region/state/province
- postal code
- country
- apartment/unit
- building
- district
- other meaningful address components

Do not invent or infer missing information.

Return JSON only with this schema (braces escaped intentionally):

{{
  "street": string | null,
  "locality": string | null,
  "region": string | null,
  "postal": string | null,
  "country": string | null,
  "additional": object
}}

Preserve the user's original text for extracted values.
'''
class AddressEntities(BaseModel):
    street: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    postal: Optional[str] = None
    country: Optional[str] = None
    additional: Dict[str, str] = Field(default_factory=dict)

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

def extract_address_entities(address: str) -> AddressEntities:
    model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
    model_api_key = os.getenv("MODEL_API_KEY")
    model_base_url = os.getenv("MODEL_BASE_URL")
    temperature = float(os.getenv("MODEL_TEMPERATURE", "0"))
    llm = ChatOpenAI(model=model_name, temperature=temperature, api_key=model_api_key, base_url=model_base_url)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYS_PROMPT),
        ("human", "Extract entities from this address:\n\n{address}"),
    ])
    structured_llm = prompt | llm.with_structured_output(AddressEntities, method="function_calling")
    # structured_llm = prompt | llm
    result = structured_llm.invoke({"address": address})

    return result


def validate_entities(entities: AddressEntities) -> tuple[List[str], List[str]]:
    issues: List[str] = []
    explanations: List[str] = []

    if not entities.street:
        issues.append("missing_street")
        explanations.append("Street address is missing.")

    if not entities.locality:
        issues.append("missing_locality")
        explanations.append("Locality (city/town) is missing.")

    if not entities.postal:
            issues.append("missing_postal")
            explanations.append("Postal code is missing.")

    if not entities.country:
            issues.append("missing_country")
            explanations.append("Country is missing.")

    if entities.postal:
         postal = entities.postal.strip()
         if not re.match(r"^[A-Za-z0-9\s\-]+$", postal):
             issues.append("invalid_postal_format")
             explanations.append("Postal code format is invalid.")

    return issues, explanations
         

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
    address = address_payload.get("line1", "").strip()

    if not address:
        return AddressValidationResult(
            extracted_entities={},
            is_valid=False,
            issues=["missing_address"],
            explanation=["Address is missing"],
        )

    try:
        entities = extract_address_entities(address)
    except Exception as exc:
        logger.error("[address_validation] extraction_failed for address: %s", address, exc_info=True)
        logger.error("[address_validation] exception: %s", str(exc))
        return AddressValidationResult(
            extracted_entities={},
            is_valid=False,
            issues=["extraction_failed"],
            explanation=["Failed to extract address entities."],
        )
    logger.info("[address_validation] extracted_entities=%s", entities.model_dump_json(indent=2))

    issues, explanations = validate_entities(entities)
    extracted: Dict[str, str] = {}

    for field_name in (
        "street",
        "locality",
        "region",
        "postal",
        "country",
    ):
        value = getattr(entities,field_name, None)
        if value:
            extracted[field_name] = value.strip()
    for key, value in entities.additional.items():
        if value:
            extracted[key] = value.strip()

    return AddressValidationResult(
        extracted_entities=extracted,
        is_valid=not issues,
        issues=issues,
        explanation=explanations,
    )

    # raise NotImplementedError("Implement the address validation logic for the interview task.")
