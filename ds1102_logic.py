"""
ds1102_logic.py – Zentrale Rechen- und Dekodierlogik für das DS1102 Oszilloskop.

Kapselt alle hardware-spezifischen Konstanten und Berechnungen an einem Ort,
damit grabber.py und mcp.py identische, korrekte Ergebnisse liefern.

Korrekte Formel (ermittelt durch Reverse-Engineering, Firmware V3.1.0, SCREEN-Modus):
    voltage = (GridOffset - raw) / LSB_PER_DIV * scale_V * probe_factor

Bekannte Fehlerquellen der alten Implementierungen:
    - grabber.py (alt): Big-Endian ('>i2'), kein GridOffset, Divisor 100  → Faktor-2.5-Fehler
    - mcp.py (alt):     instruction-String hatte Vorzeichen vertauscht (raw - offset)
"""

import numpy as np

# ---------------------------------------------------------------------------
# Hardware-Konstanten (DS1102, Firmware V3.1.0, SCREEN-Modus)
# ---------------------------------------------------------------------------

LSB_PER_DIV: float = 250.0
"""Anzahl der LSB (Least Significant Bits) pro Bildschirm-Division.
Gemessen durch Kalibrierung gegen bekannte Signale im SCREEN-Modus.
Gilt NUR für ':DATA:WAVE:SCREEN:CH*?' – nicht für Deep-Memory-Modus."""

HEADER_SIZE: int = 4
"""Anzahl der Bytes des binären Antwort-Headers, der vor den Nutzdaten steht.
Inhalt: 4-Byte Little-Endian Längenangabe der folgenden Nutzdaten."""

SAMPLES_PER_SCREEN: int = 1520
"""Feste Anzahl der Samples pro Kanal im SCREEN-Modus (= 3040 Byte / 2)."""

VOLTAGE_FORMULA: str = "voltage = (GridOffset - raw) / 250.0 * scale_v * probe_factor"
"""Kanonische Formel als String – zur Weitergabe an KI-Agenten (z.B. MCP instruction-Feld).

Vorzeichen-Konvention: (GridOffset - raw), NICHT (raw - GridOffset).
Groessere Rohwerte liegen auf dem DS1102-Display weiter unten (invertierte Y-Achse)."""


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def parse_scale_to_volts(scale_str: str) -> float:
    """Wandelt einen Skalenstring aus dem Geräte-JSON in Volt (float) um.

    Unterstützte Formate: '2.00V', '500mV'

    Args:
        scale_str: Rohstring aus meta['CHANNEL'][n]['SCALE'].

    Returns:
        Skalenwert in Volt. Gibt 1.0 zurück, wenn das Parsen fehlschlägt.

    Examples:
        >>> parse_scale_to_volts('2.00V')
        2.0
        >>> parse_scale_to_volts('500mV')
        0.5
    """
    try:
        if scale_str.endswith('mV'):
            return float(scale_str[:-2]) / 1000.0
        if scale_str.endswith('V'):
            return float(scale_str[:-1])
    except (ValueError, AttributeError):
        pass
    return 1.0


def parse_raw_samples(raw_data: bytes) -> np.ndarray | None:
    """Dekodiert die binäre Geräteantwort in ein NumPy-Array von Rohwerten.

    Überspringt den 4-Byte-Header und interpretiert die verbleibenden Bytes
    als vorzeichenbehaftete 16-Bit Integer in Little-Endian-Reihenfolge
    (dtype '<i2'). Dies entspricht dem verifizierten Binärformat der
    DS1102-Firmware V3.1.0.

    Args:
        raw_data: Rohe Bytes der USB-Geräteantwort (Header + Nutzdaten).

    Returns:
        NumPy-Array (dtype int16) der Rohsamples, oder None bei Fehler
        bzw. zu wenig Daten.
    """
    if not raw_data or len(raw_data) <= HEADER_SIZE:
        return None
    payload = raw_data[HEADER_SIZE:]
    # Ungerade Byte-Anzahl abschneiden, um vollständige 2-Byte-Paare zu garantieren
    usable = len(payload) - (len(payload) % 2)
    if usable == 0:
        return None
    try:
        # Little-Endian signed 16-bit – verifiziert für DS1102 V3.1.0
        return np.frombuffer(payload[:usable], dtype='<i2')
    except ValueError:
        return None


def samples_to_volts(
    samples: np.ndarray,
    grid_offset: float,
    scale_v: float,
    probe_factor: float = 1.0,
) -> np.ndarray:
    """Rechnet Rohsamples in physikalische Spannungswerte (Volt) um.

    Formel:
        voltage = (GridOffset - raw) / LSB_PER_DIV * scale_v * probe_factor

    Das Vorzeichen (GridOffset - raw) ist entscheidend:
    - Ein positiver Rohwert ÜBER dem GridOffset entspricht einer negativen
      Spannung (Zeiger zeigt nach unten auf dem Schirm).
    - Ein positiver Rohwert UNTER dem GridOffset entspricht einer positiven
      Spannung (Zeiger zeigt nach oben).
    Dies spiegelt die interne Koordinatenkonvention der DS1102-Hardware wider.

    Args:
        samples:      Rohsamples als NumPy-Array (int16 oder float).
        grid_offset:  GridOffset-Wert aus den JSON-Metadaten des Geräts
                      (meta['CHANNEL'][n]['GRID_OFF'] o.ä.).
                      Repräsentiert den Rohwert, der 0 V auf dem Bildschirm entspricht.
        scale_v:      Vertikalskalierung in Volt/Division (z.B. 1.0 für 1V/Div).
                      Verwende parse_scale_to_volts() zum Umwandeln des JSON-Strings.
        probe_factor: Tastteiler-Faktor (Standard 1.0; bei 10:1-Tastkopf: 10.0).

    Returns:
        NumPy-Array (float64) der berechneten Spannungswerte in Volt.
    """
    return (grid_offset - samples.astype(np.float64)) / LSB_PER_DIV * scale_v * probe_factor


def decode_and_convert(
    raw_data: bytes,
    grid_offset: float,
    scale_v: float,
    probe_factor: float = 1.0,
) -> np.ndarray | None:
    """Kombinierter Einzeiler: Rohdaten → Volt-Array.

    Convenience-Wrapper, der parse_raw_samples() und samples_to_volts()
    hintereinander aufruft. Gedacht für den Live-Monitor (grabber.py), wo
    beide Schritte immer zusammen benötigt werden.

    Args:
        raw_data:     Rohe USB-Antwortbytes.
        grid_offset:  GridOffset aus den JSON-Metadaten.
        scale_v:      Vertikalskalierung in V/Div.
        probe_factor: Tastteiler-Faktor.

    Returns:
        NumPy-Array (float64) in Volt, oder None bei Dekodierungsfehler.
    """
    samples = parse_raw_samples(raw_data)
    if samples is None:
        return None
    return samples_to_volts(samples, grid_offset, scale_v, probe_factor)
