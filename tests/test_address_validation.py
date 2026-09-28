"""Placeholder tests for the address validation helper."""

import pytest

from app.services.address_validation import validate_address_format, AddressEntities


def test_valid_address(monkeypatch):
    monkeypatch.setattr(
        "app.services.address_validation.extract_address_entities",
        lambda address: AddressEntities(
            street="123 Main St",
            locality="Los Angeles",
            region="CA",
            postal="90001",
            country="USA",
        ),
    )


    result = validate_address_format({
        "line1": "123 Main St, Los Angeles, CA 90001, USA"
    })

    assert result.is_valid
    assert result.extracted_entities["street"] == "123 Main St"
    assert result.extracted_entities["locality"] == "Los Angeles"
    assert result.extracted_entities["postal"] == "90001"
    assert result.extracted_entities["country"] == "USA"

def test_missing_country():
    result = validate_address_format({
        "line1": "123 Main St, Los Angeles, CA 90001"
    })

    assert not result.is_valid
    assert result.extracted_entities["street"] == "123 Main St"
    assert result.extracted_entities["locality"] == "Los Angeles"
    assert result.extracted_entities["postal"] == "90001"
    assert "missing_country" in result.issues

def test_missing_multi():
    result = validate_address_format({
        "line1": "IL 62704, USA"
    })

    assert not result.is_valid
    assert "missing_street" in result.issues
    assert "missing_locality" in result.issues
    assert result.extracted_entities["postal"] == "62704"
    assert result.extracted_entities["country"] == "USA"