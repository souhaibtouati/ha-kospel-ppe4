# Kospel PPE4.M — Complete API & Register Reference

**Version**: 2.0 — February 8, 2026
**Source**: Local HTTP/JSON API documented for interoperability and hardware-validated against a live device.

---

## 1. Connection

| Parameter | Value |
|---|---|
| Transport | HTTP (plain, no TLS) |
| Default IP | Assigned via DHCP by router after WiFi pairing |
| WiFi Setup AP | `ppe4_0000xxxx` (AP password: `12345678`, config page at `192.168.8.1`) |
| Discovery | Device hostname is `ppe4_0000xxxx` where xxxx is the module number (visible in LCD menu WIFI). Use mDNS or assign a static DHCP lease. |
| Authentication | **None** — no API key, no token, no auth headers |
| Timeout | Recommended 5 s for reads, 10 s for writes |

---

## 2. Response Envelope

All endpoints return JSON with this structure:

```json
{
  "ver": "1.0",
  "status": "OK",
  "status_value": "0",
  "res": {
    "<register_number>": <int_value>,
    ...
  }
}
```

- `status` = `"OK"` on success. Any other value means an error.
- `status_value` = `"0"` on success.
- `res` = dictionary of register number (string key) → integer value.

---

## 3. Read Endpoints

### 3.1 Temperature Limits — `GET /api/1014/8`

Returns 8 registers (1014–1021). Provides the **allowed temperature range** for the target and each profile. The values are dynamic — they update in real-time when the max temperature is changed on the device LCD.

The 8 registers are 4 identical min/max pairs (one per settable temperature):

| Registers | Meaning | Example |
|---|---|---|
| 1014, 1015 | Target temp: min, max | 300, 530 (30.0°C – 53.0°C) |
| 1016, 1017 | Profile 1: min, max | 300, 530 |
| 1018, 1019 | Profile 2: min, max | 300, 530 |
| 1020, 1021 | Profile 3: min, max | 300, 530 |

Values are in decidegrees (÷ 10 → °C). All 4 pairs are always identical since the device enforces the same range globally. The max value mirrors register 1388 from `/api/1388/8`.

**Polling**: Once at startup to set UI slider bounds. Re-read after the user changes the max temperature on the LCD.

**Use in Android app**: Set your temperature picker/slider to `min = reg_1014 / 10` and `max = reg_1015 / 10`.

---

### 3.2 Live Data — `GET /api/1128/25`

Returns 25 registers (1128–1152). This is the **primary polling endpoint** — contains temperatures, flow, power, status flags, error codes, and device clock.

#### Status Flags (Registers 1128–1129)

These two registers form a **32-bit status bitfield**:

```
status_word = (reg_1129 << 16) | reg_1128
```

| Bit | Meaning | App Usage |
|---|---|---|
| 0 | Device powered on | — |
| 5 | **Power limit active** | Device is limiting output power |
| 9 | Standby / ready | — |
| 10 | Temperature regulation available | — |
| 11 | **Temperature locked** | Setpoint at boundary (matches profile or max) |
| 16 | Communication OK (from reg 1129 bit 0) | — |

The app specifically checks bit 5 and bit 11 for UI state indicators.

#### Error Registers (1130–1133)

Two 32-bit error bitfields. **All zeros = no errors (normal operation).**

**Error Word 1** = `(reg_1131 << 16) | reg_1130`

These are **critical errors that lock out the heat output**. Mapped from the official manual error codes E01–E11:

| Bit | Error Code | LCD Text | Description |
|---|---|---|---|
| 0 | **E02** | TIN | Inlet temperature sensor failure / missing / short to ground |
| 1 | **E03** | TOUT | Outlet temperature sensor failure / missing / short to ground |
| 2 | **E04** | OUT/IN | Temperature sensor connections reversed / altered response |
| 3 | **E05** | AIR2 | Air clog in water circuit / vane flow meter dirty or failed |
| 4 | **E06** | AIR | Air clog / pressure switch triggered / supply phase voltage lost |
| 5 | **E07** | T MAX | Outlet water overtemperature / flow rate fluctuations |
| 6 | **E08** | FLOW | Air clog in water circuit / water supply pressure too high |
| 7 | **E09** | 3F | No mains grid sync signal / supply phase voltage lost |
| 8 | **E10** | CONFIG | Illegal hardware configuration (DIP switches) |
| 9 | **E01** | Power Off | ⚠️ **Triac failure — ISOLATE POWER IMMEDIATELY** |
| 10 | **E11** | Power Off | ⚠️ **Control system failure — ISOLATE POWER IMMEDIATELY** |

