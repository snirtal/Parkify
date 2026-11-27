"""Pending reservation requests, approval, and the simulator identity."""

from __future__ import annotations

import threading
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.orm import Facility, Floor, ParkingSpot, ParkingZone, User
from services.exceptions import ConflictError
from services.factory import build_services
from services.support import FixedClock, default_id
from services.unit_of_work import SqlAlchemyUnitOfWork
from tests.http_auth import operator_client

START = "2026-11-25T15:00:00"
WINDOW = {"plate_number": "LX-REQ1", "bay_class": "Standard", "starts_at": START, "duration_minutes": 90}


def _create(client, **overrides):
    body = dict(WINDOW)
    body.update(overrides)
    return client.post("/api/facilities/facility-skyline/reservation-requests", json=body)


def test_anonymous_callers_cannot_create_or_decide(client):
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/facilities/facility-skyline/reservation-requests", json=WINDOW).status_code == 401
    assert client.post("/api/facilities/facility-skyline/reservation-requests/missing/approval").status_code == 401


def test_simulator_can_operate_the_gate_but_not_decide(db_session):
    simulator = operator_client(db_session, role="simulator", email="simulator-req@parkify.test")
    admin = operator_client(db_session, role="admin", email="admin-req@parkify.test")

    occupancy = simulator.get("/api/facilities/facility-skyline/occupancy")
    assert occupancy.status_code == 200
    assert "hourly_rate" not in occupancy.get_json()["spots"][0]

    sessions = simulator.get("/api/facilities/facility-skyline/sessions")
    assert sessions.status_code == 200
    assert all("paid_until" not in item for item in sessions.get_json()["items"])

    created = _create(simulator)
    assert created.status_code == 201
    request_id = created.get_json()["id"]
    assert simulator.post(f"/api/facilities/facility-skyline/reservation-requests/{request_id}/approval").status_code == 403
    assert simulator.post(f"/api/facilities/facility-skyline/reservation-requests/{request_id}/rejection").status_code == 403
    assert simulator.get("/api/facilities/facility-skyline/settings").status_code == 403
    assert simulator.post("/api/facilities/facility-skyline/quotes", json={"plate_number": "LX-REQ1"}).status_code == 403

    spot = next(
        item["code"]
        for item in admin.get("/api/facilities/facility-skyline/occupancy").get_json()["spots"]
        if item["status"] == "available"
    )
    entered = simulator.post(
        "/api/facilities/facility-skyline/entries",
        json={"plate_number": "LX-GATE1", "spot_code": spot},
    )
    assert entered.status_code == 201
    exited = simulator.post(
        "/api/facilities/facility-skyline/exits",
        json={"plate_number": "LX-GATE1"},
    )
    assert exited.status_code == 200
    assert "quote" not in exited.get_json()
    assert "amount" not in exited.get_json()


def test_pending_request_does_not_hold_a_spot_until_approval(db_session):
    simulator = operator_client(db_session, role="simulator", email="simulator-hold@parkify.test")
    employee = operator_client(db_session, role="employee", email="employee-hold@parkify.test")
    before = employee.get("/api/facilities/facility-skyline/occupancy").get_json()["spots"]
    created = _create(simulator, plate_number="LX-HOLD1", starts_at="2026-11-25T14:00:00", duration_minutes=120)
    assert created.status_code == 201
    after = employee.get("/api/facilities/facility-skyline/occupancy").get_json()["spots"]
    assert [item["status"] for item in after] == [item["status"] for item in before]

    listed = employee.get("/api/facilities/facility-skyline/reservation-requests?status=Pending")
    assert listed.status_code == 200
    assert any(item["plate_number"] == "LX-HOLD1" and item["spot_code"] is None for item in listed.get_json()["items"])
    assert employee.get("/api/facilities/facility-skyline/reservations").status_code == 403
    assert employee.post("/api/facilities/facility-skyline/reservation-requests", json=WINDOW).status_code == 403

    approved = employee.post(f"/api/facilities/facility-skyline/reservation-requests/{created.get_json()['id']}/approval")
    assert approved.status_code == 200
    body = approved.get_json()
    assert body["status"] == "Approved"
    assert body["spot_code"]
    assert "amount" not in body
    repeated = employee.post(f"/api/facilities/facility-skyline/reservation-requests/{body['id']}/approval")
    assert repeated.status_code == 409
    assert repeated.get_json()["error"]["code"] == "reservation_request_closed"


