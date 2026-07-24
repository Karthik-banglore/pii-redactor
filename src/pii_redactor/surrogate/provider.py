"""Deterministic hash-seeded surrogate generation."""

from __future__ import annotations

import hashlib
from typing import Dict

from faker import Faker

from pii_redactor.domain.span import EntityType


class SurrogateProvider:
    """
    Same (entity_type, original) → same fake value, across runs and processes.
    """

    def __init__(self, locale: str = "en_IN") -> None:
        self._locale = locale
        self._cache: Dict[str, str] = {}

    def _key(self, entity_type: str, original: str) -> str:
        return f"{entity_type}:{original.strip().lower()}"

    def _faker(self, seed: int) -> Faker:
        fake = Faker(self._locale)
        Faker.seed(seed)
        fake.seed_instance(seed)
        return fake

    def _seed(self, key: str) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def fake_for(self, entity_type: str, original: str) -> str:
        key = self._key(entity_type, original)
        if key in self._cache:
            return self._cache[key]
        fake = self._faker(self._seed(key))
        value = self._generate(fake, entity_type, original)
        self._cache[key] = value
        return value

    def _generate(self, fake: Faker, entity_type: str, original: str) -> str:
        et = entity_type.upper()
        if et == EntityType.PERSON.value:
            return fake.name()
        if et == EntityType.EMAIL.value:
            # Preserve domain shape roughly
            local = fake.user_name().replace(" ", ".")
            domain = fake.free_email_domain()
            return f"{local}@{domain}"
        if et == EntityType.PHONE.value:
            return fake.phone_number()
        if et == EntityType.COMPANY.value:
            return fake.company()
        if et == EntityType.ADDRESS.value:
            return fake.address().replace("\n", ", ")
        if et == EntityType.SSN.value:
            return fake.ssn() if hasattr(fake, "ssn") else "123-45-6789"
        if et == EntityType.CREDIT_CARD.value:
            return fake.credit_card_number()
        if et == EntityType.DOB.value:
            return fake.date_of_birth(minimum_age=25, maximum_age=75).strftime("%d/%m/%Y")
        if et == EntityType.IP_ADDRESS.value:
            return fake.ipv4()
        if et == EntityType.DIN.value:
            return f"{self._seed(self._key(et, original)) % 10**8:08d}"
        if et == EntityType.PAN.value:
            # Fake PAN-shaped string
            n = self._seed(self._key(et, original))
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            return (
                "".join(letters[(n >> (4 * i)) % 26] for i in range(5))
                + f"{n % 10000:04d}"
                + letters[n % 26]
            )
        if et == EntityType.CIN.value:
            return "U99999XX9999XXX999999"
        if et == EntityType.AADHAAR.value:
            n = self._seed(self._key(et, original)) % 10**12
            s = f"{n:012d}"
            return f"{s[:4]} {s[4:8]} {s[8:]}"
        if et == EntityType.GST.value:
            return "27AAAAA0000A1Z5"
        # Fallback
        return f"[REDACTED_{et}]"
