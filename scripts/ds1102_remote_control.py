import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def send_cmd(dev, cmd):
    # WICHTIG: Die Analyse hat gezeigt, dass Befehle mit ':' beginnen und '\r\n' brauchen.
    if not cmd.endswith("\r\n"):
        cmd += "\r\n"
    print(f"📡 Sende Befehl: {repr(cmd)}")
    dev.write(EP_OUT, cmd.encode('ascii'))
    time.sleep(0.5) # Dem Gerät Zeit zum Verarbeiten geben

def main():
    print("--- 🎮 DS1102 Remote Control Test ---")
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    try:
        dev.set_configuration()
        
        # Test-Befehle basierend auf pcapng-Entdeckungen
        # 1. Autoset
        # 2. Stop (Einfrieren der Kurve)
        # 3. Run (Fortsetzen)
        
        print("\n1. Test: AUTOSET")
        send_cmd(dev, ":AUTOSet")
        print("   Warte 3 Sekunden auf Relais-Klicken...")
        time.sleep(3)
        
        print("\n2. Test: STOP (Kurve einfrieren)")
        # In der pcapng Datei sahen wir ':RUNning STOP'
        send_cmd(dev, ":RUNning STOP")
        time.sleep(1)
        
        print("\n3. Test: RUN (Fortsetzen)")
        # Vermutlich ':RUNning RUN' oder ':RUN'
        send_cmd(dev, ":RUNning RUN")
        time.sleep(1)

        print("\n4. Test: Zeitbasis ändern auf 1ms")
        send_cmd(dev, ":HORIzontal:SCALe 1ms")
        
    except Exception as e:
        print(f"💥 Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)
        print("\n--- Fernsteuerungstest beendet ---")

if __name__ == "__main__":
    main()
