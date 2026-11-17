"""API client for Kospel PPE4.M water heater."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_ENERGY_DAILY,
    API_ENERGY_TOTALS,
    API_LIVE_DATA,
    API_TEMP_LIMITS,
    API_TEMPERATURE,
    API_WATER_DAILY,
    API_WATER_TOTALS,
    API_WRITE,
    DEFAULT_PORT,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10)


class KospelApiError(Exception):
    """General API error."""


class KospelConnectionError(KospelApiError):
    """Connection error."""


class KospelApiClient:
    """API client for Kospel PPE4.M water heater.

    The PPE4.M WiFi module exposes a local HTTP/JSON API:
        GET  http://<host>/api/<start_register>/<count>  → JSON register dict
        POST http://<host>/api/write                     → write registers
    """

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._host = host
        self._port = port
        self._session = session
        self._base_url = f"http://{host}:{port}" if port != 80 else f"http://{host}"

    @property
    def host(self) -> str:
        return self._host

    # ------------------------------------------------------------------
    # Low-level API
    # ------------------------------------------------------------------

    async def _get(self, path: str) -> dict[str, Any]:
        """GET request, return the 'res' dict from the response envelope."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(url, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                _LOGGER.debug("GET %s → %s", url, data)

                if isinstance(data, dict) and "res" in data:
                    status = data.get("status", "")
                    if status != "OK":
                        _LOGGER.warning("API status=%s for %s", status, path)
                    return data["res"]
                return data if isinstance(data, dict) else {}
        except asyncio.TimeoutError as err:
            raise KospelConnectionError(
                f"Timeout connecting to {self._host}"
            ) from err
        except aiohttp.ClientError as err:
            raise KospelConnectionError(
                f"Error connecting to {self._host}: {err}"
            ) from err

    async def _post_json(self, path: str, payload: dict) -> bool:
        """POST request with JSON body."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.post(
                url, json=payload, timeout=TIMEOUT
            ) as resp:
                resp.raise_for_status()
                _LOGGER.debug("POST %s ← %s → %s", url, payload, resp.status)
                return True
        except asyncio.TimeoutError as err:
            raise KospelConnectionError(
                f"Timeout connecting to {self._host}"
            ) from err
        except aiohttp.ClientError as err:
            raise KospelConnectionError(
                f"Error writing to {self._host}: {err}"
            ) from err

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    async def async_get_temp_limits(self) -> dict[str, Any]:
        """Fetch temperature limits (1014-1021)."""
        return await self._get(API_TEMP_LIMITS)

    async def async_get_live_data(self) -> dict[str, Any]:
        """Fetch live operational data (1128-1152)."""
        return await self._get(API_LIVE_DATA)

    async def async_get_temperature(self) -> dict[str, Any]:
        """Fetch temperature settings (1388-1395)."""
        return await self._get(API_TEMPERATURE)

    async def async_get_energy_daily(self) -> dict[str, Any]:
        """Fetch energy daily history (1448-1477)."""
        return await self._get(API_ENERGY_DAILY)

    async def async_get_energy_totals(self) -> dict[str, Any]:
        """Fetch energy period totals (1500-1547)."""
        return await self._get(API_ENERGY_TOTALS)

    async def async_get_water_daily(self) -> dict[str, Any]:
        """Fetch water daily history (1576-1605)."""
        return await self._get(API_WATER_DAILY)

    async def async_get_water_totals(self) -> dict[str, Any]:
        """Fetch water period totals (1628-1675)."""
        return await self._get(API_WATER_TOTALS)

    # ------------------------------------------------------------------
    # Write helpers — firmware expects ALL 5 registers together
    # ------------------------------------------------------------------

    async def async_write_settings(
        self,
        mode: int,
        target: int,
        profile1: int,
        profile2: int,
        profile3: int,
    ) -> bool:
        """Write all 5 config registers as the firmware expects.

        All temperature values are in decidegrees (e.g. 40°C = 400).
        Mode: 0 = normal, 1 = demo.
        """
        payload = {
            "1390": mode,
            "1391": target,
            "1392": profile1,
            "1393": profile2,
            "1394": profile3,
        }
        return await self._post_json(API_WRITE, payload)

    async def async_set_target_temperature(
        self, temperature: float, current_settings: dict | None = None
    ) -> bool:
        """Set target temperature while preserving other settings.

        Args:
            temperature: Target temperature in °C.
            current_settings: Dict with current register values from /api/1388/8.
                If None, only the target register is written (may work on some firmware).
        """
        raw_target = int(round(temperature * 10))

        if current_settings:
            return await self.async_write_settings(
                mode=_intval(current_settings.get("1390", 0)),
                target=raw_target,
                profile1=_intval(current_settings.get("1392", 350)),
                profile2=_intval(current_settings.get("1393", 450)),
                profile3=_intval(current_settings.get("1394", 550)),
            )
        # Fallback: write only the target register
        return await self._post_json(API_WRITE, {"1391": raw_target})

    async def async_set_profile_temperature(
        self, profile: int, temperature: float, current_settings: dict | None = None
    ) -> bool:
        """Set a profile temperature (1, 2, or 3)."""
        raw = int(round(temperature * 10))
        reg = str(1391 + profile)  # profile 1→1392, 2→1393, 3→1394

        if current_settings:
            settings = {
                "1390": _intval(current_settings.get("1390", 0)),
                "1391": _intval(current_settings.get("1391", 400)),
                "1392": _intval(current_settings.get("1392", 350)),
                "1393": _intval(current_settings.get("1393", 450)),
                "1394": _intval(current_settings.get("1394", 550)),
            }
            settings[reg] = raw
            return await self.async_write_settings(**{
                "mode": settings["1390"],
                "target": settings["1391"],
                "profile1": settings["1392"],
                "profile2": settings["1393"],
                "profile3": settings["1394"],
            })
        return await self._post_json(API_WRITE, {reg: raw})

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    async def async_test_connection(self) -> dict[str, Any]:
        """Test connection by fetching temp limits."""
        return await self.async_get_temp_limits()


def _intval(raw: Any) -> int:
    """Parse a raw value as integer with fallback to 0."""
    if raw is None:
        return 0
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0
