"""The facility id is configuration, and the seeded default stays in place."""

from config.facility import DEFAULT_FACILITY_ID, configured_facility_id


def test_the_seeded_facility_remains_the_default(monkeypatch):
    monkeypatch.delenv("FACILITY_ID", raising=False)
    assert DEFAULT_FACILITY_ID == "facility-skyline"
    assert configured_facility_id() == "facility-skyline"


def test_a_blank_facility_override_keeps_the_default(monkeypatch):
    monkeypatch.setenv("FACILITY_ID", "   ")
    assert configured_facility_id() == "facility-skyline"


def test_facility_id_can_be_configured(monkeypatch):
    monkeypatch.setenv("FACILITY_ID", " facility-other ")
    assert configured_facility_id() == "facility-other"
