<!--
# titel: ScopeMCP
# license: GPL-3.0-or-later
# Copyright (c) 2026 Kletternaut
-->
# Documentation: Owon/Abestop DS1102 USB Protocol

This documentation is based on reverse engineering of the USB traffic between the DSO-Wave software and the oscilloscope (VID: 0x5345, PID: 0x1234).

## 1. Physical Layer
- **Interface**: USB Bulk Transfer
- **Endpoints**: 
    - OUT: `0x01` (Commands to device)
    - IN:  `0x81` (Data from device)
- **Max Packet Size**: 64 Bytes (USB 2.0 Full Speed)
- **Terminator**: All ASCII commands should be terminated with `\n` (Hex: `0A`). The device often accepts `\r\n`, but `\n` is the standard for the internal SCPI engine.
- **USB Transfer Limit**: The device has a hard limit of **3044 Bytes** per USB bulk read operation. Larger data packets must be read in segments (currently relevant for 1520 samples à 2 bytes = 3040 bytes).

## 2. Communication Handshake
Before data can be requested, the device must be initialized.
- **Initialization Command**: `*IDN?\n` or `:MODel?\n`
- **Response**: Identification string (e.g., `Abestop,DS1102,24250071,V3.1.0`)
- **Important**: Without an initial identification or after a USB timeout, the device often needs to be re-initialized (Re-Init Logic).

## 3. Command Structure (SCPI-optimized)
The device uses a FastMCP-based async architecture where all USB calls are offloaded via `asyncio.to_thread` to avoid blocking the event loop.

### Control Commands (Verified)
| Command | Action | Example |
| :--- | :--- | :--- |
| `:AUToset on` | Executes automatic setup | `:AUToset on\n` |
| `:RUNning RUN` | Starts acquisition (Green LED) | `:RUNning RUN\n` |
| `:RUNning STOP` | Stops acquisition (Red LED) | `:RUNning STOP\n` |
| `:CH1:SCALe <v>` | Sets vertical scale | `:CH1:SCALe 1.00V\n` |
| `:HORizontal:SCALe <s>` | Sets timebase | `:HORizontal:SCALe 1ms\n` |
| `:TRIGger:EDGe:LEVel <mv>` | Sets trigger level in mV | `:TRIGger:EDGe:LEVel 1500\n` |

### Query Commands (Metadata & Measurements)
- **Metadata**: `:DATA:WAVE:SCREEN:HEAD?\n`
    - Response: 4-byte header + JSON (e.g., `{"model":"DS1102", "CH1_SCALE":"2.00V", ...}`)
    - Includes critical values like `GRID_OFF` (Grid offset for scaling).
- **Measurements: The device supports direct queries for automatic measurements**:
    - `:MEASure:FREQuency?` (Frequency in Hz)
    - `:MEASure:PERIod?` (Period in seconds)
    - `:MEASure:PKPK?` (Vpp voltage)
    - `:MEASure:Vrms?` (RMS voltage)
- **Response Format**: `[Header: 4 Bytes][JSON-Payload]`
- **Response Header**: `: \x03 \x00 \x00` (First byte is `:`, then 3 bytes length indicator/type)
- **JSON Content**: Contains `TIMEBASE`, `CHANNEL` scaling (e.g., "2.00V"), `OFFSET`, and `SAMPLE` count.

## 4. Waveform Data
- **Commands**: `:DATA:WAVE:SCREEN:CH1?` or `:DATA:WAVE:SCREEN:CH2?`
- **Response Format**: `[Header: 4 Bytes][Binary Data]`
- **Header**: The first 4 bytes contain the length in Little-Endian.
    - Example: `e0 0b 00 00` -> `0x0be0` = 3040 Bytes.
- **Data Points**: 
    - Each sample consists of **2 Bytes (16-bit)**.
    - Format: **Little-Endian** Signed Integer (`<h`). *Correction: Contrary to initial assumptions, Little-Endian is correct for this model.*
    - Number of samples: 1520 per channel (equals 3040 Bytes / 2).
- **Precise Voltage Calculation (V1.2.0)**:
    - Formula: `voltage = ((GridOffset - RawValue) / 250.0) * Scale * Probe`
    - `GridOffset`: Value from the metadata JSON.
    - `250.0`: Constant LSB/Division factor for SCREEN mode.
    - `Scale`: Current scaling (e.g., 1.0 for 1V/Div).
    - `Probe`: Probe factor (1x, 10x).

## 5. Known Limits & Performance
- **Transfer Limit**: 3044 Bytes (hardware-related).
- **Latency**: A sequential read of both channels takes about 16s. Through **Async optimization** and removal of redundant metadata queries, this has been reduced to **~7s**.
- **Cache**: A 2.0s TTL cache for metadata prevents unnecessary USB load.

---

## MCP Integration Status (as of March 15, 2026)

The protocol is fully implemented in `ds1102_mcp.py` and supports:
- [x] Async I/O (no blocking)
- [x] Dual-Channel Capture (optimized)
- [x] Direct measurement queries (Frequency, Vpp, etc.)
- [x] Trigger level control
- [x] Automatic USB reconnection (Re-Init)

| `:CH1:SCALe <val>` | `:CH1:SCALe 1.00V` | Sets the scale for CH1 |

---

## Completed & Open Tasks

In Version 1.2.0, many research tasks were solved:

1.  **Measurements**: [SOLVED] Device supports `:MEASure:FREQuency?`, `:MEASure:PKPK?`, etc.
2.  **Trigger Level**: [SOLVED] Controlled via `:TRIGger:EDGe:LEVel <mv>`.
3.  **Latency**: [OPTIMIZED] Reduced from 16s to ~7s for Dual-Channel.

**Open**:
- **Deep Memory**: Querying more than 1520 samples (Deep Memory).
- **Display Dump**: Direct frame buffer query (if supported).

## 6. Important Note for Developers
The device is extremely sensitive to rapid successive bulk reads. The Python implementation uses `time.sleep(0.01)` between commands and a robust retry logic with re-initialization of the USB interface.
