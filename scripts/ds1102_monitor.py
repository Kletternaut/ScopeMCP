import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package
import matplotlib.pyplot as plt
import numpy as np
import json

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def send_cmd(dev, cmd):
    if not cmd.endswith("\r\n"):
        cmd += "\r\n"
    dev.write(EP_OUT, cmd.encode('ascii'))

def read_resp(dev, size=16384, timeout=1000):
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        return data.tobytes()
    except usb.core.USBError:
        return None

def parse_header(header_data):
    try:
        # Die ersten 4 Bytes sind die Länge (Little Endian)
        msg_len = int.from_bytes(header_data[:4], byteorder='little')
        json_str = header_data[4:4+msg_len].decode('ascii', errors='replace')
        return json.loads(json_str)
    except Exception as e:
        print(f"⚠️ Fehler beim Parsen des Headers: {e}")
        return None

def main():
    print("--- 📺 DS1102 Live Monitor-Modus ---")
    print("Drücke Strg+C zum Beenden.")
    
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    try:
        dev.set_configuration()
        
        # Interaktiven Plot-Modus aktivieren
        plt.ion()
        fig, ax = plt.subplots(figsize=(10, 5))
        line, = ax.plot([], [], label='CH1', color='cyan')
        ax.set_facecolor('black')
        ax.grid(color='gray', linestyle='--', alpha=0.5)
        ax.set_ylim(0, 255) # Rohdaten sind 0-255
        ax.legend()
        
        while True:
            # 1. Header für aktuelle Einstellungen holen
            send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
            header_raw = read_resp(dev)
            header = parse_header(header_raw) if header_raw else None
            
            # 2. Wellenform von CH1 holen
            send_cmd(dev, ":DATA:WAVE:SCREEN:CH1?")
            wave_raw = b""
            # Kurzes Sammeln der Daten
            for _ in range(5):
                chunk = read_resp(dev, size=8192, timeout=200)
                if chunk: wave_raw += chunk
                if len(wave_raw) > 3000: break
            
            if len(wave_raw) > 4:
                # Wir überspringen die ersten 4 Bytes (Längen-Header des Datenpakets)
                samples = np.frombuffer(wave_raw[4:], dtype=np.uint8)
                
                # Plot aktualisieren
                line.set_data(np.arange(len(samples)), samples)
                ax.set_xlim(0, len(samples))
                
                if header:
                    # Zeitbasis und Volt/Div aus dem Header anzeigen
                    tb = header.get("TIMEBASE", {}).get("SCALE", "?")
                    ch1_v = header.get("CH1", {}).get("SCALE", "?")
                    ax.set_title(f"DS1102 Live - TB: {tb} | CH1: {ch1_v}")
                
                fig.canvas.draw()
                fig.canvas.flush_events()
                
            time.sleep(0.1) # Kurze Pause zur Entlastung

    except KeyboardInterrupt:
        print("\n🛑 Monitor beendet.")
    except Exception as e:
        print(f"💥 Fehler: {e}")
    finally:
        plt.ioff()
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
