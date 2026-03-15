import usb.core
import usb.util
import time
import json
import libusb_package

def test_command(cmd):
    backend = libusb_package.get_libusb1_backend()
    dev = usb.core.find(idVendor=0x5345, idProduct=0x1234, backend=backend)
    
    if dev is None:
        print("Scope not found")
        return
    
    try:
        # Auf Windows ist detach_kernel_driver oft nicht unterstützt/nötig
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except (usb.core.USBError, NotImplementedError, Exception):
            pass 
            
        dev.set_configuration()
        
        # Sende Befehl
        full_cmd = cmd + "\n"
        print(f"Sending: {cmd}")
        dev.write(0x01, full_cmd.encode())
        
        # Wenn es eine Abfrage ist (?), lese die Antwort
        if "?" in cmd:
            time.sleep(0.1)
            response = dev.read(0x81, 1024, timeout=1000)
            text = "".join([chr(x) for x in response])
            print(f"Response: {text}")
            return text
    except Exception as e:
        print(f"Error: {e}")
    finally:
        usb.util.dispose_resources(dev)

commands_to_test = [
    "*IDN?",
    # Trigger - Vereinfachte Syntax (Flat Structure)
    ":TRIG:TYPE?",          # Edge?
    ":TRIG:SOUR?",          # CH1?
    ":TRIG:LEVel?",         # Trigger Level?
    ":TRIG:MODe?",          # Auto/Normal?
    ":TRIG:SLOPe?",         # Rising/Falling?
    ":TRIG:COUPling?",      # AC/DC?
    
    # Messwerte - Verschiedene Variationen
    ":MEASure:VPP?",        # Peak-to-Peak
    ":MEASure:FREQ?",       # Frequenz
    ":MEASure:PKPK?",
    ":VPP?",                # Ganz flach
    ":FREQ?",
    
    # Kanalsteuerung & Kopplung
    ":CH1:COUPling?",       # AC/DC/GND
    ":CH1:DISPlay?",        # On/Off
    ":CH2:DISPlay?",
    ":CH2:COUPling?",
    
    # Dokumentation/Utility
    ":DISPlay:BRIGhtness?",
    ":SYSTem:TIME?",
]

print("--- DS1102 SCPI Command Brute-Force Test ---")
for cmd in commands_to_test:
    test_command(cmd)
    print("-" * 20)
