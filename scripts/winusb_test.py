import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package

# Oszilloskop Konfiguration
VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def main():
    print("--- 🛠️ DS1102 WinUSB Connection Test ---")
    
    # Nutze libusb_package als Backend für Windows
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    
    # Suche Gerät
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden. Prüfe Kabel und Zadig (WinUSB).")
        return

    print("✅ Gerät gefunden!")
    
    try:
        # Falls ein Treiber das Interface belegt (sollte bei WinUSB nicht sein)
        # dev.is_kernel_driver_active(0) ist auf Windows/WinUSB nicht unterstützt.
        # if dev.is_kernel_driver_active(0):
        #     print("Löse Kernel-Treiber...")
        #     dev.detach_kernel_driver(0)
            
        # Konfiguration setzen
        dev.set_configuration()
        
        # Sende *IDN?
        msg = "*IDN?\n"
        print(f"Sende: {msg.strip()}")
        dev.write(ENDPOINT_OUT, msg)
        
        # Lese Antwort
        time.sleep(0.5)
        try:
            response = dev.read(ENDPOINT_IN, 100, timeout=1000)
            decoded = "".join([chr(x) for x in response])
            print(f"📩 Antwort vom Oszilloskop: {decoded.strip()}")
        except Exception as read_err:
            print(f"⚠️ Lesefehler bei *IDN?: {read_err}")
        
        # Teste nun den :AUTOSet Befehl
        commands = [":AUTOSet\n", ":RUN\n", ":STOP\n"]
        for cmd in commands:
            print(f"Sende: {cmd.strip()}...")
            dev.write(ENDPOINT_OUT, cmd)
            time.sleep(2)
            
    except Exception as e:
        print(f"❌ Fehler: {e}")
    finally:
        # Ressourcen freigeben
        usb.util.dispose_resources(dev)
        print("--- Analyse-Zustand: Warte auf Reaktionen am Gerät ---")

if __name__ == "__main__":
    main()
