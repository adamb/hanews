import pytest
from pydantic import ValidationError

from hai.llm.schemas import Classification


def test_classification_accepts_valid_payload() -> None:
    result = Classification.model_validate(
        {
            "topics": ["thread", "matter", "devices", "not_a_topic"],
            "relevance_score": 96,
            "novelty_score": 88,
            "importance_score": 71,
            "personal_interest_score": 97,
            "decision": "keep",
            "reason": "New Matter-over-Thread presence sensor.",
            "why_it_matters": "Local low-power presence.",
            "why_you_care": "You run Thread.",
            "claims_to_verify": ["Matter certification"],
            "summary": "Vendor shipped a Thread presence sensor.",
        }
    )
    assert result.topics == ["thread", "matter", "devices"]
    assert result.decision == "keep"


def test_classification_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Classification.model_validate(
            {
                "topics": [],
                "relevance_score": 140,
                "novelty_score": 0,
                "importance_score": 0,
                "personal_interest_score": 0,
                "decision": "keep",
                "reason": "x",
                "why_it_matters": "x",
                "why_you_care": "x",
                "summary": "x",
            }
        )


def test_classification_rejects_freeform_decision() -> None:
    with pytest.raises(ValidationError):
        Classification.model_validate(
            {
                "topics": [],
                "relevance_score": 10,
                "novelty_score": 10,
                "importance_score": 10,
                "personal_interest_score": 10,
                "decision": "maybe",
                "reason": "x",
                "why_it_matters": "x",
                "why_you_care": "x",
                "summary": "x",
            }
        )
