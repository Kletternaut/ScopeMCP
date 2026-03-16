# Changelog

## [V1.2.1] - 2026-03-16

### Fixed
- **Amplitude Scaling**: Added explicit `probe` factor to `capture_waveform` and `capture_dual_waveform` results to fix CH2 low-amplitude issues.
- **Documentation**: Fixed broken protocol link in `README.md`.

### Changed
- **Legal**: Migrated project license from MIT to **GNU GPLv3**.
- **Documentation**: Major `README.md` restructure for better clarity, including new tool lists and firmware findings.
- **Logo**: Centered and resized logo for better presentation.
- **UX**: Reordered README sections to show available tools immediately after the introduction.

### Added
- **License**: Added official `LICENSE` file (GNU GPLv3).

## [V1.2.0] - 2026-03-15

### Added
- **Measurement Tool**: New `get_measurements` tool for direct hardware extraction of Freq, Vpp, and RMS.
- **Trigger Level**: New `set_trigger_level` tool for high-precision mV settings.
- **Connection Status**: Added `get_connection_status` for quick hardware health checks.
- **Timestamping**: Integrated ISO timestamps in all capture result structures.
- **Validation**: Strict parameter checking for channels, trigger modes, and slopes.

### Performance & Robustness
- **Async I/O**: Fully migrated to `asyncio.to_thread()` for all hardware USB operations.
- **Fast Parsing**: Refactored waveform data extraction using `struct.unpack`.
- **Metadata Cache**: Implemented a smart 2.0s TTL cache to reduce USB latency.
- **USB Recovery**: Added automatic re-initialization logic to recover from device disconnects.
- **Logging**: Integrated Python's `logging` module for structured error tracking.
- **Buffer Optimization**: Improved buffer clearing cycles for reduced tool response times.

## [1.1.0] - Previous

### Added
- **Dual-Channel Capture:** Optimized `capture_dual_waveform` reducing acquisition time from 16s to ~7-9s.
- **Downsampling:** Support for adjustable `downsample_factor` to speed up chat-side rendering.
- **Remote Control Suite:** Added tools for Coupling (AC/DC), Offset adjustment, and Trigger source.
- **Vertical Orientation Fix:** Reversed scaling formula (`(Offset - Raw)`) to match hardware display (CH1 top, CH2 bottom).

### Changed
- **Performance Tuning:** Reduced non-mechanical command delays to 50-100ms.
- **USB Buffering:** Increased read buffer to 32KB for stable high-sample-rate transfers.
- **Error Handling:** Robust metadata parsing (`ch_info` fix) and improved timeout logic (800ms).

## [1.0.0] - Initial Release

### Added
- **MCP Server (`ds1102_mcp.py`):** Full FastMCP integration for Claude Desktop.
- **Waveform Capturing:** Automatic binary capture for CH1 and CH2.
- **Metadata Analysis:** JSON-based extraction of scale, probe, and timebase settings.
- **Relay Safety:** Automatic 1.5s delay after mechanical relay switching (`:SCALe`).

### Changed
- **Waveform Parsing:** Migrated from Big-Endian to **16-bit signed Little-Endian** (fixes "sinus-mats" issues).
- **Calibration:** Established **250.0 LSB/Division** scaling factor for SCREEN-mode data.

