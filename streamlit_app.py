"""Streamlit chatbot for the contract intake review exercise."""
from __future__ import annotations

import json

import streamlit as st

from app.ui.chat_flow import ChatReviewSession

st.set_page_config(page_title="Contract Intake Agent", page_icon="🤖")
st.title("Contract Intake Review")

if "chat_session" not in st.session_state:
    st.session_state.chat_session = ChatReviewSession()

session: ChatReviewSession = st.session_state.chat_session
session.ensure_started()


with st.sidebar:
    if st.button("Reset conversation", use_container_width=True):
        st.session_state.chat_session = ChatReviewSession()
        st.rerun()
    st.markdown("### Data collection status")
    missing = session.missing_sections()
    if missing:
        st.warning("Missing: " + ", ".join(missing))
    else:
        st.success("All sections captured (type 'Confirm' to run review).")
    st.markdown("### Address validation")
    if session.address_result:
        if session.address_result.is_valid:
            st.success("Address format looks complete.")
        else:
            st.error("Address issues detected.")
        for line in session.address_result.explanation:
            st.write(f"- {line}")
    else:
        st.info("Address validation will run once you provide the address (and implement the validator).")
    if session.review_error:
        st.error(f"Ingestion error: {session.review_error}")

st.caption("Provide the deal details via chat. Type 'Confirm' to generate the review summary once everything is captured.")

for turn in session.turns:
    with st.chat_message(turn.speaker):
        st.markdown(turn.message)

user_input = st.chat_input("Type your response")
if user_input:
    normalized = user_input.strip()
    if normalized.lower() == "confirm":
        session.add_user_message(user_input)
        if session.is_ready_for_review():
            session.store_review_result(
                session.normalized_payload,
                "Collected payload:\n```\n" + json.dumps(session.normalized_payload, indent=2) + "\n```",
            )
        else:
            session.add_agent_message("Still missing details. Share Account, Contact, Address, or Notes before confirming.")
        st.rerun()
    else:
        session.handle_user_response(user_input)
        st.rerun()

if session.review_state:
    with st.expander("Latest LangGraph output", expanded=False):
        st.code(json.dumps(session.review_state, indent=2))
