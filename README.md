<p align="center">
  <img src="resources/images/ScopeMCP_klein.png" alt="ScopeMCP Logo" width="400">
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

1. `capture_dual_waveform`: Optimized dual-channel acquisition.
2. `capture_waveform`: Single channel acquisition.
3. `set_autoset`: Automatic setup.
4. `set_vscale` / `set_hscale`: Scale adjustments.
5. `set_coupling`: AC/DC switching.
6. `set_offset`: Vertical position.
7. `set_trigger_mode` / `set_trigger_level`.
8. `get_idn`: Device identification.

## License
MIT
