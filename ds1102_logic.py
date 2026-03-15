"""
ds1102_logic.py - Zentrale Rechen- und Dekodierlogik fuer das DS1102 Oszilloskop.

Kapselt alle hardware-spezifischen Konstanten und Berechnungen an einem Ort,
damit grabber.py und mcp.py identische, korrekte Ergebnisse liefern.

Korrekte Formel (verifiziert durch Live-Test gegen Firmware V3.1.0, SCREEN-Modus):
    voltage = (raw - OFFSET) / LSB_PER_DIV * scale_v * probe_factor

    OFFSET: meta['CHANNEL'][n]['OFFSET'] - Integer aus dem Firmware-JSON.
            Verifizierter Key-Name: 'OFFSET' (nicht 'GRID_OFF').

Entwicklungshistorie der Formel:
    - grabber.py V1:  (raw / 100.0) * scale         - falscher Divisor, kein Offset
    - mcp.py     V1:  (raw - offset) / 250 * scale  - richtiges Vorzeichen, falscher Key
    - logic.py   V1:  (GRID_OFF - raw) / 250        - falscher Key, invertiertes Vorzeichen
    - logic.py   V2:  (raw - OFFSET) / 250          - verifiziert korrekt (dieser Stand)
"""

import numpy as np

# ---------------------------------------------------------------------------
# Hardware-Konstanten (DS1102, Firmware V3.1.0, SCREEN-Modus)
# ---------------------------------------------------------------------------

LSB_PER_DIV: float = 250.0
"""Anzahl der LSB pro Bildschirm-Division im SCREEN-Modus.
Durch Kalibrierung gegen bekannte Signale ermittelt.
Gilt NICHT fuer den Deep-Memory-Modus."""

HEADER_SIZE: int = 4
"""Groesse des binaeren Antwort-Headers in Bytes.
Inhalt: 4-Byte Little-Endian Laengenangabe der folgenden Nutzdaten."""

SAMPLES_PER_SCREEN: int = 1520
"""Feste Sample-Anzahl pro Kanal im SCREEN-Modus (3040 Byte / 2 Byte pro Sample)."""

VOLTAGE_FORMULA: str = "voltage = (raw - OFFSET) / 250.0 * scale_v * probe_factor"
"""Kanonische Formel als String - zur Weitergabe an KI-Agenten (MCP instruction-Feld).

Verifiziert durch Live-Test (Firmware V3.1.0):
  Key:        meta['CHANNEL'][n]['OFFSET']  (Integer, z.B. 0, 100, -100)
  Vorzeichen: (raw - OFFSET), NICHT (OFFSET - raw)
  Beispiel:   raw=992, OFFSET=0, scale=0.2V, probe=10 -> +7.94V (Rechteck HIGH)"""


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def parse_scale_to_volts(scale_str: str) -> float:
    """Wandelt einen Skalenstring aus dem Geraete-JSON in Volt (float) um.

    Unterstuetzte Formate: '2.00V', '500mV'

    Args:
        scale_str: Rohstring aus meta['CHANNEL'][n]['SCALE'].

    Returns:
        Skalenwert in Volt. Gibt 1.0 zurueck wenn das Parsen fehlschlaegt.

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
    """Dekodiert die binaere Geraeteantwort in ein NumPy-Array von Rohwerten.

    Ueberspringt den 4-Byte-Header und interpretiert die verbleibenden Bytes
    als vorzeichenbehaftete 16-Bit Integer in Little-Endian (dtype '<i2').
    Verifiziert fuer DS1102 Firmware V3.1.0.

    Args:
        raw_data: Rohe Bytes der USB-Geraeteantwort (Header + Nutzdaten).

    Returns:
        NumPy-Array (dtype int16) der Rohsamples, oder None bei Fehler.
    """
    if not raw_data or len(raw_data) <= HEADER_SIZE:
        return None
    payload = raw_data[HEADER_SIZE:]
    usable = len(payload) - (len(payload) % 2)
    if usable == 0:
        return None
    try:
        return np.frombuffer(payload[:usable], dtype='<i2')
    except ValueError:
        return None


def samples_to_volts(
    samples: np.ndarray,
    offset: float,
    scale_v: float,
    probe_factor: float = 1.0,
) -> np.ndarray:
    """Rechnet Rohsamples in physikalische Spannungswerte (Volt) um.

    Formel (verifiziert gegen DS1102 Firmware V3.1.0):
        voltage = (raw - OFFSET) / LSB_PER_DIV * scale_v * probe_factor

    Args:
        samples:      Rohsamples als NumPy-Array (int16 oder float).
        offset:       Wert aus meta['CHANNEL'][n]['OFFSET'].
                      Bei OFFSET=0 und raw=992: (992-0)/250*0.2*10 = +7.94V.
        scale_v:      Vertikalskalierung in Volt/Division (z.B. 0.2 fuer 200mV/Div).
        probe_factor: Tastteiler-Faktor (Standard 1.0; 10x-Tastkopf -> 10.0).

    Returns:
        NumPy-Array (float64) der berechneten Spannungswerte in Volt.
    """
    return (samples.astype(np.float64) - offset) / LSB_PER_DIV * scale_v * probe_factor


def decode_and_convert(
    raw_data: bytes,
    offset: float,
    scale_v: float,
    probe_factor: float = 1.0,
) -> np.ndarray | None:
    """Kombinierter Einzeiler: Rohdaten -> Volt-Array.

    Convenience-Wrapper fuer grabber.py: parse_raw_samples() + samples_to_volts().

    Args:
        raw_data:     Rohe USB-Antwortbytes (Header + Nutzdaten).
        offset:       Wert aus meta['CHANNEL'][n]['OFFSET'].
        scale_v:      Vertikalskalierung in V/Div.
        probe_factor: Tastteiler-Faktor.

    Returns:
        NumPy-Array (float64) in Volt, oder None bei Dekodierungsfehler.
    """
    samples = parse_raw_samples(raw_data)
    if samples is None:
        return None
    return samples_to_volts(samples, offset, scale_v, probe_factor)