**Error Word 2** = `(reg_1133 << 16) | reg_1132`

These are **warnings that affect operating comfort** but do not necessarily lock out heat output. Mapped from official manual warning codes W01–W17:

| Bit | Warning Code | Description |
|---|---|---|
| 0 | **W01** | E06 AIR error occurred while heating |
| 1 | **W02** | E05 AIR2 error occurred while heating |
| 2 | **W03** | E08 FLOW error occurred while heating |
| 3 | **W04** | E07 T MAX error occurred while heating |
| 4 | **W05** | Pressure switch tripped / incorrect DIP switches / heater or triac failure / phase lost |
| 5 | **W06** | Low battery |
| 6 | **W07** | Battery drained |
| 7 | **W08** | Altered response of one or both temperature sensors |
| 8 | **W09** | Control PCB failure |
| 9 | **W10** | Control PCB failure |
| 10 | **W11** | WiFi module failure |
| 11 | **W12** | Control PCB failure |
| 12 | **W13** | Environment conditions out of limits / inlet temperature sensor failure |
| 13 | **W14** | Outlet temperature sensor failed (check with W13/W15 for combined diagnosis) |
| 14 | **W15** | Environment conditions out of limits / control PCB failure |
| 15 | **W16** | Environment conditions out of limits / inlet temperature sensor failure |
| 16 | **W17** | Environment conditions out of limits / control PCB failure |
| 17 | — | Reserved |

#### Live Sensor Registers (1134–1145)

| Register | Meaning | Raw Unit | Conversion | Display |
|---|---|---|---|---|
| 1134 | Inlet water temperature | decidegrees | ÷ 10 | `"%1.1f °C"` |
| 1135 | Outlet water temperature | decidegrees | ÷ 10 | `"%1.1f °C"` |
| 1136 | Auxiliary temperature | decidegrees | ÷ 10 | `"%1.1f °C"` (not used by official app) |
| 1137 | Water flow rate | deci-l/min | ÷ 10 | `"%1.1f l/min"` |
| 1138 | Current power consumption | watts | ÷ 1000 | `"%1.1f kW"` |
| 1139 | (unknown) | — | — | Not used by app |
| 1140 | Active temperature setpoint | decidegrees | ÷ 10 | `"%1.1f °C"` |
| 1141 | Heating stage | direct | — | 0 = off, >0 = active (number of active stages) |
| 1142 | Minimum flow threshold | direct | — | 90 observed (possibly deci-l/min) |
| 1143 | Rated power | watts | — | Device nominal power |
| 1144 | Selected power level | watts | ÷ 1000 | `"%1.1f kW"` |
| 1145 | (unknown) | — | — | Not used by app |

**Heating active** is derived from register 1141: if `reg_1141 != 0`, the device is heating.

#### Device Clock (1146–1152)

| Register | Meaning | Range |
|---|---|---|
| 1146 | Year (offset from 2000) | e.g. 26 = 2026 |
| 1147 | Month | 1–12 |
| 1148 | Day | 1–31 |
| 1149 | Day of week | 1–7 (1 = Monday) |
| 1150 | Hour | 0–23 |
| 1151 | Minute | 0–59 |
| 1152 | Second | 0–59 |

**Polling**: Every 5–10 seconds for live UI updates.

---

### 3.3 Temperature Settings — `GET /api/1388/8`

Returns 8 registers (1388–1395).