def test_employee_rejection_and_duplicate_requests(db_session):
    simulator = operator_client(db_session, role="simulator", email="simulator-dup@parkify.test")
    employee = operator_client(db_session, role="employee", email="employee-dup@parkify.test")
    first = _create(simulator, plate_number="LX-DUP1")
    assert first.status_code == 201
    duplicate = _create(simulator, plate_number="LX-DUP1")
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "duplicate_request"
    rejected = employee.post(f"/api/facilities/facility-skyline/reservation-requests/{first.get_json()['id']}/rejection")
    assert rejected.status_code == 200
    assert rejected.get_json()["status"] == "Rejected"
    again = employee.post(f"/api/facilities/facility-skyline/reservation-requests/{first.get_json()['id']}/approval")
    assert again.status_code == 409


def test_admin_can_still_book_directly_and_can_approve(db_session):
    admin = operator_client(db_session, role="admin", email="admin-book@parkify.test")
    simulator = operator_client(db_session, role="simulator", email="simulator-book@parkify.test")
    spot = next(
        item["code"]
        for item in admin.get("/api/facilities/facility-skyline/occupancy").get_json()["spots"]
        if item["status"] == "available" and item["bay_class"] == "Standard"
    )
    direct = admin.post(
        "/api/facilities/facility-skyline/reservations",
        json={
            "plate_number": "LX-DIR1",
            "spot_code": spot,
            "starts_at": "2026-11-25T18:00:00",
            "ends_at": "2026-11-25T19:00:00",
        },
    )
    assert direct.status_code == 201
    created = _create(simulator, plate_number="LX-ADM1", starts_at="2026-11-25T19:00:00", duration_minutes=60)
    approved = admin.post(f"/api/facilities/facility-skyline/reservation-requests/{created.get_json()['id']}/approval")
    assert approved.status_code == 200


def test_approval_fails_when_the_bay_class_is_full(db_session):
    admin = operator_client(db_session, role="admin", email="admin-full@parkify.test")
    simulator = operator_client(db_session, role="simulator", email="simulator-full@parkify.test")
    spots = admin.get("/api/facilities/facility-skyline/occupancy").get_json()["spots"]
    accessible = [item for item in spots if item["bay_class"] == "Accessible"]
    assert accessible
    for index, spot in enumerate(accessible):
        if spot["status"] == "unavailable":
            continue
        admin.post(
            "/api/facilities/facility-skyline/reservations",
            json={
                "plate_number": f"LX-FULL{index}",
                "spot_code": spot["code"],
                "starts_at": "2026-11-25T20:00:00",
                "ends_at": "2026-11-25T21:00:00",
            },
        )
    created = _create(
        simulator,
        plate_number="LX-NOBAY",
        bay_class="Accessible",
        starts_at="2026-11-25T20:00:00",
        duration_minutes=60,
    )
    assert created.status_code == 201
    decision = admin.post(f"/api/facilities/facility-skyline/reservation-requests/{created.get_json()['id']}/approval")
    assert decision.status_code == 409
    assert decision.get_json()["error"]["code"] == "insufficient_availability"


def test_an_approved_vehicle_can_arrive_and_depart(db_session):
    admin = operator_client(db_session, role="admin", email="admin-arrive@parkify.test")
    simulator = operator_client(db_session, role="simulator", email="simulator-arrive@parkify.test")
    created = _create(
        simulator,
        plate_number="LX-ARV1",
        starts_at="2026-11-25T14:00:00",
        duration_minutes=120,
    )
    approved = admin.post(f"/api/facilities/facility-skyline/reservation-requests/{created.get_json()['id']}/approval")
    assert approved.status_code == 200
    spot = approved.get_json()["spot_code"]
    entered = simulator.post(
        "/api/facilities/facility-skyline/entries",
        json={"plate_number": "LX-ARV1", "spot_code": spot},
    )
    assert entered.status_code == 201
    exited = simulator.post(
        "/api/facilities/facility-skyline/exits",
        json={"plate_number": "LX-ARV1"},
    )
    assert exited.status_code == 200
    assert "quote" not in exited.get_json()


