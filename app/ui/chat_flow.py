"""Streamlit chat workflow for the intake review task."""
from __future__ import annotations

import json
import logging
import os
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.services.address_validation import AddressValidationResult, validate_address_format

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts" / "text" / "contract"
_INGEST_PROMPT: Optional[ChatPromptTemplate] = None
_INGEST_CHAIN = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_prompt_text(name: str) -> str:
    path = PROMPT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text().strip()


def _get_ingest_chain():
    global _INGEST_CHAIN, _INGEST_PROMPT
    if _INGEST_CHAIN is None:
        system_prompt = _load_prompt_text("chat_ingest_system.txt")
        human_prompt = _load_prompt_text("chat_ingest_human.txt")
        logger.info("[chat_ingest] system prompt:\n%s", system_prompt)
        logger.info("[chat_ingest] human prompt:\n%s", human_prompt)
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        model_name = os.getenv("CHAT_INGEST_MODEL", "gpt-4o-mini")
        temperature = float(os.getenv("CHAT_INGEST_TEMPERATURE", "0"))
        llm = ChatOpenAI(model=model_name, temperature=temperature)
        _INGEST_PROMPT = prompt
        _INGEST_CHAIN = prompt | llm | StrOutputParser()
    return _INGEST_CHAIN


@dataclass
class ConversationTurn:
    speaker: str
    message: str
    metadata: Dict[str, str] = field(default_factory=dict)


