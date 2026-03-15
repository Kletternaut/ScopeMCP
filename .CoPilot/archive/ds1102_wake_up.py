import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import time

def wake_up_test():
    VID, PID = 0x5345, 0x1234
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden! Bitte USB-Verbindung prüfen.")
        return

    print("✅ Gerät gefunden. Starte Wake-Up Sequenz...")
    try:
        dev.set_configuration()
    except Exception as e:
        print(f"❌ Fehler bei set_configuration: {e}")
        return

    variants = [
        (":MODel?", b":MODel?\n"),      # Nur LF
        (":MODel?", b":MODel?\r\n"),    # CRLF (Standard)
        (":MODel?", b":MODel?\r"),      # Nur CR
        ("MODel?", b"MODel?\n"),        # Ohne Doppelpunkt
        ("*IDN?", b"*IDN?\n"),          # Standard SCPI
    ]

    for label, cmd_bytes in variants:
        print(f"\n🚀 Teste Variante {label} (Hex: {cmd_bytes.hex()})...")
        try:
            # Puffer leeren
            try: dev.read(0x81, 64, timeout=50)
            except: pass
            
            dev.write(0x01, cmd_bytes)
            time.sleep(0.3)
            
            res = dev.read(0x81, 128, timeout=1000)
            print(f"✨ ANTWORT ERHALTEN: {res.tobytes().decode('ascii', errors='ignore').strip()}")
            print(f"📦 ROHDATEN (HEX): {res.tobytes().hex()}")
            print(">>> DIESE VARIANTE FUNKTIONIERT! <<<")
            return
        except usb.core.USBError as e:
            print(f"⏳ Keine Antwort (Timeout: {e})")

    print("\n❌ Keine der Varianten hat funktioniert. Das Gerät schweigt weiterhin.")

if __name__ == "__main__":
    wake_up_test()