def test_two_approvals_cannot_take_the_last_matching_spot(migrated_engine):
    facility_id = "facility-req-conc"
    _cleanup_request_race(migrated_engine)
    approver_id = _setup_request_race(migrated_engine, facility_id)
    services = build_services(
        lambda: SqlAlchemyUnitOfWork(Session(bind=migrated_engine), close_session=True),
        clock=FixedClock(datetime(2026, 11, 25, 14, 24)),
        ids=default_id,
    )
    first = services.reservation_requests.create_request(
        facility_id, "LX-CONA", "Standard", datetime(2026, 11, 25, 18, 0), datetime(2026, 11, 25, 19, 0)
    )
    second = services.reservation_requests.create_request(
        facility_id, "LX-CONB", "Standard", datetime(2026, 11, 25, 18, 0), datetime(2026, 11, 25, 19, 0)
    )
    results: list[str] = []
    barrier = threading.Barrier(2)

    def attempt(request_id: str) -> None:
        local = build_services(
            lambda: SqlAlchemyUnitOfWork(Session(bind=migrated_engine), close_session=True, lock_timeout_ms=15000),
            clock=FixedClock(datetime(2026, 11, 25, 14, 24)),
            ids=default_id,
        )
        try:
            barrier.wait(20)
            local.reservation_requests.approve_request(facility_id, request_id, actor_id=approver_id)
            results.append("ok")
        except ConflictError:
            results.append("conflict")
        except Exception as exc:
            results.append(type(exc).__name__)

    threads = [threading.Thread(target=attempt, args=(item.id,)) for item in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(40)
    try:
        assert sorted(results) == ["conflict", "ok"]
    finally:
        _cleanup_request_race(migrated_engine)


def _setup_request_race(engine, facility_id: str) -> str:
    session = Session(bind=engine, autoflush=False, expire_on_commit=False)
    approver = User(
        id="user-req-conc",
        email="approver-req-conc@parkify.test",
        full_name="Approver",
        password_hash="x" * 20,
        role="admin",
    )
    session.add(approver)
    session.add(
        Facility(
            id=facility_id,
            name="Request Concurrency",
            address="1 Isolated Way",
            operating_hours="24/7",
            simulated_date=date(2026, 11, 25),
            simulated_time=time(14, 24),
            snapshot_label="request-concurrency",
        )
    )
    session.add(Floor(id="floor-req-conc", facility_id=facility_id, code="R9", name="Request deck", level_index=9))
    session.add(
        ParkingZone(
            id="zone-req-conc",
            floor_id="floor-req-conc",
            code="R-REQ",
            name="Request zone",
            category="Test",
            dashboard_category="Standard",
            accent="blue",
        )
    )
    session.add(
        ParkingSpot(
            id="spot-req-conc",
            floor_id="floor-req-conc",
            zone_id="zone-req-conc",
            code="RQ-1",
            row="north",
            slot_index=0,
            bay_class="Standard",
            hourly_rate=Decimal("4.20"),
            sensor_note="request concurrency",
        )
    )
    session.commit()
    session.close()
    return approver.id


def _cleanup_request_race(engine) -> None:
    statements = (
        "DELETE FROM reservation_requests WHERE facility_id = 'facility-req-conc'",
        "DELETE FROM reservations WHERE spot_id = 'spot-req-conc'",
        "DELETE FROM parking_sessions WHERE spot_id = 'spot-req-conc'",
        "DELETE FROM gate_activities WHERE spot_id = 'spot-req-conc'",
        "DELETE FROM parking_spots WHERE id = 'spot-req-conc'",
        "DELETE FROM parking_zones WHERE id = 'zone-req-conc'",
        "DELETE FROM floors WHERE id = 'floor-req-conc'",
        "DELETE FROM facility_settings WHERE facility_id = 'facility-req-conc'",
        "DELETE FROM vehicles WHERE plate_number IN ('LX-CONA', 'LX-CONB')",
        "DELETE FROM users WHERE id = 'user-req-conc'",
        "DELETE FROM facilities WHERE id = 'facility-req-conc'",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