| Register | Meaning | Raw Unit | Conversion | R/W |
|---|---|---|---|---|
| 1388 | Max allowed temperature (LCD "Temp_Max") | decidegrees | ÷ 10 | R |
| 1389 | (reserved, always 0) | — | — | R |
| 1390 | Configuration mode flag | direct | 0 = normal, 1 = demo | R/W |
| 1391 | Target temperature | decidegrees | ÷ 10 | R/W |
| 1392 | Profile 1 temperature | decidegrees | ÷ 10 | R/W |
| 1393 | Profile 2 temperature | decidegrees | ÷ 10 | R/W |
| 1394 | Profile 3 temperature | decidegrees | ÷ 10 | R/W |
| 1395 | Hardware max temperature (factory limit) | decidegrees | ÷ 10 | R |

**Polling**: After each write, or every 30–60 seconds.

---

### 3.4 Energy Daily History — `GET /api/1448/30`

Returns 30 registers (1448–1477). Each day uses a **register pair** forming a 32-bit value.

**Formula**: `energy_kWh = ((reg_odd << 16) | reg_even) / 1000`

The first pair (1448/1449) appears to be metadata/padding. Actual data starts at 1450.

| Registers | Formula | Meaning |
|---|---|---|
| 1448, 1449 | — | (header / padding — skip) |
| **1450**, **1451** | `(r1451 << 16 \| r1450) / 1000` | **Energy today** (kWh) |
| 1452, 1453 | `(r1453 << 16 \| r1452) / 1000` | Energy yesterday |
| 1454, 1455 | `(r1455 << 16 \| r1454) / 1000` | Energy 2 days ago |
| 1456, 1457 | `(r1457 << 16 \| r1456) / 1000` | Energy 3 days ago |
| 1458, 1459 | `(r1459 << 16 \| r1458) / 1000` | Energy 4 days ago |
| 1460, 1461 | `(r1461 << 16 \| r1460) / 1000` | Energy 5 days ago |
| 1462, 1463 | `(r1463 << 16 \| r1462) / 1000` | Energy 6 days ago |
| 1464, 1465 | `(r1465 << 16 \| r1464) / 1000` | Energy 7 days ago |
| 1466, 1467 | `(r1467 << 16 \| r1466) / 1000` | Energy 8 days ago |
| 1468, 1469 | `(r1469 << 16 \| r1468) / 1000` | Energy 9 days ago |
| 1470, 1471 | `(r1471 << 16 \| r1470) / 1000` | Energy 10 days ago |
| 1472, 1473 | `(r1473 << 16 \| r1472) / 1000` | Energy 11 days ago |
| 1474, 1475 | `(r1475 << 16 \| r1474) / 1000` | Energy 12 days ago |

Total: 13 days of history (today + 12 previous days).

---

### 3.5 Energy Period Totals — `GET /api/1500/48`

Returns 48 registers (1500–1547). Same 32-bit pair formula, **÷ 1000** for kWh.

> **Note**: The official app fetches `/api/1520/48` (starting at register 1520). However, the actual data extends back to register 1500, which contains additional period totals including what appears to be the lifetime energy counter.

**Formula**: `energy_kWh = ((reg_odd << 16) | reg_even) / 1000`

| Registers | Meaning |
|---|---|
| 1500–1511 | Daily history (6 × 32-bit pairs, mirrors /api/1448 days) |
| **1512, 1513** | **Energy This Week** (confirmed: 40.4 kWh ✓) |
| **1514, 1515** | **Energy This Year** (confirmed: 300 kWh ✓) |
| 1516, 1517 | Last Year (0 on first year) |
| 1518, 1519 | This Year duplicate |
| 1520, 1521 | 0 (unknown) |
| **1522, 1523** | **Energy Last Month** (confirmed: Feb = 201.3 kWh, Feb+Mar = Year ✓) |
| **1524, 1525** | **Energy This Month** (confirmed: 99.6 kWh ≈ LCD 99.3 ✓) |
| 1526–1547 | Historical months (all 0 on new device) |

> Layout confirmed by cross-referencing LCD display against differentiated register values (Mar 2026).
> Validation: Last Month (1522) + This Month (1524) = This Year (1514) ✓

