import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package

VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def build_owon_packet(payload):
    """Baut ein klassisches Owon-Paket: 4 Bytes Länge (LE) + Payload"""
    if isinstance(payload, str):
        payload = payload.encode('ascii')
    length_bytes = len(payload).to_bytes(4, byteorder='little')
    return length_bytes + payload

def try_read(dev, timeout=500):
    try:
        data = dev.read(ENDPOINT_IN, 1024, timeout=timeout)
        return data
    except usb.core.USBError as e:
        if e.errno == 10060 or "timeout" in str(e).lower():
            return None
        raise e

def test_set_command(dev, cmd_name, cmd_payload):
    print(f"\n--- Teste SET-Befehl: {cmd_name} ({cmd_payload.hex() if isinstance(cmd_payload, bytes) else cmd_payload}) ---")
    
    # Packet bauen (Owon Format)
    packet = build_owon_packet(cmd_payload)
    
    print(f"Sende Paket: {packet.hex()}")
    dev.write(ENDPOINT_OUT, packet)
    
    # Sofort versuchen zu lesen
    print("Suche nach sofortiger Bestätigung (ACK/OK)...")
    resp = try_read(dev, timeout=200)
    if resp:
        print(f"✅ Direkte Antwort erhalten: {resp.tobytes()} (Hex: {resp.tobytes().hex()})")
    else:
        print("❌ Keine direkte Antwort auf SET-Befehl.")

    # Status abfragen zur Verifikation
    # Hier reparieren wir die Query-Generierung
    if "?" not in cmd_name:
        base_cmd = cmd_name.split(" ")[0] # Sehr grob, besser das Original nehmen
        actual_base = ""
        if ":CH1:COUPling" in cmd_payload: actual_base = ":CH1:COUPling"
        elif "CH1:COUPling" in cmd_payload: actual_base = "CH1:COUPling"
        elif ":TRIGger:LEVel" in cmd_payload: actual_base = ":TRIGger:LEVel"
        elif ":TRIG:LEV" in cmd_payload: actual_base = ":TRIG:LEV"
        
        if actual_base:
            query = actual_base + "?"
            print(f"Sende Query zur Verifikation: {query}")
            dev.write(ENDPOINT_OUT, build_owon_packet(query))
            
            resp_query = try_read(dev, timeout=500)
            if resp_query:
                try:
                    text = resp_query.tobytes().decode('ascii', errors='ignore').strip()
                    print(f"✅ Query Antwort erhalten: {text} (Hex: {resp_query.tobytes().hex()})")
                except:
                    print(f"✅ Query Antwort erhalten (Hex): {resp_query.tobytes().hex()}")
            else:
                print("❌ Keine Antwort auf Verifikations-Query.")

def main():
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    print("✅ Gerät gefunden!")
    
    try:
        # Falls das Gerät beschäftigt ist, versuchen wir es zu claimen
        # if dev.is_kernel_driver_active(0):
        #    dev.detach_kernel_driver(0)
        
        dev.set_configuration()
        
        # Test 1: Coupling
        test_set_command(dev, "CH1 Coupling DC", ":CH1:COUPling DC")
        
        # Test 2: Coupling AC (um eine Änderung zu erzwingen)
        test_set_command(dev, "CH1 Coupling AC", ":CH1:COUPling AC")

        # Test 3: Trigger Level (Zahlenwert)
        test_set_command(dev, "Trigger Level 0.5V", ":TRIG:LEV 0.5")

        # Test 4: Ein Befehl aus dem Protokoll-Dokument (falls bekannt)
        test_set_command(dev, "CH1 Coupling AC (NO COLON)", "CH1:COUPling AC")

    except Exception as e:
        print(f"💥 Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
