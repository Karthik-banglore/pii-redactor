"""Deterministic surrogate tests."""

from pii_redactor.surrogate.provider import SurrogateProvider


def test_same_input_same_output():
    a = SurrogateProvider()
    b = SurrogateProvider()
    name1 = a.fake_for("PERSON", "Rajesh Kushal Hegde")
    name2 = b.fake_for("PERSON", "Rajesh Kushal Hegde")
    assert name1 == name2
    assert name1 != "Rajesh Kushal Hegde"


def test_case_insensitive_cache():
    p = SurrogateProvider()
    assert p.fake_for("PERSON", "Alice") == p.fake_for("PERSON", "alice")


def test_different_types_differ():
    p = SurrogateProvider()
    # Same string under different entity types should not collide
    email = p.fake_for("EMAIL", "test@example.com")
    person = p.fake_for("PERSON", "test@example.com")
    assert email != person