---

### 3.6 Water Daily History — `GET /api/1576/30`

Returns 30 registers (1576–1605). Same register pair structure, but **÷ 10** for liters.

**Formula**: `water_L = ((reg_odd << 16) | reg_even) / 10`

| Registers | Formula | Meaning |
|---|---|---|
| 1576, 1577 | — | Header: day of week (1576) and month (1577) |
| **1578**, **1579** | `(r1579 << 16 \| r1578) / 10` | **Water today** (L) |
| 1580, 1581 | `(r1581 << 16 \| r1580) / 10` | Water yesterday |
| 1582, 1583 | `(r1583 << 16 \| r1582) / 10` | Water 2 days ago |
| 1584, 1585 | same pattern... | Water 3 days ago |
| 1586, 1587 | | Water 4 days ago |
| 1588, 1589 | | Water 5 days ago |
| 1590, 1591 | | Water 6 days ago |
| 1592, 1593 | | Water 7 days ago |
| 1594, 1595 | | Water 8 days ago |
| 1596, 1597 | | Water 9 days ago |
| 1598, 1599 | | Water 10 days ago |
| 1600, 1601 | | Water 11 days ago |
| 1602, 1603 | | Water 12 days ago |

Total: 13 days of history.

---

### 3.7 Water Period Totals — `GET /api/1628/48`

Returns 48 registers (1628–1675). Same structure as energy period totals but **÷ 10** for liters.

> **Note**: The official app fetches `/api/1648/48`. Like with energy, the data extends back to ~1628 with additional lifetime/weekly counters.

**Formula**: `water_L = ((reg_odd << 16) | reg_even) / 10`

| Registers | Meaning |
|---|---|
| 1628–1639 | Daily history (6 × 32-bit pairs, mirrors /api/1576 days) |
| **1640, 1641** | **Water This Week** (confirmed: 1.128 m³ ≈ LCD 1.12 ✓) |
| **1642, 1643** | **Water This Year** (confirmed: 7.766 m³ ≈ LCD 7.76 ✓) |
| 1644, 1645 | Last Year (0 on first year) |
| 1646, 1647 | This Year duplicate |
| 1648, 1649 | 0 (unknown) |
| **1650, 1651** | **Water Last Month** (Feb = 5.053 m³, Feb+Mar = Year ✓) |
| **1652, 1653** | **Water This Month** (confirmed: 2.713 m³ ≈ LCD 2.7 ✓) |
| 1654–1675 | Historical months (all 0 on new device) |

> Same layout as energy periods. Validation: Last Month + This Month = This Year ✓

---

## 4. Write Endpoint

### `POST /api/write`

Writes temperature settings and configuration. The body is JSON with register keys as strings.

**Content-Type**: `application/json`

**The official app always writes all 5 registers together:**

```json
{
  "1390": 0,
  "1391": 400,
  "1392": 350,
  "1393": 450,
  "1394": 550
}
```

| Key | Meaning | Value Format |
|---|---|---|
| `"1390"` | Mode flag | 0 = normal operation |
| `"1391"` | Target temperature | **degrees × 10** (e.g. 400 = 40.0°C) |
| `"1392"` | Profile 1 temperature | degrees × 10 |
| `"1393"` | Profile 2 temperature | degrees × 10 |
| `"1394"` | Profile 3 temperature | degrees × 10 |

**Temperature range**: The device supports two modes configured via DIP switch 3 on the control board:
- **NORMAL mode** (factory default): 300–600 (30.0°C – 60.0°C)
- **SHOWER mode** (DIP switch 3 ON): 300–550 (30.0°C – 55.0°C)

The effective max is further limited by the LCD "TEMP MAX" setting (register 1388 / endpoint `/api/1014/8`). The device enforces limits internally.

**Write flow**:
1. Read current values from `/api/1388/8`
2. Modify only the values you want to change
3. POST all 5 registers together to `/api/write`
4. Wait ~200 ms (the app inserts this delay)
5. Re-read `/api/1388/8` and `/api/1128/25` to confirm

