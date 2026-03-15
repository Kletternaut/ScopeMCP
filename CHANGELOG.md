# Changelog

## [1.0.0] - 2026-03-15

### Hinzugefügt
- **MCP-Server (`ds1102_mcp.py`):** Vollständige FastMCP-Integration zur Oszilloskop-Steuerung über Claude Desktop.
- **Waveform-Capturing:** Automatische Erfassung von CH1 und CH2 Rohdaten (1520 Samples).
- **Metadaten-Analyse:** Unterstützung der JSON-Metadaten für automatische Skalierung (`PROBE` 1X/10X, `SCALE`).
- **USB-Stabilitätslogik:** 1.5s Pausen nach Relais-Schaltvorgängen (`:SCALe`) und Buffer-Flush vor Lesezugriffen.

### Geändert
- **Waveform-Parsing:** Umstellung von Big-Endian auf **16-bit signed Little-Endian**. Behebt "Sinus-Matsch" bei Rechteck-Signalen.
- **Kalibrierung:** Neuer Kalibrierungsfaktor **250.0 LSB/Division** basierend auf Werksreset-Parametern.
- **Paket-Struktur:** Korrektur des 4-Byte binären Headers in den Wellenform-Datenpaketen.

### Behoben
- **USB-Timeouts:** Behebt Hänger nach horizontaler/vertikaler Skalierungsänderung durch optimierte Wartezeiten.
- **Daten-Länge:** Korrektur der SAMPLE-Anzahl Erkennung auf nun konstant 1520 Samples pro Kanal.
