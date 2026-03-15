import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import time

def minimal_test():
    VID, PID = 0x5345, 0x1234
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    print("✅ Gerät gefunden. Konfiguriere...")
    dev.set_configuration()
    
    # 1. Purge / Leeren falls Daten hängen
    print("🧹 Leere Puffer (Endpoint 0x81)...")
    try:
        dev.read(0x81, 64, timeout=100)
    except: pass

    # 2. Sende MODel?
    cmd = b":MODel?\r\n"
    print(f"📡 Sende: {cmd}")
    dev.write(0x01, cmd)
    
    # 3. Direkt danach lesen
    time.sleep(0.5)
    print("📥 Lese Antwort...")
    try:
        res = dev.read(0x81, 64, timeout=2000)
        print(f"✅ ANTWORT: {res.tobytes().decode('ascii', errors='ignore')}")
        print(f"📦 HEX: {res.tobytes().hex()}")
    except Exception as e:
        print(f"❌ FEHLER: {e}")

if __name__ == "__main__":
    minimal_test()
