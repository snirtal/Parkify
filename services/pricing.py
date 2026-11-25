"""Facility pricing.

The frontend displays rates but never calculates a charge. The rules below
are the assumptions used until a pricing policy is specified more narrowly.

- Standard stalls use the facility hourly rate.
- EV Fast 150kW stalls use the facility hourly rate plus the EV surcharge.
- VIP Priority and Accessible stalls keep the rate stored on the stall.
  The settings screen does not replace those two rates.
- A stay within the free grace period, including a stay of exactly that
  length, costs 0. Grace is not subtracted from a longer stay.
- Longer stays are billed in started hours. Each started hour is the
  facility-local ceiling of that calendar day's portion of the stay.
- Each facility-local calendar day is capped by the facility daily maximum,
  then the daily amounts are added. The cap is the one facility setting,
  including for EV and VIP rates.
- `paid_until` is the time shown on an occupied stall. It is not a prepaid
  balance, so it does not reduce the charge.
- The charge is returned to the caller. The schema has no charge column,
  so it is not stored.
- Operating hours are a display string, not a schedule. Pricing does not
  reject time outside that string.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from models.orm import FacilitySettings, ParkingSpot

from services.exceptions import ValidationError
from services.results import ParkingQuote
from services.rules import EV_BAY_CLASS, STANDARD_BAY_CLASS, format_duration

TWOPLACES = Decimal("0.01")
HOUR_MICROSECONDS = 3_600_000_000


def quantize_money(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValidationError("Monetary values must be finite Decimal amounts.")
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class PricingService:
    """Calculate displayed hourly rates and a stay's charge."""

    def displayed_hourly_rate(self, spot: ParkingSpot, settings: FacilitySettings) -> Decimal:
        if spot.bay_class == EV_BAY_CLASS:
            return quantize_money(settings.hourly_rate + settings.ev_surcharge)
        if spot.bay_class == STANDARD_BAY_CLASS:
            return quantize_money(settings.hourly_rate)
        return quantize_money(spot.hourly_rate)

    def quote(
        self,
        spot: ParkingSpot,
        settings: FacilitySettings,
        started_at: datetime,
        ended_at: datetime,
    ) -> ParkingQuote:
        if started_at.tzinfo is not None or ended_at.tzinfo is not None:
            raise ValidationError(
                "Parking times must be facility-local values without a time zone."
            )
        if ended_at < started_at:
            raise ValidationError("The parking session end must not be earlier than the start.")

        rate = self.displayed_hourly_rate(spot, settings)
        daily_maximum = quantize_money(settings.daily_max_rate)
        interval = ended_at - started_at
        grace = timedelta(minutes=int(settings.grace_period_minutes))
        duration_seconds = int(interval.total_seconds())
        if interval <= grace:
            return ParkingQuote(
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=duration_seconds,
                duration_label=format_duration(interval),
                hourly_rate=rate,
                billable_hours=0,
                amount=Decimal("0.00"),
                grace_applied=True,
                daily_maximum=daily_maximum,
            )

        billable_hours = 0
        amount = Decimal("0.00")
        for day_start, day_end in _local_days(started_at, ended_at):
            hours = _started_hours(day_start, day_end)
            billable_hours += hours
            raw = quantize_money(rate * hours)
            if raw > daily_maximum:
                raw = daily_maximum
            amount += raw
        return ParkingQuote(
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            duration_label=format_duration(interval),
            hourly_rate=rate,
            billable_hours=billable_hours,
            amount=quantize_money(amount),
            grace_applied=False,
            daily_maximum=daily_maximum,
        )


def _started_hours(start: datetime, end: datetime) -> int:
    microseconds = (end - start) // timedelta(microseconds=1)
    if microseconds <= 0:
        return 0
    return (microseconds + HOUR_MICROSECONDS - 1) // HOUR_MICROSECONDS


def _local_days(start: datetime, end: datetime):
    cursor = start
    while cursor < end:
        next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min)
        slice_end = min(end, next_midnight)
        yield cursor, slice_end
        cursor = slice_end