Register 1144 (selected power level) is also writable. The app does not write it through this endpoint, but it can be written as:
```json
{"1144": 18000}
```
Value is in watts (e.g. 18000 = 18 kW).

---

## 5. Data Conversion Reference

### 32-bit Register Pair Pattern

All statistics registers use pairs of consecutive 16-bit registers to form a 32-bit value:

```kotlin
fun readUint32(res: Map<String, Int>, lowReg: Int): Long {
    val low = res[lowReg.toString()] ?: 0
    val high = res[(lowReg + 1).toString()] ?: 0
    return (high.toLong() shl 16) or low.toLong()
}

// Energy (Wh → kWh)
val energyKwh = readUint32(res, 1450) / 1000.0

// Water (dL → L)
val waterL = readUint32(res, 1578) / 10.0
```

### Conversion Summary

| Data Type | Raw Unit | Divisor | Display Unit |
|---|---|---|---|
| Temperature (1134, 1135, 1136, 1140) | decidegrees (°C × 10) | ÷ 10 | °C |
| Flow rate (1137) | deci-l/min | ÷ 10 | l/min |
| Power (1138, 1144) | watts | ÷ 1000 | kW |
| Temperature settings (1388, 1391–1395) | decidegrees | ÷ 10 | °C |
| Energy daily & period totals | Wh (32-bit) | ÷ 1000 | kWh |
| Water daily & period totals | dL (32-bit) | ÷ 10 | L |
| Clock year (1146) | offset from 2000 | + 2000 | year |
| Status (1128/1129) | bitfield | bit-test | boolean flags |
| Errors (1130–1133) | bitfield | bit-test | boolean flags |
| Heating stage (1141) | direct | — | 0 = off |

---

## 6. Recommended Polling Strategy for Android

```
┌─────────────────────────────────────────┐
│  Foreground (live screen visible)       │
│  Every 5–10 seconds:                    │
│    GET /api/1128/25  (live data)        │
│    GET /api/1388/8   (settings)         │
│                                         │
│  Every 60 seconds:                      │
│    GET /api/1448/30  (energy daily)     │
│    GET /api/1500/48  (energy totals)    │
│    GET /api/1576/30  (water daily)      │
│    GET /api/1628/48  (water totals)     │
│                                         │
│  Once at startup:                       │
│    GET /api/1014/8   (device info)      │
└─────────────────────────────────────────┘
```

Use concurrent requests with coroutines. The device handles multiple simultaneous connections.

---

## 7. Android Implementation Notes

### Kotlin Data Classes

```kotlin
data class LiveData(
    val statusWord: Long,        // (reg1129 << 16) | reg1128
    val errorWord1: Long,        // (reg1131 << 16) | reg1130
    val errorWord2: Long,        // (reg1133 << 16) | reg1132
    val inletTemp: Double,       // reg1134 / 10.0
    val outletTemp: Double,      // reg1135 / 10.0
    val flowRate: Double,        // reg1137 / 10.0
    val powerKw: Double,         // reg1138 / 1000.0
    val setpoint: Double,        // reg1140 / 10.0
    val heatingStage: Int,       // reg1141 (0 = off)
    val selectedPowerKw: Double, // reg1144 / 1000.0
    val deviceTime: LocalDateTime,
    // derived booleans
    val isHeating: Boolean,      // reg1141 != 0
    val isPowerLimited: Boolean, // statusWord bit 5
    val isTempLocked: Boolean,   // statusWord bit 11
    val hasError1: Boolean,      // errorWord1 != 0
    val hasError2: Boolean,      // errorWord2 != 0
)

data class Settings(
    val maxAllowedTemp: Double,  // reg1388 / 10.0
    val modeFlag: Int,           // reg1390
    val targetTemp: Double,      // reg1391 / 10.0
    val profile1Temp: Double,    // reg1392 / 10.0
    val profile2Temp: Double,    // reg1393 / 10.0
    val profile3Temp: Double,    // reg1394 / 10.0
    val hwMaxTemp: Double,       // reg1395 / 10.0
)

data class EnergyStats(
    val dailyKwh: List<Double>,     // 13 days, index 0 = today
    val thisYearKwh: Double,        // reg 1520/1521
    val thisMonthKwh: Double,       // reg 1522/1523
    val monthlyKwh: List<Double>,   // up to 12 previous months
    val lifetimeKwh: Double,        // reg 1512/1513
)

data class WaterStats(
    val dailyL: List<Double>,       // 13 days, index 0 = today
    val thisYearL: Double,          // reg 1648/1649
    val thisMonthL: Double,         // reg 1650/1651
    val monthlyL: List<Double>,     // up to 12 previous months
    val lifetimeL: Double,          // reg 1640/1641 (probable)
)
```

