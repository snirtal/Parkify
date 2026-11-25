"""Idempotent seed for the Skyline Autonomous Hub snapshot.

Source of truth: frontend/src/data/mockParkingData.ts and the default
facility settings in frontend/src/utils/settingsUtils.ts.

Occupancy is not copied onto parking spots. Open sessions, maintenance
reasons, and reservation windows are stored separately.

Assumptions required by the frontend snapshot:
- Timestamps are facility-local naive datetimes (Chicago), matching the
  simulated clock of 2026-11-25 14:24.
- Spots without a gate-entry timestamp start at 08:00 on that date.
- Completed sessions are reconstructed from the exit timestamp and the
  displayed duration: CHI-418M started at 11:58:18, LKS-290A at 09:44:33.
- Vehicle primary keys are stable ids derived from the license plate.
  The frontend does not assign vehicle ids.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from config.database import check_database_connection, create_db_engine
from config.settings import get_settings
from models.orm import (
    Facility,
    FacilitySettings,
    Floor,
    GateActivity,
    ParkingSession,
    ParkingSpot,
    ParkingZone,
    Reservation,
    Vehicle,
)

FACILITY_ID = "facility-skyline"
SIMULATED_DATE = date(2026, 11, 25)
CLOCK = datetime(2026, 11, 25, 14, 24, 0)
DEFAULT_SESSION_START = datetime(2026, 11, 25, 8, 0, 0)

# id, code, deck, row, slot, bay class, hourly rate, sensor note, maintenance
SPOTS: tuple[tuple, ...] = (
    ("bay-p201", "P-201", "P2", "north", 0, "VIP Priority", "6.00", "LiDAR stall telemetry nominal. Cabin thermal sentry active.", None),
    ("bay-p202", "P-202", "P2", "north", 1, "EV Fast 150kW", "4.80", "Bay clear and calibrated. 150kW DC charger standing by for immediate plug-in.", None),
    ("bay-p203", "P-203", "P2", "north", 2, "VIP Priority", "6.00", "License plate recognition armed at Skyline North Gate for incoming reservation.", None),
    ("bay-p204", "P-204", "P2", "north", 3, "VIP Priority", "6.00", "Picked up an impact vibration near your windshield, but optical scan verified zero scratch.", None),
    ("bay-p205", "P-205", "P2", "north", 4, "Standard", "4.20", "Continuous ultrasonic and optical stall monitoring nominal.", None),
    ("bay-p206", "P-206", "P2", "north", 5, "EV Fast 150kW", "4.80", "Active fast-charge session at 84% SoC. Estimated completion in 11 minutes.", None),
    ("bay-p207", "P-207", "P2", "south", 0, "Standard", "4.20", "ANPR verified commuter pass. Telemetry nominal.", None),
    ("bay-p208", "P-208", "P2", "south", 1, "EV Fast 150kW", "4.80", "Bay temporarily locked while induction pad completes automated diagnostics.", "Induction Charger Calibration"),
    ("bay-p209", "P-209", "P2", "south", 2, "Standard", "4.20", "Perimeter motion guard active. Zero anomalies logged.", None),
    ("bay-p210", "P-210", "P2", "south", 3, "Accessible", "3.50", "Wide-clearance accessible stall open near elevator core B.", None),
    ("bay-p211", "P-211", "P2", "south", 4, "EV Fast 150kW", "4.80", "Connected to 150kW DC dispenser • 91% SoC.", None),
    ("bay-p212", "P-212", "P2", "south", 5, "Standard", "4.20", "Optical sentry active. Zero movement alerts.", None),
    ("bay-p101", "P-101", "P1", "north", 0, "EV Fast 150kW", "4.80", "Ultra-fast charger bay ready on Level P1.", None),
    ("bay-p102", "P-102", "P1", "north", 1, "VIP Priority", "6.00", "Full 360 optical sentry active on Level P1.", None),
    ("bay-p103", "P-103", "P1", "north", 2, "Standard", "4.20", "Standard telemetry active. Vehicle locked.", None),
    ("bay-p104", "P-104", "P1", "north", 3, "VIP Priority", "6.00", "Executive reservation hold active.", None),
    ("bay-p105", "P-105", "P1", "north", 4, "Standard", "4.20", "Ultrasonic bay occupancy verified.", None),
    ("bay-p106", "P-106", "P1", "north", 5, "Standard", "4.20", "Floor sensor calibration cycle in progress.", "Surface Sensor Recalibration"),
    ("bay-p107", "P-107", "P1", "south", 0, "Accessible", "3.50", "Priority accessible stall monitored.", None),
    ("bay-p108", "P-108", "P1", "south", 1, "EV Fast 150kW", "4.80", "EV fast charger online and available.", None),
    ("bay-p109", "P-109", "P1", "south", 2, "Standard", "4.20", "Open stall near South Exit ramp.", None),
    ("bay-p110", "P-110", "P1", "south", 3, "Standard", "4.20", "Telemetry nominal.", None),
    ("bay-p111", "P-111", "P1", "south", 4, "EV Fast 150kW", "4.80", "Fast-charge active • 72% SoC.", None),
    ("bay-p112", "P-112", "P1", "south", 5, "Standard", "4.20", "Stall vacant and ready.", None),
)

# plate, model, body, color, accent, driver, initials
VEHICLES: tuple[tuple, ...] = (
    ("CHI-901A", "Aether GT Silhouette", "Coupe", "#7c5ce6", "#c084fc", "Marcus Vance", "MV"),
    ("VEL-204X", "Voedo Horizon 3000 FX", "Sedan", "#f3f4fa", "#a855f7", "Sarah Connor", "SC"),
    ("EVX-882K", "Polestar 4 Performance", "Crossover", "#9ba8c4", "#38bdf8", "Daniel Park", "DP"),
    ("NXT-510P", "Lucid Air Sapphire", "Sedan", "#3b6ee8", "#22d3ee", "Liam Chen", "LC"),
    ("AUD-207G", "Audi e-tron GT RS", "Coupe", "#cbd5e8", "#60a5fa", "Sophia Martinez", "SM"),
    ("SKY-409R", "Rivian R2 Touring", "SUV", "#52789e", "#38bdf8", "Noah Alvarez", "NA"),
    ("PRC-211E", "Porsche Macan Electric", "SUV", "#9d7bea", "#c084fc", "Aria Sterling", "AS"),
    ("GEN-212K", "Genesis GV60 Mint", "Crossover", "#4db6c6", "#22d3ee", "Ethan Cole", "EC"),
    ("PRS-102T", "Taycan Turbo Cross", "Coupe", "#e2e8f5", "#22d3ee", "Claire Bennett", "CB"),
    ("TSL-774M", "Model S Plaid Cobalt", "Sedan", "#4f6ee8", "#a855f7", "Owen Brooks", "OB"),
    ("BMW-105X", "BMW i5 Touring M60", "Sedan", "#b4bed0", "#60a5fa", "Lucas Meyer", "LM"),
    ("MBZ-309E", "EQS SUV Pearl", "SUV", "#eef2fa", "#3b82f6", "Hannah Kim", "HK"),
    ("HYN-618C", "IONIQ 6 Cyber Silver", "Sedan", "#76a4c4", "#22d3ee", "Victor Patel", "VP"),
    ("VLV-111E", "Volvo EX30 Ultra", "Crossover", "#8a6fe8", "#c084fc", "Maya Lin", "ML"),
    ("VIP-700S", None, None, None, None, "Elena Rostova", None),
    ("EXEC-104", None, None, None, None, "Julian Mercer", None),
    ("EVG-202M", None, None, None, None, "Nadia Lin", None),
    ("FLT-108C", None, None, None, None, "David Ross", None),
    ("KRN-101A", None, None, None, None, "Tessa Brooks", None),
    ("ZNT-109X", None, None, None, None, "Omar Haddad", None),
    ("CHI-418M", None, None, None, None, None, None),
    ("LKS-290A", None, None, None, None, None, None),
)

# spot id, plate, paid until HH.MM, monitoring label, alert title or None
ACTIVE_SESSIONS: tuple[tuple, ...] = (
    ("bay-p201", "CHI-901A", "18.30", "Sentry shield active", None),
    ("bay-p204", "VEL-204X", "14.08", "Complete monitoring", "Got a punch"),
    ("bay-p205", "EVX-882K", "19.15", "Complete monitoring", None),
    ("bay-p206", "NXT-510P", "17.50", "EV Charge • 84% SoC", None),
    ("bay-p207", "AUD-207G", "18.45", "Complete monitoring", None),
    ("bay-p209", "SKY-409R", "20.00", "Perimeter guard active", None),
    ("bay-p211", "PRC-211E", "16.55", "EV Charge • 91% SoC", None),
    ("bay-p212", "GEN-212K", "19.30", "Complete monitoring", None),
    ("bay-p102", "PRS-102T", "21.10", "Complete monitoring", None),
    ("bay-p103", "TSL-774M", "18.05", "Sentry mode active", None),
    ("bay-p105", "BMW-105X", "17.25", "Complete monitoring", None),
    ("bay-p107", "MBZ-309E", "17.40", "Complete monitoring", None),
    ("bay-p110", "HYN-618C", "19.45", "Complete monitoring", None),
    ("bay-p111", "VLV-111E", "18.15", "EV Charge • 72% SoC", None),
)

ENTRY_AT = {
    "VEL-204X": datetime(2026, 11, 25, 14, 24, 5),
    "NXT-510P": datetime(2026, 11, 25, 14, 19, 42),
    "EVX-882K": datetime(2026, 11, 25, 14, 6, 51),
}

ALERT_NOTE = (
    "Picked up an impact on your windshield, but do not worry — AI optical "
    "cameras checked it and there is not even a scratch."
)

# id, plate, spot code, date, start, end, status, seeded
RESERVATIONS: tuple[tuple, ...] = (
    ("res-1", "VIP-700S", "P-203", "2026-11-25", "14:00", "16:45", "Active", False),
    ("res-2", "EXEC-104", "P-104", "2026-11-25", "13:30", "16:00", "Active", True),
    ("res-3", "EVG-202M", "P-202", "2026-11-26", "09:00", "12:00", "Scheduled", False),
    ("res-4", "FLT-108C", "P-108", "2026-11-26", "13:00", "16:30", "Scheduled", False),
    ("res-5", "KRN-101A", "P-101", "2026-11-25", "09:00", "11:30", "Completed", False),
    ("res-6", "ZNT-109X", "P-109", "2026-11-25", "11:00", "13:00", "Cancelled", False),
)

# id, time, plate, direction, gate, spot code, status, duration
GATE_LOGS: tuple[tuple, ...] = (
    ("gl-1", "14:24:05", "VEL-204X", "entry", "Skyline North A", "P-204", "Active", None),
    ("gl-2", "14:19:42", "NXT-510P", "entry", "EV HyperGate", "P-206", "Active", None),
    ("gl-3", "14:12:18", "CHI-418M", "exit", "South Express B", "P-202", "Completed", "2h 14m"),
    ("gl-4", "14:06:51", "EVX-882K", "entry", "Skyline North B", "P-205", "Active", None),
    ("gl-5", "13:58:09", "VIP-700S", "entry", "VIP Valet Lane", "P-203", "Reserved", None),
    ("gl-6", "13:49:33", "LKS-290A", "exit", "South Express A", "P-108", "Completed", "4h 05m"),
)

COMPLETED_SESSIONS: tuple[tuple, ...] = (
    (
        "ses-exit-chi-418m",
        "bay-p202",
        "CHI-418M",
        datetime(2026, 11, 25, 11, 58, 18),
        datetime(2026, 11, 25, 14, 12, 18),
    ),
    (
        "ses-exit-lks-290a",
        "bay-p108",
        "LKS-290A",
        datetime(2026, 11, 25, 9, 44, 33),
        datetime(2026, 11, 25, 13, 49, 33),
    ),
)

ZONES = (
    ("z-p2n", "floor-p2", "P2-N", "Deck P2 North — VIP & Sensor", "Monitored Smart Stalls", "Priority", "purple"),
    ("z-p2s", "floor-p2", "P2-S", "Deck P2 South — EV & Accessible", "Fast-Charge & Wide Bays", "EV Charging", "cyan"),
    ("z-p1n", "floor-p1", "P1-N", "Deck P1 North — Executive", "Priority & Commuter Bays", "Commuter", "blue"),
    ("z-p1s", "floor-p1", "P1-S", "Deck P1 South — Express", "High-Turnover Stalls", "Standard", "crimson"),
)


def vehicle_id(plate: str) -> str:
    return f"veh-{plate.lower()}"


def spot_id_by_code() -> dict[str, str]:
    return {code: spot_id for spot_id, code, *_rest in SPOTS}


def _clock(day: str, hhmm: str) -> datetime:
    hours, minutes = hhmm.split(":")
    year, month, day_number = (int(part) for part in day.split("-"))
    return datetime(year, month, day_number, int(hours), int(minutes))


def _paid_until(token: str) -> datetime:
    hours, minutes = token.split(".")
    return datetime(SIMULATED_DATE.year, SIMULATED_DATE.month, SIMULATED_DATE.day, int(hours), int(minutes))


def _merge_all(session: Session) -> None:
    session.merge(
        Facility(
            id=FACILITY_ID,
            name="Skyline Autonomous Hub",
            address="13 Skyline, Chicago, 60611",
            operating_hours="00:00 – 23:59 (24/7)",
            simulated_date=SIMULATED_DATE,
            simulated_time=time(14, 24),
            snapshot_label="Today, 11/25/26 14:24:05 PM",
        )
    )
    session.merge(
        FacilitySettings(
            id="settings-skyline",
            facility_id=FACILITY_ID,
            hourly_rate=Decimal("4.20"),
            daily_max_rate=Decimal("28.00"),
            grace_period_minutes=15,
            ev_surcharge=Decimal("0.60"),
            high_occupancy_alert=True,
            reservation_overstay_alert=True,
            space_fault_alert=True,
        )
    )
    session.merge(Floor(id="floor-p2", facility_id=FACILITY_ID, code="P2", name="Deck P2", level_index=2))
    session.merge(Floor(id="floor-p1", facility_id=FACILITY_ID, code="P1", name="Deck P1", level_index=1))
    for zone_id, floor_id, code, name, category, dashboard, accent in ZONES:
        session.merge(
            ParkingZone(
                id=zone_id,
                floor_id=floor_id,
                code=code,
                name=name,
                category=category,
                dashboard_category=dashboard,
                accent=accent,
            )
        )

    for spot_id, code, deck, row, slot, bay_class, rate, note, maintenance in SPOTS:
        floor_id = "floor-p2" if deck == "P2" else "floor-p1"
        zone_id = {
            ("P2", "north"): "z-p2n",
            ("P2", "south"): "z-p2s",
            ("P1", "north"): "z-p1n",
            ("P1", "south"): "z-p1s",
        }[(deck, row)]
        session.merge(
            ParkingSpot(
                id=spot_id,
                floor_id=floor_id,
                zone_id=zone_id,
                code=code,
                row=row,
                slot_index=slot,
                bay_class=bay_class,
                hourly_rate=Decimal(rate),
                sensor_note=note,
                maintenance_reason=maintenance,
            )
        )

    for plate, model, body, color, accent, driver, initials in VEHICLES:
        session.merge(
            Vehicle(
                id=vehicle_id(plate),
                plate_number=plate,
                model=model,
                body_type=body,
                color_hex=color,
                accent_hex=accent,
                driver_name=driver,
                driver_initials=initials,
            )
        )

    for spot_id, plate, until, monitoring, alert_title in ACTIVE_SESSIONS:
        session.merge(
            ParkingSession(
                id=f"ses-{spot_id}",
                spot_id=spot_id,
                vehicle_id=vehicle_id(plate),
                status="Active",
                started_at=ENTRY_AT.get(plate, DEFAULT_SESSION_START),
                ended_at=None,
                paid_until=_paid_until(until),
                until_caption="Paid parking time",
                monitoring_label=monitoring,
                has_alert=alert_title is not None,
                alert_title=alert_title,
                alert_note=ALERT_NOTE if alert_title else None,
            )
        )

    for session_id, spot_id, plate, started_at, ended_at in COMPLETED_SESSIONS:
        session.merge(
            ParkingSession(
                id=session_id,
                spot_id=spot_id,
                vehicle_id=vehicle_id(plate),
                status="Completed",
                started_at=started_at,
                ended_at=ended_at,
                paid_until=None,
                until_caption=None,
                monitoring_label=None,
                has_alert=False,
            )
        )

    codes = spot_id_by_code()
    for reservation_id, plate, code, day, start, end, status, seeded in RESERVATIONS:
        session.merge(
            Reservation(
                id=reservation_id,
                spot_id=codes[code],
                vehicle_id=vehicle_id(plate),
                status=status,
                starts_at=_clock(day, start),
                ends_at=_clock(day, end),
                is_seeded=seeded,
            )
        )

    for gate_id, stamp, plate, direction, gate_name, code, status, duration in GATE_LOGS:
        hours, minutes, seconds = (int(part) for part in stamp.split(":"))
        session.merge(
            GateActivity(
                id=gate_id,
                spot_id=codes[code],
                vehicle_id=vehicle_id(plate),
                reservation_id="res-1" if gate_id == "gl-5" else None,
                occurred_at=datetime(2026, 11, 25, hours, minutes, seconds),
                direction=direction,
                gate_name=gate_name,
                status=status,
                duration_label=duration,
            )
        )


def seed_database(session: Session, *, commit: bool = True) -> dict[str, int]:
    """Insert the snapshot or update the same primary keys when run again."""
    _merge_all(session)
    session.flush()
    if commit:
        session.commit()

    def count(model: type) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "facilities": count(Facility),
        "floors": count(Floor),
        "zones": count(ParkingZone),
        "spots": count(ParkingSpot),
        "vehicles": count(Vehicle),
        "sessions": count(ParkingSession),
        "reservations": count(Reservation),
        "gate_activities": count(GateActivity),
        "settings": count(FacilitySettings),
    }


def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit(
            "DATABASE_URL is not set. Add the Neon connection string to .env, "
            "then run this command again."
        )
    engine = create_db_engine(settings.database_url)
    check_database_connection(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    with factory() as session:
        counts = seed_database(session)
    engine.dispose()
    print("Seed complete:")
    for name, value in counts.items():
        print(f"  {name}: {value}")


if __name__ == "__main__":
    main()
