# ScopeMCP — Project Review & Improvement Suggestions
> Repo: https://github.com/Kletternaut/ScopeMCP
> Review based on: ds1102_mcp.py (V1.1.0), live testing session

---

## Summary

ScopeMCP is a well-structured and functional MCP bridge for the DS1102 oscilloscope.
The core functionality works reliably. The following review identifies areas for
improvement across code quality, performance, robustness, and feature completeness.

---

## 1. Performance

### 1.1 USB Transfer is the Main Bottleneck (~9–10s per capture)
The DS1102 always transfers the full screen buffer (~3KB) over USB regardless
of how many samples are requested. This is a hardware/protocol limitation.

**Verification (2026-03-15):**
Tests with `:DATA:WAVE:POINTS [100, 500, 1000]` showed that the scope always
returns exactly 3044 bytes. Software-side downsampling is the only viable path.

**Suggestions:**
- Investigate whether `:WAV:POIN` or similar SCPI commands can limit data
  transfer at the hardware level before USB transmission begins. (Update: Tested, not effective on this model).
- Consider adding an async/non-blocking capture mode so the UI stays
  responsive during acquisition. (Implemented via `asyncio.to_thread`)

### 1.2 Metadata Cache TTL is Hardcoded
The 2-second cache TTL in `get_metadata_cached()` is a magic number buried
in the method signature.

**Suggestion:**
```python
META_CACHE_TTL = 2.0  # seconds — make it a class constant or config value
```

### 1.3 No Async USB I/O
All USB operations are synchronous and block the entire MCP event loop.
Since `FastMCP` is async, blocking calls in async tool handlers can stall
other concurrent tool invocations.

**Suggestion:** Wrap blocking USB calls in `asyncio.to_thread()`:
```python
data = await asyncio.to_thread(scope.read_resp, dev, size=8192, timeout=2000)
```

---

## 2. Robustness & Error Handling

### 2.1 Silent Failures Everywhere
Most error paths return `{"error": "..."}` or an empty string with no
logging. Debugging a failing capture requires guesswork.

**Suggestion:** Add structured logging:
```python
import logging
logger = logging.getLogger("ScopeMCP")
logger.warning("USB read failed: %s", e)
```

### 2.2 USB Device Loss Not Recovered Gracefully
If the USB cable is unplugged and replugged, `get_device()` re-initializes
correctly — but any in-progress `read_resp()` call will raise an unhandled
exception that silently returns `None`.

**Suggestion:** Add explicit USB error handling with retry logic:
```python
for attempt in range(3):
    try:
        return bytes(dev.read(EP_IN, size, timeout=timeout))
    except usb.core.USBError as e:
        if attempt == 2:
            self._dev = None  # force re-init on next call
            raise
        time.sleep(0.1)
```

### 2.3 `_clear_buffer` Can Still Block
With max 3 iterations and 5ms timeout, `_clear_buffer` takes up to 15ms
per `send_cmd` call. At 5 commands per dual capture, that's 75ms of
guaranteed delay just from buffer clearing.

**Suggestion:** Only clear the buffer once before the first command of a
sequence, not before every command:
```python
def capture_dual_waveform(...):
    scope._clear_buffer(dev)  # once at the start
    for ch in [1, 2]:
        scope._send_cmd_raw(dev, ...)  # send without buffer clear
```

### 2.4 No Validation of `channel` Parameter
`capture_waveform(channel=5)` will silently send `:DATA:WAVE:SCREEN:CH5?`
to the scope with unpredictable results.

**Suggestion:**
```python
if channel not in (1, 2):
    return {"error": f"Invalid channel: {channel}. Must be 1 or 2."}
```

---

## 3. Code Quality

### 3.1 Magic Numbers
Several constants are scattered inline throughout the code:

| Value | Location | Should be |
|-------|----------|-----------|
| `250.0` | multiple places | `LSB_PER_DIV = 250.0` |
| `0x01`, `0x81` | top of file | already constants — good |
| `16384`, `8192` | read_resp calls | `USB_READ_SIZE_LARGE`, `USB_READ_SIZE_SMALL` |
| `0.05` | throttle | `CMD_THROTTLE_S = 0.05` |

