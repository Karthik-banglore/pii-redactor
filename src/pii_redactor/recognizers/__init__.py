"""Build the default recognizer registry."""

from __future__ import annotations

from pii_redactor.recognizers.base import RecognizerRegistry
from pii_redactor.recognizers.indian import (
    AadhaarRecognizer,
    CINRecognizer,
    DINRecognizer,
    GSTRecognizer,
    PANRecognizer,
)
from pii_redactor.recognizers.ner import SpacyNERRecognizer
from pii_redactor.recognizers.patterns import (
    CreditCardRecognizer,
    DOBRecognizer,
    EmailRecognizer,
    IPAddressRecognizer,
    PhoneRecognizer,
    SSNRecognizer,
)
from pii_redactor.recognizers.person_pattern import PersonNameRecognizer


def build_default_registry(spacy_model: str | None = None) -> RecognizerRegistry:
    registry = RecognizerRegistry(
        [
            EmailRecognizer(),
            PhoneRecognizer(),
            SSNRecognizer(),
            CreditCardRecognizer(),
            IPAddressRecognizer(),
            DOBRecognizer(),
            DINRecognizer(),
            PANRecognizer(),
            CINRecognizer(),
            AadhaarRecognizer(),
            GSTRecognizer(),
            PersonNameRecognizer(),
            SpacyNERRecognizer(model=spacy_model),
        ]
    )
    return registry
