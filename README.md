# ScopeMCP — DS1102 Oscilloscope MCP Server

<p align="center">
  <img src="resources/images/ScopeMCP_klein.png" alt="ScopeMCP Logo" width="200">
</p>

A Python MCP server that connects the [**Owon/Abestop DS1102 (Firmware V3.1.0)**](resources/images/Abestop_DS1102.jpg) oscilloscope (Firmware V3.1.0) to AI assistants like Claude via the [Model Context Protocol](https://modelcontextprotocol.io/).



---

## Requirements

- Python 3.10+
- libusb backend (on Windows: install via [Zadig](https://zadig.akeo.ie/))
- DS1102 connected via USB

```bash
pip install mcp libusb-package pyusb
```

---

## Setup

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ds1102-scope": {
      "command": "python",
      "args": ["C:/path/to/ds1102_mcp.py"]
    }
  }
}
```

---

## Available Tools

### Status & Metadata
- `get_connection_status`: Checks connection, model, run status, and timestamp.
- `get_live_metadata`: Returns full device metadata (timebase, sample rate, channel/trigger config).
- `get_measurements`: Provides frequency, period, scale, probe factor, and coupling for both channels.

### Waveform Capture
- `capture_waveform(channel, max_samples)`: Captures a single channel (fixed at 1520 hardware samples, software downsampled).
- `capture_dual_waveform(max_samples)`: Efficiently captures both channels in a single operation.

**Voltage conversion formula**:
```
voltage = (raw - OFFSET) / 250.0 * scale_v * probe_factor
```

> **Note:** The DS1102 always transfers 1520 samples over USB. Downsampling occurs in software.

### Vertical & Horizontal Control
- `set_vertical_scale(channel, scale)`: e.g., "1V", "500mV".
- `set_channel_coupling(channel, coupling)`: AC, DC, or GND.
- `set_voltage_offset(channel, offset)`: Vertical position in Volts.
- `set_horizontal_scale(scale)`: e.g., "1ms", "500us".

### Trigger & Device Control
- `set_trigger_mode(mode)`: AUTO, NORMAL, SINGLE.
- `set_trigger_source(source)`: CH1, CH2.
- `set_trigger_slope(slope)`: RISE, FALL.
- `set_trigger_level(level_mv)`: Threshold in millivolts (e.g., 500.0 for 0.5V).
- `set_run_state(state)`: RUN or STOP.
- `run_autoset()`: Performs automatic oscilloscope setup.

---

## Known Limitations

- **Capture speed (~7–10s):** The DS1102 always transfers the full 1520-sample buffer over USB. The `:DATA:WAVE:POINTS` SCPI command has no effect on transfer size for this firmware. This is a confirmed hardware limitation — see `FINDINGS_USB_Transfer_Limit.md`.
- **`run_status` never shows `STOP`:** The firmware always reports `TRIG` in the status field, even when stopped. This is a firmware behavior, not a server bug.
- **CH2 returns zeros when `DISPLAY: OFF`:** No signal data is available from a channel that is disabled on the scope.

---

## Protocol Notes (Firmware V3.1.0)

- Every SCPI command is prefixed with a **4-byte little-endian length header**.
- Commands must end with `\n` (0x0A).
- Screen data: 1520 samples × 2 bytes signed 16-bit little-endian = 3040 bytes + 4-byte header.
- Full protocol details: see `ds1102_protocol.md`.

---

## License

MIT
