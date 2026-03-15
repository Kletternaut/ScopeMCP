# DS1102 Scope MCP Server ([Abestop/Owon SDS1102](resources/images/Abestop_DS1102.jpg) V3.1.0)

<p align="center">
  <img src="resources/images/ScopeMCP_klein.png" alt="ScopeMCP Logo" width="200">
</p>

**DS1102 Scope MCP Server** is a high-performance Python-based bridge that integrates the **Owon/Abestop DS1102 (Firmware V3.1.0)** oscilloscope into the **Model Context Protocol (MCP)** ecosystem.

## Key Features (V1.2.0)

- **AI-Native Control**: AI agents can execute `Autoset`, toggle `RUN/STOP` states, and adjust vertical/horizontal scales through natural language.
- **Async USB Architecture**: All hardware I/O is offloaded via `asyncio.to_thread()`, keeping the MCP event loop responsive.
- **Precision 16-bit Parsing**: Optimized `struct.unpack` extraction of signed 16-bit waveform data.
- **Metadata Caching**: Smart 2.0s TTL cache for oscilloscope settings, reducing redundant USB roundtrips.
- **Robust Error Handling**: Automatic USB re-initialization on disconnect and structured logging.
- **Optimized Dual-Channel Tool**: Combined hardware and software optimizations reduce capture time by ~55% (16s → ~7s).
- **Exact Amplitude Calibration**: Integrated 250.0 LSB/Division scaling factor specifically for SCREEN data mode.

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
- **Async I/O**: USB operations run in dedicated threads to prevent blocking.

## Available MCP Tools

1. `capture_dual_waveform`: Optimized dual-channel acquisition (saves ~55% time).
2. `capture_waveform`: Single channel acquisition with ISO timestamp and full metadata.
3. `get_measurements`: Structured calculation of Freq, Period, Vpp, and RMS.
4. `get_live_metadata`: Full JSON metadata with smart caching.
5. `set_trigger_level`: High-precision trigger threshold setting (mV).
6. `get_connection_status`: Quick health check and IDN identification.
7. `run_autoset`: Automatic setup of all parameters.
8. `set_vertical_scale` / `set_horizontal_scale`: Scale adjustments with validation.
9. `set_channel_coupling`: AC/DC/GND switching.
10. `set_voltage_offset`: Vertical position adjustment (in Volts).
11. `set_trigger_mode` / `set_trigger_slope` / `set_trigger_source`: Trigger configuration.
12. `set_run_state`: Toggle between RUN and STOP.

## License
MIT
