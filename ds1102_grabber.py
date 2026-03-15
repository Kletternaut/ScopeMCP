import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package
import json
import matplotlib.pyplot as plt
import numpy as np

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def send_cmd(dev, cmd):
    if not cmd.endswith("\r\n"):
        cmd += "\r\n"
    print(f"📡 Sende: {repr(cmd)}")
    dev.write(EP_OUT, cmd.encode('ascii'))
    time.sleep(0.2)

def read_resp(dev, size=4096, timeout=1500):
    try:
        full_data = b""
        while True:
            chunk = dev.read(EP_IN, size, timeout=timeout)
            full_data += chunk.tobytes()
            if len(chunk) < size:
                break
            timeout = 500
        return full_data
    except usb.core.USBError as e:
        if not full_data:
            print(f"⏳ Timeout oder Fehler: {e}")
            return None
        return full_data

def decode_waveform(raw_data):
    if len(raw_data) < 4:
        return None
    # Header überspringen (: \x03 \x00 \x00)
    samples_raw = raw_data[4:]
    try:
        # Owon nutzt oft Big Endian (>i2) für 16-Bit
        samples = np.frombuffer(samples_raw, dtype='>i2')
        return samples
    except Exception as e:
        print(f"❌ Fehler beim Dekodieren: {e}")
        return None

def parse_vscale(v_scale_str):
    """Wandelt '2.00V' oder '500mV' in einen Float-Faktor um."""
    try:
        val = float(v_scale_str[:-1]) # Entfernt 'V' oder 'mV' am Ende
        if v_scale_str.endswith('mV'):
            return val / 1000.0
        return val
    except:
        return 1.0

def on_key(event, dev):
    """Event-Handler für Tastenbefehle im Plot-Fenster."""
    if event.key == 'a':
        print("🚀 Sende AUTOSET...")
        send_cmd(dev, ":AUToset on")
    elif event.key == 's':
        print("🛑 Sende STOP...")
        send_cmd(dev, ":RUNning STOP")
    elif event.key == 'r':
        print("▶️ Sende RUN...")
        send_cmd(dev, ":RUNning RUN")

def main():
    print("--- 📈 DS1102 Live Monitor (Volt Mode) ---")
    print("Tasten: [A] Autoset | [S] Stop | [R] Run")
    try:
        backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        print(f"DEBUG: Backend geladen: {backend is not None}")
        dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
        print(f"DEBUG: Device gefunden: {dev is not None}")
    except Exception as be_err:
        print(f"❌ Fehler beim Laden von Backend/Device: {be_err}")
        return
    
    if dev is None:
        print("❌ Gerät nicht gefunden. Ist das Oszi angeschaltet und per USB verbunden?")
        return

    try:
        print("DEBUG: Versuche set_configuration...")
        dev.set_configuration()
        print("DEBUG: set_configuration erfolgreich.")
        
        # Plot-Setup für Live-Updates
        plt.ion() 
        fig, ax = plt.subplots(figsize=(10, 5))
        print("DEBUG: Matplotlib Fenster erstellt.")
        
        # KEY-Hitcher für interaktive Befehle
        fig.canvas.mpl_connect('key_press_event', lambda event: on_key(event, dev))
        
        line, = ax.plot([], [])
        ax.set_ylim(-5, 5) # Erster Schätzwert für Volt-Achse
        ax.grid(True)
        ax.set_xlabel("Zeit (Samples)")
        ax.set_ylabel("Spannung (V)")

        # 1. Identifikation / Handshake (einmalig)
        send_cmd(dev, ":MODel?")
        resp = read_resp(dev)
        if resp:
            print(f"✅ Oszilloskop erkannt: {repr(resp[:30])}...")
        else:
            print("⚠️ Keine Antwort auf :MODel? - Handshake fehlgeschlagen.")

        print("\n🚀 Starte Live-Monitor. Schließe das Fenster zum Beenden.")
        
        # Variable für automatische Skalierung am Start
        v_scale_str = "1.00V" 
        
        while plt.fignum_exists(fig.number):
            # 2. Header abfragen (für aktuelle Skalierung)
            send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
            header_raw = read_resp(dev)
            
            v_scale = 1.0
            if header_raw:
                json_start = header_raw.find(b'{')
                if json_start != -1:
                    try:
                        meta = json.loads(header_raw[json_start:].decode('ascii', errors='ignore'))
                        v_scale_str = meta['CHANNEL'][0]['SCALE'] # z.B. "2.00V"
                        v_scale = parse_vscale(v_scale_str)
                    except: pass

            # 3. CH1 Wellenform abfragen
            send_cmd(dev, ":DATA:WAVE:SCREEN:CH1?")
            wave_raw = read_resp(dev, size=4096)
            
            if wave_raw:
                samples = decode_waveform(wave_raw)
                if samples is not None and len(samples) > 0:
                    # Umrechnung: 
                    # 100 Digits pro Division (geschätzt aus Capture)
                    # Volt = (Raw / 100) * Scale
                    volt_data = (samples.astype(float) / 100.0) * v_scale 
                    
                    # Update Plot
                    line.set_data(np.arange(len(volt_data)), volt_data)
                    ax.set_xlim(0, len(volt_data))
                    
                    # Dynamische Y-Achse
                    limit = v_scale * 4 # Zeige +/- 4 Divisionen
                    ax.set_ylim(-limit, limit)
                    ax.set_title(f"CH1 Live - Scale: {v_scale_str}")
                    
                    fig.canvas.draw_idle()
                    plt.pause(0.01) # Wichtig für Matplotlib Refresh
            
            time.sleep(0.05) # Höhere Refresh-Rate

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"💥 Monitor gestoppt: {e}")
    finally:
        plt.ioff()
        print("🛑 Monitor beendet.")

if __name__ == "__main__":
    main()
