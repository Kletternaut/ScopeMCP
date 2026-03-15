<p align="center">
  <img src="resources/images/ScopeMCP_klein.png" alt="ScopeMCP Logo" width="200">
</p>

# DS1102 Scope MCP Server (Abestop/Owon V3.1.0)

**DS1102 Scope MCP Server** is a high-performance Python-based bridge that integrates the **Owon/Abestop DS1102 (Firmware V3.1.0)** oscilloscope into the **Model Context Protocol (MCP)** ecosystem.

## Key Features (V1.1.0)

- **AI-Native Control**: AI agents can execute `Autoset`, toggle `RUN/STOP` states, and adjust vertical/horizontal scales through natural language.
- **Precision 16-bit Data Capture**: Direct extraction of signed 16-bit Little-Endian waveform data. Fixed "Sinus-Matsch" and vertical inversion issues.
- **Optimized Dual-Channel Tool**: `capture_dual_waveform` reduces capture time from ~16s to ~9s by batching SCPI commands and optimizing USB buffering (32KB).
- **Exact Amplitude Calibration**: Integrated 250.0 LSB/Division scaling factor specifically for SCREEN data mode.
- **Low-Latency Performance**: Optimized internal delays (100ms for non-relay commands) and increased USB timeouts.

## Installation & Setup

1. **Python 3.10+** and **libusb-Backend** (e.g., libusb-win32 via Zadig on Windows).
2. **Dependencies**: 
   ```bash
   pip install mcp libusb-package pyusb
   ```
3. **Claude Desktop Integration**:
   Add to `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "ds1102-scope": {
         "command": "python",
         "args": ["C:/Users/Tom/Oszi/ds1102_mcp.py"]
       }
     }
   }
   ```

## Protocol Details (Firmware V3.1.0)

- **Binary Header**: Every SCPI command is prefixed with a 4-byte Little-Endian length field.
- **Terminator**: All commands MUST end with `\n` (0x0A).
- **Data Scaling**: 
  - `voltage = ((GridOffset - RawValue) / 250.0) * Scale * Probe`
  - SCREEN data provides 1520 samples per channel.
- **Mechanical Delays**: A 1.5s delay is automatically applied after `:SCALe` commands for relay safety.

## Available MCP Tools

1. `capture_dual_waveform`: Optimized dual-channel acquisition (saves ~50% time).
2. `capture_waveform`: Single channel acquisition with downsampling.
3. `get_live_metadata`: Full JSON metadata (Freq, Vpp, Settings).
4. `run_autoset`: Automatic setup of all parameters.
5. `set_vertical_scale` / `set_horizontal_scale`: Scale adjustments.
6. `set_channel_coupling`: AC/DC/GND switching.
7. `set_voltage_offset`: Vertical position adjustment (in Volts).
8. `set_trigger_mode` / `set_trigger_slope` / `set_trigger_source`: Trigger configuration.
9. `set_run_state`: Toggle between RUN and STOP.

## License
MIT