### Parsing Example

```kotlin
fun parseLiveData(res: Map<String, Int>): LiveData {
    val r = { key: Int -> res[key.toString()] ?: 0 }
    val u32 = { low: Int -> (r(low + 1).toLong() shl 16) or r(low).toLong() }

    val statusWord = u32(1128)
    val errorWord1 = u32(1130)
    val errorWord2 = u32(1132)

    return LiveData(
        statusWord = statusWord,
        errorWord1 = errorWord1,
        errorWord2 = errorWord2,
        inletTemp = r(1134) / 10.0,
        outletTemp = r(1135) / 10.0,
        flowRate = r(1137) / 10.0,
        powerKw = r(1138) / 1000.0,
        setpoint = r(1140) / 10.0,
        heatingStage = r(1141),
        selectedPowerKw = r(1144) / 1000.0,
        deviceTime = LocalDateTime.of(
            r(1146) + 2000, r(1147), r(1148),
            r(1150), r(1151), r(1152)
        ),
        isHeating = r(1141) != 0,
        isPowerLimited = (statusWord and (1L shl 5)) != 0L,
        isTempLocked = (statusWord and (1L shl 11)) != 0L,
        hasError1 = errorWord1 != 0L,
        hasError2 = errorWord2 != 0L,
    )
}

fun parseEnergyDaily(res: Map<String, Int>): List<Double> {
    return (0 until 13).map { day ->
        val baseReg = 1450 + (day * 2)
        val low = res[baseReg.toString()] ?: 0
        val high = res[(baseReg + 1).toString()] ?: 0
        ((high.toLong() shl 16) or low.toLong()) / 1000.0
    }
}

fun parseWaterDaily(res: Map<String, Int>): List<Double> {
    return (0 until 13).map { day ->
        val baseReg = 1578 + (day * 2)
        val low = res[baseReg.toString()] ?: 0
        val high = res[(baseReg + 1).toString()] ?: 0
        ((high.toLong() shl 16) or low.toLong()) / 10.0
    }
}
```

### Write Example

```kotlin
suspend fun setTemperature(
    host: String,
    targetDeg: Double,
    profile1Deg: Double,
    profile2Deg: Double,
    profile3Deg: Double,
    mode: Int = 0
) {
    val body = JSONObject().apply {
        put("1390", mode)
        put("1391", (targetDeg * 10).toInt())
        put("1392", (profile1Deg * 10).toInt())
        put("1393", (profile2Deg * 10).toInt())
        put("1394", (profile3Deg * 10).toInt())
    }

    val request = Request.Builder()
        .url("http://$host/api/write")
        .post(body.toString().toRequestBody("application/json".toMediaType()))
        .build()

    httpClient.newCall(request).execute()
    delay(200) // firmware needs time to apply
}
```

---

## 8. Error Handling

- **Connection refused**: Device is off or not on the network.
- **Timeout (>5 s)**: Device may be rebooting. Retry with backoff.
- **`status` != `"OK"`**: Invalid register range or device busy. Don't retry immediately.
- **All register values = 0**: Normal for error registers and unused history slots. Only flag an issue if live registers (1134, 1135, 1138) are all 0 when the device should be connected.
- **Stale data**: The device clock (1146–1152) can be used to verify the device is responding with fresh data.

---

## 9. Complete Register Map

### Live Data Endpoint (`/api/1128/25`)

