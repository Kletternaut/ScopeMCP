# Changelog

## [V1.2.0] - 2026-03-15

### Performance
- Replaced all synchronous USB calls with `asyncio.to_thread()` across
  all MCP tools — reduces dual capture time from ~10.5s to ~7.2s
- Combined with previous optimizations (V1.1.0), total improvement
  vs. original: 16.1s → 7.2s (~55% faster)

### Notes
- Remaining ~7s is confirmed hardware floor (DS1102 always transfers
  3044 bytes regardless of sample count — see FINDINGS_USB_Transfer_Limit.md)

## [1.1.0] - Aktuell

### Hinzugefügt
- **Dual-Channel Capture:** Neuer optimierter Befehl `capture_dual_waveform`, der beide Kanäle in einer Operation erfasst (reduziert Wartezeit von 16s auf ~9s).
- **Downsampling:** Unterstützung für einstellbares Downsampling (`downsample_factor`) zur schnelleren Übertragung im Chat.
- **Detaillierte Fernsteuerung:** Erweiterung der Tools um Kopplung (AC/DC), Offset-Verschiebung, Trigger-Source und Trigger-Level.
- **Vertical Orientation Fix:** Invertierung der Formel (`(Offset - Raw)`) zur korrekten Darstellung von CH1 (oben) und CH2 (unten) entsprechend der Hardware-Anzeige.

### Geändert
- **Performance-Tuning:** Reduzierung der Delays für nicht-mechanische Befehle auf 100ms.
- **USB-Buffer:** Erhöhung des USB-Lesepuffers auf 32.768 Bytes für stabilere Datentransfers bei hohen Sampleraten.
- **Fehlerbehandlung:** Robusteres Parsing der Meta-Daten (`ch_info` Fix) und verbesserte Timeout-Logik (800ms).

## [1.0.0] - Vorherige Version

### Hinzugefügt
- **MCP-Server (`ds1102_mcp.py`):** FastMCP-Integration zur Oszilloskop-Steuerung über Claude Desktop.
- **Waveform-Capturing:** Automatische Erfassung von CH1 und CH2 Rohdaten.
- **Metadaten-Analyse:** Unterstützung der JSON-Metadaten für automatische Skalierung.
- **USB-Stabilitätslogik:** 1.5s Pausen nach Relais-Schaltvorgängen (`:SCALe`).

### Geändert
- **Waveform-Parsing:** Umstellung von Big-Endian auf **16-bit signed Little-Endian**. Behebt "Sinus-Matsch".
- **Kalibrierung:** Einführung des Faktors **250.0 LSB/Division** für SCREEN-Daten.

