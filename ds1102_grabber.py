"""
ScopeMCP
Copyright (c) 2026 Kletternaut

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SPDX-License-Identifier: GPL-3.0-or-later
"""
import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package
import json
import matplotlib.pyplot as plt
import numpy as np
from ds1102_logic import decode_and_convert, parse_scale_to_volts, LSB_PER_DIV

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81


def _clear_buffer(dev):
    """Leert den USB-Eingangspuffer."""
    for _ in range(5):
        try:
            dev.read(EP_IN, 8192, timeout=10)
        except:
            break


def send_cmd(dev, cmd, clear_buffer=True):
    """Sendet Befehl im Owon-Binaer-Format (4-Byte Header + ASCII-Cmd + LF)."""
    if clear_buffer:
        _clear_buffer(dev)
    
    if not cmd.startswith(":"):
        cmd = ":" + cmd
    if not cmd.endswith("\n"):
        cmd += "\n"

    cmd_bytes = cmd.encode("ascii")
    length_header = len(cmd_bytes).to_bytes(4, byteorder="little")
    packet = length_header + cmd_bytes

    print(f"Sende: {cmd.strip()}")
    try:
        dev.write(EP_OUT, packet)
    except usb.core.USBError as e:
        print(f"USB Write Error: {e}")
        raise
    
    # Kurze Pause nach dem Schreiben, damit das Gerät Zeit zum Reagieren hat
    time.sleep(0.05)


def read_resp(dev, size=16384, timeout=2000):
    """Liest Antwort vom Geraet (Owon-Format)."""
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        if not data:
            return None
        return bytes(data)
    except usb.core.USBError as e:
        if "timeout" not in str(e).lower():
            print(f"Read Error: {e}")
        return None


# decode_waveform und parse_vscale wurden durch ds1102_logic.py ersetzt:
#   - parse_raw_samples()    -> Little-Endian '<i2' (vorher fehlerhaft Big-Endian '>i2')
#   - parse_scale_to_volts() -> robusteres Parsen von 'mV'/'V'-Strings
#   - decode_and_convert()   -> kombinierter Wrapper inkl. verifizierter Volt-Formel


def on_key(event, dev):
    """Event-Handler fuer Tastenbefehle im Plot-Fenster."""
    if event.key == 'a':
        print("Sende AUTOSET...")
        send_cmd(dev, "AUToset on")
    elif event.key == 's':
        print("Sende STOP...")
        send_cmd(dev, "RUNning STOP")
    elif event.key == 'r':
        print("Sende RUN...")
        send_cmd(dev, "RUNning RUN")