| Reg | Name | Type | Scale | Description |
|---|---|---|---|---|
| 1128 | status_low | uint16 | bitfield | Status word, low 16 bits |
| 1129 | status_high | uint16 | bitfield | Status word, high 16 bits |
| 1130 | error1_low | uint16 | bitfield | Error word 1, low 16 bits |
| 1131 | error1_high | uint16 | bitfield | Error word 1, high 16 bits |
| 1132 | error2_low | uint16 | bitfield | Error word 2, low 16 bits |
| 1133 | error2_high | uint16 | bitfield | Error word 2, high 16 bits |
| 1134 | inlet_temp | int | ÷ 10 → °C | Inlet water temperature |
| 1135 | outlet_temp | int | ÷ 10 → °C | Outlet water temperature |
| 1136 | aux_temp | int | ÷ 10 → °C | Auxiliary temperature (not in app) |
| 1137 | flow_rate | int | ÷ 10 → l/min | Water flow rate |
| 1138 | power | int | W (÷1000 → kW) | Current power consumption |
| 1139 | — | — | — | Unknown / not used |
| 1140 | setpoint | int | ÷ 10 → °C | Active temperature setpoint |
| 1141 | heating_stage | int | direct | 0=off, >0=active stages |
| 1142 | min_flow | int | direct | Minimum flow threshold (heating starts at 1.8 l/min per manual) |
| 1143 | rated_power | int | W | Device rated power |
| 1144 | selected_power | int | W (÷1000 → kW) | Selected power level (writable) |
| 1145 | — | — | — | Unknown / not used |
| 1146 | year | int | +2000 | Clock: year |
| 1147 | month | int | 1–12 | Clock: month |
| 1148 | day | int | 1–31 | Clock: day |
| 1149 | day_of_week | int | 1–7 | Clock: day of week (1=Mon) |
| 1150 | hour | int | 0–23 | Clock: hour |
| 1151 | minute | int | 0–59 | Clock: minute |
| 1152 | second | int | 0–59 | Clock: second |

### Settings Endpoint (`/api/1388/8`)

| Reg | Name | Type | Scale | R/W | Description |
|---|---|---|---|---|---|
| 1388 | max_allowed_temp | int | ÷ 10 → °C | R | Max allowed temperature |
| 1389 | — | — | — | R | Reserved (always 0) |
| 1390 | mode_flag | int | direct | R/W | 0=normal, 1=demo |
| 1391 | target_temp | int | ÷ 10 → °C | R/W | Target temperature |
| 1392 | profile1_temp | int | ÷ 10 → °C | R/W | Profile 1 temperature |
| 1393 | profile2_temp | int | ÷ 10 → °C | R/W | Profile 2 temperature |
| 1394 | profile3_temp | int | ÷ 10 → °C | R/W | Profile 3 temperature |
| 1395 | hw_max_temp | int | ÷ 10 → °C | R | Hardware max (factory limit, 70°C) |

### Energy Daily (`/api/1448/30`) — ÷ 1000 → kWh

| Registers (low, high) | Day |
|---|---|
| 1450, 1451 | Today |
| 1452, 1453 | Yesterday |
| 1454, 1455 | 2 days ago |
| ... (2 regs per day) | ... |
| 1474, 1475 | 12 days ago |

### Energy Periods (`/api/1500/48`) — ÷ 1000 → kWh

| Registers (low, high) | Period |
|---|---|
| 1512, 1513 | This week (confirmed) |
| 1514, 1515 | This year (confirmed) |
| 1516, 1517 | Last year |
| 1518, 1519 | This year (duplicate) |
| 1522, 1523 | Last month (confirmed) |
| 1524, 1525 | This month (confirmed) |

### Water Daily (`/api/1576/30`) — ÷ 10 → L

| Registers (low, high) | Day |
|---|---|
| 1578, 1579 | Today |
| 1580, 1581 | Yesterday |
| 1582, 1583 | 2 days ago |
| ... (2 regs per day) | ... |
| 1602, 1603 | 12 days ago |

