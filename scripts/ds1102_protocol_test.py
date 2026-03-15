import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import time
import json
import numpy as np

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def send_cmd(dev, cmd):
    if not cmd.endswith("\r\n"):
        cmd += "\r\n"
    print(f"📡 Sende: {repr(cmd)}")
    dev.write(EP_OUT, cmd.encode('ascii'))
    time.sleep(0.1)

def read_resp(dev, size=8192, timeout=2000):
    """Liest die gesamte Antwort vom Bulk-In Endpoint mit Fehlerdiagnose."""
    try:
        # Debug: Kurzes Lesen, um Puffer zu leeren
        # dev.read(EP_IN, 64, timeout=100)
        
        full_data = b""
        chunk = dev.read(EP_IN, size, timeout=timeout)
        full_data = chunk.tobytes()
        return full_data
    except usb.core.USBError as e:
        print(f"DEBUG: USB Fehler beim Lesen: {e}")
        return None
    except Exception as e:
        print(f"DEBUG: Anderer Fehler beim Lesen: {e}")
        return None

def test_protocol_steps(dev):
    print("\n--- 🏁 Start Protokoll-Test-Suite ---")
    
    # SCHRITT 1: Handshake
    print("\n[STEP 1] Initialisierung (:MODel?)")
    send_cmd(dev, ":MODel?")
    resp = read_resp(dev)
    if resp:
        print(f"✅ Handshake OK: {resp.decode('ascii', errors='ignore').strip()}")
    else:
        print("❌ Handshake fehlgeschlagen!")
        return

    # SCHRITT 2: Metadaten (JSON)
    print("\n[STEP 2] Metadaten (:DATA:WAVE:SCREEN:HEAD?)")
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = read_resp(dev)
    if header_raw and b'{' in header_raw:
        json_str = header_raw[header_raw.find(b'{'):].decode('ascii', errors='ignore')
        try:
            meta = json.loads(json_str)
            print(f"✅ JSON empfangen. Kanal 1 Skalierung: {meta.get('CHANNEL', [{}])[0].get('SCALE', 'N/A')}")
            print(f"✅ Zeitbasis: {meta.get('TIMEBASE', {}).get('SCALE', 'N/A')}")
        except Exception as e:
            print(f"❌ JSON-Parsing fehlgeschlagen: {e}")
    else:
        print("❌ Keine Metadaten empfangen.")

    # SCHRITT 3: Kanal 1 Wellenform (Binär)
    print("\n[STEP 3] Kanal 1 Daten (:DATA:WAVE:SCREEN:CH1?)")
    send_cmd(dev, ":DATA:WAVE:SCREEN:CH1?")
    wave_raw = read_resp(dev)
    if wave_raw:
        # Header analysieren (erste 4 Bytes)
        h_bytes = wave_raw[:4]
        # In Little Endian die Länge berechnen
        data_len = int.from_bytes(h_bytes, byteorder='little')
        print(f"✅ Wellenform-Header: {h_bytes.hex()} (Länge laut Header: {data_len} Bytes)")
        print(f"✅ Reale Länge empfangen: {len(wave_raw)} Bytes")
        
        # Daten-Werte analysieren (Samples ab Byte 4)
        samples_raw = wave_raw[4:]
        if len(samples_raw) >= 10:
            samples = np.frombuffer(samples_raw, dtype='>i2')
            print(f"✅ Erste 5 Samples (Big-Endian): {samples[:5]}")
            print(f"✅ Anzahl der Samples: {len(samples)}")
    else:
        print("❌ Keine Wellenform-Daten empfangen.")

    # SCHRITT 4: Kanal 2 Wellenform (Binär) - Falls vorhanden
    print("\n[STEP 4] Kanal 2 Daten (:DATA:WAVE:SCREEN:CH2?)")
    send_cmd(dev, ":DATA:WAVE:SCREEN:CH2?")
    wave2_raw = read_resp(dev)
    if wave2_raw and len(wave2_raw) > 10:
        print(f"✅ Kanal 2 aktiv (Länge: {len(wave2_raw)} Bytes)")
    else:
        print("ℹ️ Kanal 2 scheint inaktiv zu sein.")

def main():
    print("--- 🔬 DS1102 Protokoll-Tester (Deep Recovery) ---")
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    try:
        # dev.is_kernel_driver_active(0) ist unter Windows nicht verfügbar.
        # Wir überspringen das und gehen direkt zum set_configuration()
        
        dev.set_configuration()
        
        # Manchmal braucht das Gerät einen Reset oder ein leeres Lesen
        print("📡 Versuche Initialisierung...")
        test_protocol_steps(dev)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"💥 Test abgebrochen durch Fehler: {e}")
    finally:
        print("\n--- 🏁 Test beendet ---")

if __name__ == "__main__":
    main()
