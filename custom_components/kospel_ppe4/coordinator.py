"""DataUpdateCoordinator for Kospel PPE4.M."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import KospelApiClient, KospelApiError, KospelConnectionError
from .const import (
    DAILY_HISTORY_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERROR_WORD1_BITS,
    ERROR_WORD2_BITS,
)

_LOGGER = logging.getLogger(__name__)


# ---- Helpers ----

def _div10(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return int(raw) / 10.0
    except (ValueError, TypeError):
        return None


def _intval(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _get(d: dict, key: str | int) -> Any:
    """Get a register value from a dict, trying both str and int keys."""
    v = d.get(str(key))
    if v is not None:
        return v
    return d.get(int(key)) if isinstance(key, str) and key.isdigit() else None


def _32bit(d: dict, low_reg: int) -> int:
    """Combine two consecutive 16-bit registers into a 32-bit value.

    Formula: (reg[low+1] << 16) | reg[low]
    """
    low = _intval(_get(d, str(low_reg))) or 0
    high = _intval(_get(d, str(low_reg + 1))) or 0
    return (high << 16) | (low & 0xFFFF)


def _decode_errors(word: int, bit_map: dict[int, tuple[str, str]]) -> list[str]:
    """Decode a 32-bit error/warning word into a list of active error strings."""
    errors = []
    for bit, (code, desc) in bit_map.items():
        if word & (1 << bit):
            errors.append(f"{code}: {desc}")
    return errors


# ---- Data Classes ----

@dataclass
class KospelData:
    """All data from the PPE4.M."""

    # Live temperatures (°C)
    inlet_temp: float | None = None
    outlet_temp: float | None = None
    aux_temp: float | None = None
    current_setpoint: float | None = None
    target_temp: float | None = None
    max_allowed_temp: float | None = None
    hw_max_temp: float | None = None

    # Temperature limits from /api/1014/8
    temp_min: float = 30.0
    temp_max: float = 60.0

    # Live flow/power
    flow_rate: float | None = None
    power_w: int | None = None          # Current power in watts
    power_kw: float | None = None       # Current power in kW
    rated_power_w: int | None = None
    selected_power_w: int | None = None
    selected_power_kw: float | None = None
    min_flow: int | None = None

    # Status — 32-bit decoded
    status_word: int = 0
    is_heating: bool = False
    is_power_limited: bool = False
    is_temp_locked: bool = False

    # Errors — 32-bit decoded
    error_word1: int = 0
    error_word2: int = 0
    has_errors: bool = False
    has_warnings: bool = False
    active_errors: list[str] = field(default_factory=list)
    active_warnings: list[str] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0

    # Heating
    heating_stage: int | None = None

    # Device datetime
    dt_year: int | None = None
    dt_month: int | None = None
    dt_day: int | None = None
    dt_dow: int | None = None
    dt_hour: int | None = None
    dt_minute: int | None = None
    dt_second: int | None = None

    # Profiles (°C)
    profile1_temp: float | None = None
    profile2_temp: float | None = None
    profile3_temp: float | None = None
    mode_flag: int | None = None

    # Energy stats (kWh)
    energy_today_kwh: float = 0.0
    energy_yesterday_kwh: float = 0.0
    energy_week_kwh: float = 0.0
    energy_month_kwh: float = 0.0
    energy_year_kwh: float = 0.0
    energy_lifetime_kwh: float = 0.0

    # Water stats (liters)
    water_today_l: float = 0.0
    water_yesterday_l: float = 0.0
    water_week_l: float = 0.0
    water_month_l: float = 0.0
    water_year_l: float = 0.0
    water_lifetime_l: float = 0.0

    # Raw settings for write-back
    raw_temp_settings: dict[str, Any] = field(default_factory=dict)


class KospelDataCoordinator(DataUpdateCoordinator[KospelData]):
    """Single coordinator polling all endpoints every cycle."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: KospelApiClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> KospelData:
        try:
            results = await asyncio.gather(
                self.client.async_get_temp_limits(),
                self.client.async_get_live_data(),
                self.client.async_get_temperature(),
                self.client.async_get_energy_daily(),
                self.client.async_get_energy_totals(),
                self.client.async_get_water_daily(),
                self.client.async_get_water_totals(),
                return_exceptions=True,
            )
        except KospelConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err

        limits = results[0] if not isinstance(results[0], Exception) else {}
        live = results[1] if not isinstance(results[1], Exception) else {}
        temp = results[2] if not isinstance(results[2], Exception) else {}
        e_daily = results[3] if not isinstance(results[3], Exception) else {}
        e_totals = results[4] if not isinstance(results[4], Exception) else {}
        w_daily = results[5] if not isinstance(results[5], Exception) else {}
        w_totals = results[6] if not isinstance(results[6], Exception) else {}

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                _LOGGER.debug("Fetch %d failed: %s", i, r)

        if not live and not temp:
            raise UpdateFailed("Core API endpoints failed")

        # ---- Temperature limits from /api/1014/8 ----
        temp_min = (_intval(_get(limits, "1014")) or 300) / 10.0
        temp_max = (_intval(_get(limits, "1015")) or 600) / 10.0

        # ---- Status word: (reg1129 << 16) | reg1128 ----
        status_word = _32bit(live, 1128)
        is_power_limited = bool(status_word & (1 << 5))
        is_temp_locked = bool(status_word & (1 << 11))

        # ---- Error words ----
        error_word1 = _32bit(live, 1130)
        error_word2 = _32bit(live, 1132)
        active_errors = _decode_errors(error_word1, ERROR_WORD1_BITS)
        active_warnings = _decode_errors(error_word2, ERROR_WORD2_BITS)

        # ---- Heating ----
        heating_stage = _intval(_get(live, "1141"))
        is_heating = heating_stage is not None and heating_stage > 0

        # ---- Power ----
        power_w = _intval(_get(live, "1138"))
        selected_power_w = _intval(_get(live, "1144"))

        # ---- Energy daily ----
        energy_today = _32bit(e_daily, 1450)
        energy_yesterday = _32bit(e_daily, 1452)

        # ---- Water daily ----
        water_today = _32bit(w_daily, 1578)
        water_yesterday = _32bit(w_daily, 1580)

        # ---- Energy period totals (from /api/1500/48) ----
        # Layout confirmed with differentiated values (Mar 2026):
        #   +12/+13 (1512/1513) = This Week
        #   +14/+15 (1514/1515) = This Year
        #   +16/+17 (1516/1517) = Last Year
        #   +22/+23 (1522/1523) = Last Month
        #   +24/+25 (1524/1525) = This Month
        energy_week = _32bit(e_totals, 1512)
        energy_year = _32bit(e_totals, 1514)
        energy_month = _32bit(e_totals, 1524)
        energy_last_month = _32bit(e_totals, 1522)
        # Lifetime not yet identified — use year as best approximation
        energy_lifetime = energy_year

        # ---- Water period totals (from /api/1628/48) ----
        # Same layout as energy (confirmed Mar 2026):
        #   +12/+13 (1640/1641) = This Week
        #   +14/+15 (1642/1643) = This Year
        #   +16/+17 (1644/1645) = Last Year
        #   +22/+23 (1650/1651) = Last Month
        #   +24/+25 (1652/1653) = This Month
        water_week = _32bit(w_totals, 1640)
        water_year = _32bit(w_totals, 1642)
        water_month = _32bit(w_totals, 1652)
        water_last_month = _32bit(w_totals, 1650)
        # Lifetime not yet identified — use year as best approximation
        water_lifetime = water_year

        # ---- Device datetime ----
        year_raw = _intval(_get(live, "1146"))
        dt_year = 2000 + year_raw if year_raw is not None else None

        return KospelData(
            # Temperatures
            inlet_temp=_div10(_get(live, "1134")),
            outlet_temp=_div10(_get(live, "1135")),
            aux_temp=_div10(_get(live, "1136")),
            current_setpoint=_div10(_get(live, "1140")),
            target_temp=_div10(_get(temp, "1391")),
            max_allowed_temp=_div10(_get(temp, "1388")),
            hw_max_temp=_div10(_get(temp, "1395")),
            # Limits
            temp_min=temp_min,
            temp_max=temp_max,
            # Flow / Power
            flow_rate=_div10(_get(live, "1137")),
            power_w=power_w,
            power_kw=power_w / 1000.0 if power_w is not None else None,
            rated_power_w=_intval(_get(live, "1143")),
            selected_power_w=selected_power_w,
            selected_power_kw=(
                selected_power_w / 1000.0
                if selected_power_w is not None
                else None
            ),
            min_flow=_intval(_get(live, "1142")),
            # Status
            status_word=status_word,
            is_heating=is_heating,
            is_power_limited=is_power_limited,
            is_temp_locked=is_temp_locked,
            # Errors
            error_word1=error_word1,
            error_word2=error_word2,
            has_errors=error_word1 != 0,
            has_warnings=error_word2 != 0,
            active_errors=active_errors,
            active_warnings=active_warnings,
            error_count=len(active_errors),
            warning_count=len(active_warnings),
            # Heating
            heating_stage=heating_stage,
            # Datetime
            dt_year=dt_year,
            dt_month=_intval(_get(live, "1147")),
            dt_day=_intval(_get(live, "1148")),
            dt_dow=_intval(_get(live, "1149")),
            dt_hour=_intval(_get(live, "1150")),
            dt_minute=_intval(_get(live, "1151")),
            dt_second=_intval(_get(live, "1152")),
            # Profiles
            profile1_temp=_div10(_get(temp, "1392")),
            profile2_temp=_div10(_get(temp, "1393")),
            profile3_temp=_div10(_get(temp, "1394")),
            mode_flag=_intval(_get(temp, "1390")),
            # Energy (Wh → kWh)
            energy_today_kwh=energy_today / 1000.0,
            energy_yesterday_kwh=energy_yesterday / 1000.0,
            energy_week_kwh=energy_week / 1000.0,
            energy_month_kwh=energy_month / 1000.0,
            energy_year_kwh=energy_year / 1000.0,
            energy_lifetime_kwh=energy_lifetime / 1000.0,
            # Water (dL → L)
            water_today_l=water_today / 10.0,
            water_yesterday_l=water_yesterday / 10.0,
            water_week_l=water_week / 10.0,
            water_month_l=water_month / 10.0,
            water_year_l=water_year / 10.0,
            water_lifetime_l=water_lifetime / 10.0,
            # Raw settings for write-back
            raw_temp_settings=dict(temp) if temp else {},
        )