### Water Periods (`/api/1628/48`) — ÷ 10 → L

| Registers (low, high) | Period |
|---|---|
| 1640, 1641 | This week (confirmed) |
| 1642, 1643 | This year (confirmed) |
| 1644, 1645 | Last year |
| 1646, 1647 | This year (duplicate) |
| 1650, 1651 | Last month (confirmed) |
| 1652, 1653 | This month (confirmed) |

---

## 10. LCD Panel Menu ↔ API Register Mapping

The PPE4.M LCD panel displays information that maps directly to API registers:

| LCD Menu Item | LCD Text | API Source |
|---|---|---|
| Temperature profiles | TEMP 1 / TEMP 2 / TEMP 3 | Registers 1392, 1393, 1394 (write via `/api/write`) |
| Actual heat output | POWER | Register 1138 ÷ 1000 → kW |
| Cold water inlet temp | TEMP IN | Register 1134 ÷ 10 → °C |
| Hot water outlet temp | TEMP OUT | Register 1135 ÷ 10 → °C |
| DHW temperature setting | SET TEMP | Register 1140 ÷ 10 → °C |
| Actual water flow rate | FLOW | Register 1137 ÷ 10 → l/min |
| Heat output setting | SET POWER | Register 1144 ÷ 1000 → kW |
| Energy consumption | ENERGY (DAY/WEEK/MONTH/YEAR) | `/api/1448/30` + `/api/1500/48` |
| Water consumption | WATER (DAY/WEEK/MONTH/YEAR) | `/api/1576/30` + `/api/1628/48` |
| Max temperature setting | TEMP MAX | Register 1388 ÷ 10 → °C (also `/api/1014/8`) |
| WiFi signal level | WIFI | Not exposed via API |
| Active warnings | WARNINGS | Error Word 2 (registers 1132/1133) |
| Active errors | ERRORS | Error Word 1 (registers 1130/1131) |
| Date and time | DATE TIME | Registers 1146–1152 |

### LCD Icons and API Equivalents

| LCD Icon | Meaning | API Detection |
|---|---|---|
| ⚡ (heating) | Heating on | Register 1141 > 0 |
| ⚡ (flashing) | Temperature cannot be achieved at max power | Status word bit 5 = 1 |
| ⚠ (warning) | Operating comfort event | Error Word 2 ≠ 0 |
| 🚫 (error) | Heat output locked out | Error Word 1 ≠ 0 |
| 💧 (water drop) | Flow rate display | Register 1137 > 0 |
| 📶 (WiFi) | WiFi connected | Connection alive |

---

## 11. Hardware Configuration (DIP Switches)

The PPE4 has a 6-position DIP switch block inside the enclosure. These settings affect the API behavior:

| DIP Switch | Function | Effect on API |
|---|---|---|
| 1–2 | Power level selection (4 combinations) | Changes register 1143 (rated_power) and 1144 range |
| 3 | SHOWER mode (max 55°C) | Changes register 1388 max from 600 → 550; `/api/1014/8` values change |
| 4 | Temperature setting lockout | Prevents writes to registers 1391–1394 via `/api/write` |
| 5 | Air clogging sensor disabled | Affects whether E05/E06 errors appear in Error Word 1 |
| 6 | Power triac failure detection disabled | Affects whether E01 error appears in Error Word 1 |

### Power Level Settings (DIP switches 1–2)

| DIP 1 | DIP 2 | PPE4-10/11/12/15 | PPE4-17/18/21/24 |
|---|---|---|---|
| OFF | OFF | 10 kW | 17 kW |
| ON | OFF | 11 kW | 18 kW |
| OFF | ON | 12 kW | 21 kW |
| ON | ON | 15 kW | 24 kW |

---

## 12. Security Notes

- **No authentication** — anyone on the local network can read all data and change settings.
- **Plain HTTP** — all data is unencrypted.
- **Recommendation**: Isolate the device on a dedicated VLAN or IoT network. Use a reverse proxy with authentication if exposing outside the LAN.
- The device does not support HTTPS, firmware updates over WiFi, or any form of access control.