def main():
    print("--- DS1102 Live Monitor (Volt Mode) ---")
    print("Tasten: [A] Autoset | [S] Stop | [R] Run")
    try:
        backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        print(f"Backend geladen: {backend is not None}")
        dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
        print(f"Device gefunden: {dev is not None}")
    except Exception as be_err:
        print(f"Fehler beim Laden von Backend/Device: {be_err}")
        return

    if dev is None:
        print("Geraet nicht gefunden. Ist das Oszi angeschaltet und per USB verbunden?")
        return

    try:
        dev.set_configuration()
        print("set_configuration erfolgreich.")

        plt.ion()
        # Subplots übereinander für CH1 und CH2
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        fig.canvas.mpl_connect('key_press_event', lambda event: on_key(event, dev))

        line1, = ax1.plot([], [], color='yellow', label='CH1')
        ax1.grid(True, which='both', linestyle='--', alpha=0.5)
        ax1.legend(loc='upper right')
        # Einheitenlabels entfernen
        ax1.set_yticklabels([])
        ax1.set_xticklabels([])

        line2, = ax2.plot([], [], color='cyan', label='CH2')
        ax2.set_xlabel("Zeit (Divisions)")
        ax2.grid(True, which='both', linestyle='--', alpha=0.5)
        ax2.legend(loc='upper right')
        # Einheitenlabels entfernen
        ax2.set_yticklabels([])
        ax2.set_xticklabels([])

        # 1. Handshake
        send_cmd(dev, "MODel?", clear_buffer=True)
        resp = read_resp(dev, timeout=2000)
        if resp:
            print(f"Oszilloskop erkannt: {repr(resp[:30])}...")
        else:
            print("Keine Antwort auf :MODel? - Handshake fehlgeschlagen.")

        print("\nStarte Live-Monitor. Schliesse das Fenster zum Beenden.")

        while plt.fignum_exists(fig.number):
            # 2. Header abfragen (Metadaten für beide Kanäle)
            send_cmd(dev, "DATA:WAVE:SCREEN:HEAD?", clear_buffer=True)
            header_raw = read_resp(dev, timeout=2000)

            meta = None
            if header_raw:
                json_start = header_raw.find(b'{')
                if json_start != -1:
                    json_end = header_raw.rfind(b'}')
                    if json_end != -1:
                        try:
                            json_data = header_raw[json_start:json_end+1].decode('ascii', errors='ignore')
                            meta = json.loads(json_data)
                        except Exception as je:
                            print(f"JSON Parse Error: {je}")

            if not meta:
                time.sleep(0.5)
                continue

            # Beide Kanäle nacheinander abfragen
            for i, ch_num in enumerate([1, 2]):
                if not meta or 'CHANNEL' not in meta or len(meta['CHANNEL']) <= i:
                    continue
                
                ch_meta = meta['CHANNEL'][i]
                current_ax = ax1 if ch_num == 1 else ax2
                current_line = line1 if ch_num == 1 else line2
                
                # Nur aktive Kanäle anzeigen
                if ch_meta.get('DISPLAY', 'OFF') == 'OFF':
                    current_line.set_data([], [])
                    current_ax.set_title(f"CH{ch_num} (OFF)")
                    continue

                v_scale_str = ch_meta.get('SCALE', '1.00V')
                v_scale = parse_scale_to_volts(v_scale_str)
                offset = float(ch_meta.get('OFFSET', 0))
                
                # Robustes Probe-Parsing
                probe_raw = str(ch_meta.get("PROBE", "1.0")).upper()
                if probe_raw.endswith("X"):
                    probe_raw = probe_raw[:-1]
                try:
                    probe = float(probe_raw)
                except:
                    probe = 1.0

                # Wellenform abfragen
                send_cmd(dev, f"DATA:WAVE:SCREEN:CH{ch_num}?", clear_buffer=False)
                wave_raw = read_resp(dev, size=16384, timeout=2500)

                if wave_raw and len(wave_raw) > 10:
                    volt_data = decode_and_convert(wave_raw, offset, v_scale, probe)

                    if volt_data is not None and len(volt_data) > 0:
                        current_line.set_data(np.arange(len(volt_data)), volt_data)
                        
                        # Vertikale Zentrierung und Raster-Anpassung
                        # Die v_scale (z.B. 0.5V) mal probe (z.B. 10x) ergibt die echten Volt pro Kästchen (5V/div).
                        volts_per_div = v_scale * probe
                        
                        # Wir zeigen 10 Divisions total (+5/-5)
                        divs_half = 5
                        limit = volts_per_div * divs_half
                        
                        current_ax.set_ylim(-limit, limit)
                        
                        # Fix für die Raster-Einheiten (Grid Ticks):
                        # Wir erzwingen Ticks bei jedem Divisions-Schritt (volts_per_div)
                        from matplotlib.ticker import MultipleLocator
                        current_ax.yaxis.set_major_locator(MultipleLocator(volts_per_div))
                        # Horizontale Ticks (X-Achse) für Zeit-Divisions (ca. 150 Samples pro Div bei Standard-Timebase)
                        current_ax.xaxis.set_major_locator(MultipleLocator(150))
                        
                        current_ax.set_title(f"CH{ch_num}: {v_scale_str} (Probe x{probe})")

            ax2.set_xlim(0, 1520)
            fig.canvas.draw_idle()
            plt.pause(0.01)

            time.sleep(0.1)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Monitor gestoppt: {e}")
    finally:
        plt.ioff()
        print("Monitor beendet.")


if __name__ == "__main__":
    main()