### 3.2 Duplicate HEAD Request Logic
`capture_waveform` and `capture_dual_waveform` both contain identical
metadata parsing logic. This is already partially solved by
`get_metadata_cached()` — but `capture_waveform` still has its own
inline parsing fallback that duplicates the code.

**Suggestion:** Remove the inline fallback entirely and rely exclusively
on `get_metadata_cached()`.

### 3.3 `asyncio` Imported but Not Used
The file has `import asyncio` at the top but never uses it.
Either use it (see 1.3) or remove it.

### 3.4 Byte Parsing Could Be Simpler
```python
# Current:
for i in range(4, len(data)-1, 2):
    val = int.from_bytes(data[i:i+2], byteorder='little', signed=True)

# Simpler with numpy or struct:
import struct
raw = list(struct.unpack_from(f'<{(len(data)-4)//2}h', data, offset=4))
```
This is faster and less error-prone (no off-by-one risk).

---

## 4. Missing Features

### 4.1 No `capture_waveform` Result Includes Timestamp
Every measurement should include an ISO timestamp for logging/traceability:
```python
"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
```

### 4.2 No Frequency / Vpp Calculated from Raw Samples
`vpp_calc` was removed from the output. Clients (like Claude) currently
have to calculate Vpp themselves from the raw samples. The server should
provide at minimum:
- `vpp` (peak-to-peak voltage, already computed in metadata)
- `freq` (from metadata `FREQUENCE` field)
- `dc_offset` (mean voltage)

### 4.3 No `get_run_state` Tool
There is `set_run_state` (RUN/STOP) but no way to query the current state.
The metadata includes `RUNSTATUS` — expose it as a dedicated tool or
include it in every capture response.

### 4.4 No Single-Shot Trigger Support
For one-time event capture, a `capture_single_shot` tool would be very
useful: set trigger to SINGLE, wait for trigger, capture, return to AUTO.

### 4.5 No Connection Status Tool
There is no `ping` or `get_connection_status` tool. Useful for Claude to
verify the scope is connected before starting a measurement sequence.
```python
@mcp.tool()
async def get_connection_status() -> dict:
    dev = scope.get_device()
    return {"connected": dev is not None, "device": str(dev) if dev else None}
```

---

## 5. Documentation

### 5.1 `ds1102_protocol.md` Should Include the Voltage Formula
The protocol doc is referenced but the voltage conversion formula
`(raw - offset) / 250 * scale * probe` should be prominently documented
there, including the sign convention and the reason for `offset ± 100`.

### 5.2 CHANGELOG Is Good — Keep It Updated
The CHANGELOG already documents the key fixes well. Suggestion: add a
"Known Limitations" section noting the ~9s USB transfer floor.

### 5.3 No Unit Tests
Even basic sanity checks would help:
```python
# test_scaling.py
assert voltage(raw=100, offset=100, scale=0.02, probe=10) == 0.0
assert voltage(raw=350, offset=100, scale=0.02, probe=10) == 2.0
```

---

## 6. Security / Deployment

### 6.1 Hardcoded Windows Path in README
```json
"args": ["C:/Users/Tom/Oszi/ds1102_mcp.py"]
```
This should use a relative path or an environment variable in the README example.

### 6.2 No `pyproject.toml` or `setup.py`
The project could benefit from a proper Python package structure so it can
be installed via `pip install .` rather than run as a raw script.

---

## Priority Overview

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| 2.4 | Channel parameter validation | very low | high |
| 4.5 | Connection status tool | very low | high |
| 3.1 | Magic numbers → constants | low | medium |
| 4.1 | Timestamp in responses | low | medium |
| 4.2 | Vpp/freq in capture response | low | high |
| 2.1 | Structured logging | low | high |
| 1.3 | Async USB I/O | medium | high |
| 2.2 | USB reconnect retry logic | medium | high |
| 4.4 | Single-shot trigger tool | medium | high |
| 5.3 | Unit tests | medium | medium |
| 1.1 | Hardware-level sample limiting | high | very high |
