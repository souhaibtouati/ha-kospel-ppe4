"""Constants for the Kospel PPE4.M integration.

Register mappings confirmed via firmware analysis (libPPE4Exp.so) and
hardware validation against a live PPE4.M device (Feb 2026).
Error/warning codes confirmed from official Kospel manual EN-116B_f.1535.
"""

DOMAIN = "kospel_ppe4"
MANUFACTURER = "Kospel"
MODEL = "PPE4.M"

CONF_HOST = "host"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 10
DEFAULT_PORT = 80

# ============================================================================
# API Endpoints
# ============================================================================
API_TEMP_LIMITS = "/api/1014/8"       # Temperature min/max limits (dynamic)
API_LIVE_DATA = "/api/1128/25"        # Live data, status, errors, datetime
API_TEMPERATURE = "/api/1388/8"       # Temperature settings & profiles
API_WRITE = "/api/write"              # Write registers (POST JSON)
API_ENERGY_DAILY = "/api/1448/30"     # Energy daily history (13 days)
API_ENERGY_TOTALS = "/api/1500/48"    # Energy period totals (incl. lifetime)
API_WATER_DAILY = "/api/1576/30"      # Water daily history (13 days)
API_WATER_TOTALS = "/api/1628/48"     # Water period totals (incl. lifetime)

# ============================================================================
# Temperature Limits (defaults; overridden by /api/1014/8 at runtime)
# ============================================================================
TEMP_MIN = 30.0
TEMP_MAX = 60.0
TEMP_STEP = 1.0
DAILY_HISTORY_DAYS = 13

# ============================================================================
# Error Word 1 — Critical errors (lock out heat output)
# From manual pages 18: E01-E11
# ============================================================================
ERROR_WORD1_BITS: dict[int, tuple[str, str]] = {
    0: ("E02", "Inlet temperature sensor failure (TIN)"),
    1: ("E03", "Outlet temperature sensor failure (TOUT)"),
    2: ("E04", "Temperature sensors reversed (OUT/IN)"),
    3: ("E05", "Air clog / flow meter failure (AIR2)"),
    4: ("E06", "Air clog / pressure switch / phase lost (AIR)"),
    5: ("E07", "Overtemperature (T MAX)"),
    6: ("E08", "Air clog / water pressure too high (FLOW)"),
    7: ("E09", "No mains grid sync / phase lost (3F)"),
    8: ("E10", "Illegal hardware configuration (CONFIG)"),
    9: ("E01", "Triac failure — ISOLATE POWER (Power Off)"),
    10: ("E11", "Control system failure — ISOLATE POWER (Power Off)"),
}

# ============================================================================
# Error Word 2 — Warnings (affect comfort, may not lock out heating)
# From manual pages 19-20: W01-W17
# ============================================================================
ERROR_WORD2_BITS: dict[int, tuple[str, str]] = {
    0: ("W01", "AIR error while heating"),
    1: ("W02", "AIR2 error while heating"),
    2: ("W03", "FLOW error while heating"),
    3: ("W04", "T MAX error while heating"),
    4: ("W05", "Pressure switch / heater / triac failure"),
    5: ("W06", "Low battery"),
    6: ("W07", "Battery drained"),
    7: ("W08", "Temperature sensor response altered"),
    8: ("W09", "Control PCB failure"),
    9: ("W10", "Control PCB failure"),
    10: ("W11", "WiFi module failure"),
    11: ("W12", "Control PCB failure"),
    12: ("W13", "Environment out of limits / inlet sensor"),
    13: ("W14", "Outlet temperature sensor failed"),
    14: ("W15", "Environment out of limits / control PCB"),
    15: ("W16", "Environment out of limits / inlet sensor"),
    16: ("W17", "Environment out of limits / control PCB"),
}