class ChatReviewSession:
    """State container for the Streamlit chatbot experience."""

    def __init__(self) -> None:
        self.turns: List[ConversationTurn] = []
        self.normalized_payload: Dict[str, object] = {
            "account_name": "",
            "primary_contact": "",
            "deal_notes": "",
            "address": ""
        }
        self.address_result: Optional[AddressValidationResult] = None
        self.review_state: Optional[Dict[str, str]] = None
        self.review_error: Optional[str] = None
        self.last_ingest_payload: Optional[Dict[str, object]] = None
        self.last_ingest_response: Optional[str] = None
        self.last_ingest_parsed: Optional[Dict[str, object]] = None

    def add_user_message(self, text: str) -> None:
        self.turns.append(ConversationTurn(speaker="user", message=text))

    def add_agent_message(self, text: str, metadata: Optional[Dict[str, str]] = None) -> None:
        self.turns.append(ConversationTurn(speaker="agent", message=text, metadata=metadata or {}))

    def ensure_started(self) -> None:
        if self.turns:
            return
        self.add_agent_message(
            "Hi! I need four things: **Account**, **Contact**, **Address**, and **Notes**. "
            "Share them in any order (e.g. `Account is Globex`, `Address is 742 Evergreen Terrace, Springfield, IL 62704, USA`)."
        )

    def handle_user_response(self, text: str) -> None:
        self.review_state = None
        self.review_error = None
        self.add_user_message(text)
        before = self._snapshot()
        updated = self._maybe_ingest_json(text)
        if not updated:
            parsed = self._run_ingest_chain(text)
            if parsed is None:
                self.add_agent_message(
                    "I couldn't parse that message. Please rephrase or confirm your LLM credentials are configured."
                )
                return
            self._apply_ingest_result(parsed)
        acknowledgement = self._build_acknowledgement(before, self.normalized_payload)
        self._validate_address()
        missing = self.missing_sections()
        reply_parts: List[str] = []
        if acknowledgement:
            reply_parts.append("Captured:\n" + acknowledgement)
        else:
            reply_parts.append(
                "I didn't detect new details. Try phrases like `Account is ...`, `Contact is ...`, `Address is ...`, or `Notes`."
            )
        if missing:
            reply_parts.append("Still need: " + ", ".join(missing))
        else:
            reply_parts.append("All sections captured. Type **Confirm** to generate the review summary.")
        self.add_agent_message("\n\n".join(reply_parts))

    def _run_ingest_chain(self, text: str) -> Optional[Dict[str, object]]:
        chain = _get_ingest_chain()
        prompt = _INGEST_PROMPT
        try:
            payload = {
                "current_payload": json.dumps(self.normalized_payload, indent=2),
                "missing_sections": ", ".join(self.missing_sections()) or "none",
                "user_message": text,
            }
            self.last_ingest_payload = payload
            if prompt is not None:
                rendered = prompt.format_messages(**payload)
                rendered_text = "\n\n".join(
                    f"{message.type}: {getattr(message, 'content', '')}" for message in rendered
                )
                logger.info("[chat_ingest] formatted prompt:\n%s", rendered_text)
            response_text = chain.invoke(payload)
            self.last_ingest_response = response_text
            parsed = json.loads(response_text)
            self.last_ingest_parsed = parsed
            logger.info("[chat_ingest] payload=%s", json.dumps(payload, indent=2))
            logger.info("[chat_ingest] response=%s", response_text)
            logger.info("[chat_ingest] parsed=%s", json.dumps(parsed, indent=2))
        except Exception as exc:  # pragma: no cover - network/LLM issues
            self.review_error = f"ingest_failed: {exc}"
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    def _apply_ingest_result(self, parsed: Dict[str, object]) -> None:
        for field in ("account_name", "primary_contact", "deal_notes"):
            value = parsed.get(field)
            if isinstance(value, str) and value.strip():
                self.normalized_payload[field] = value.strip()
        address_updates = parsed.get("address", {})
        if isinstance(address_updates, dict):
            address = self._ensure_address()
            for key, value in address_updates.items():
                if isinstance(value, str) and value.strip():
                    address[key] = value.strip()

    def _maybe_ingest_json(self, text: str) -> bool:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict):
            return False
        self._apply_ingest_result(payload)
        return True

    def missing_sections(self) -> List[str]:
        missing: List[str] = []
        if not str(self.normalized_payload.get("account_name", "")).strip():
            missing.append("Account")
        if not str(self.normalized_payload.get("primary_contact", "")).strip():
            missing.append("Contact")
        address = self._ensure_address()
        if not str(address.get("line1", "")).strip():
            missing.append("Address")
        if not str(self.normalized_payload.get("deal_notes", "")).strip():
            missing.append("Notes")
        return missing

    def _validate_address(self) -> None:
        address = self._ensure_address()
        if not address.get("line1"):
            return
        try:
            self.address_result = validate_address_format(address)
        except NotImplementedError:
            self.address_result = None

    def is_ready_for_review(self) -> bool:
        return len(self.missing_sections()) == 0

    def store_review_result(self, state: Dict[str, str], message: str) -> None:
        self.review_state = state
        self.add_agent_message(message, metadata={"type": "review_result"})

    def _build_acknowledgement(self, before: Dict[str, object], after: Dict[str, object]) -> str:
        lines: List[str] = []
        if before.get("account_name") != after.get("account_name") and after.get("account_name"):
            lines.append(f"- Account: **{after['account_name']}**")
        if before.get("primary_contact") != after.get("primary_contact") and after.get("primary_contact"):
            lines.append(f"- Contact: **{after['primary_contact']}**")
        if before.get("deal_notes") != after.get("deal_notes") and after.get("deal_notes"):
            lines.append("- Notes updated.")
        before_address = before.get("address", {})
        after_address = after.get("address", {})
        if before_address != after_address and isinstance(after_address, dict) and after_address.get("line1"):
            lines.append("- Address captured/updated.")
        return "\n".join(lines)

    def _ensure_address(self) -> Dict[str, str]:
        address = self.normalized_payload.setdefault("address", {})
        if not isinstance(address, dict):
            address = {}
            self.normalized_payload["address"] = address
        return address  # type: ignore[return-value]

    def _snapshot(self) -> Dict[str, object]:
        return deepcopy(self.normalized_payload)


__all__ = ["ChatReviewSession", "ConversationTurn"]
