import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import time
import sys

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def get_device():
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    if dev:
        try:
            dev.set_configuration()
            usb.util.claim_interface(dev, 0)
        except Exception as e:
            print(f"Warnung bei Initialisierung: {e}")
    return dev

def clear_buffer(dev):
    """Liest alles aus dem Puffer, was noch da ist."""
    count = 0
    try:
        while True:
            dev.read(EP_IN, 1024, timeout=10)
            count += 1
    except:
        pass
    return count

def send_cmd(dev, cmd):
    """
    Sende Befehl im Owon-Binär-Format (4 Bytes Länge + Befehl).
    Wir testen hier verschiedene Abschlusszeichen.
    """
    print(f"\n--- Sende: {cmd} ---")
    # Das Protokoll-Doc sagt \r\n, ds1102_mcp.py nutzt gar nichts außer dem Laengen-Header.
    # Wir probieren es hier mal MIT \n wie im Doc angedeutet ("must be terminated with \n").
    if not cmd.endswith("\n"):
        cmd += "\n"
        
    cmd_bytes = cmd.encode('ascii')
    length_header = len(cmd_bytes).to_bytes(4, byteorder='little')
    packet = length_header + cmd_bytes
    
    print(f"Header: {length_header.hex()} | Payload Hex: {cmd_bytes.hex()}")
    
    clear_buffer(dev)
    dev.write(EP_OUT, packet)
    time.sleep(0.2)

def read_resp(dev, timeout=2000):
    try:
        data = dev.read(EP_IN, 8192, timeout=timeout)
        if data:
            res_hex = bytes(data).hex()
            res_ascii = bytes(data).decode('ascii', errors='ignore').replace('\n', '\\n').replace('\r', '\\r')
            print(f"Antwort (Hex): {res_hex}")
            print(f"Antwort (ASCII): {res_ascii}")
            return bytes(data)
    except usb.core.USBError as e:
        if e.errno == 10060 or "timeout" in str(e).lower():
            print("Antwort: TIMEOUT")
        else:
            print(f"Antwort-Fehler: {e}")
    return None

def main():
    dev = get_device()
    if not dev:
        print("Fehler: DS1102 nicht gefunden!")
        return

    # 1. Kopplung setzen
    send_cmd(dev, ":CH2:COUPling DC")
    read_resp(dev) # Schauen ob direkt eine Bestätigung kommt
    
    # 2. Kopplung abfragen
    send_cmd(dev, ":CH2:COUPling?")
    read_resp(dev)

    # 3. Offset setzen (Wir testen beide Varianten)
    send_cmd(dev, ":CH1:OFFSet 0.00V")
    read_resp(dev)
    
    # 4. Offset abfragen
    send_cmd(dev, ":CH1:OFFSet?")
    read_resp(dev)

    # 5. Autoset
    send_cmd(dev, ":AUToset on")
    print("Warte 5 Sekunden auf Autoset...")
    time.sleep(5)

    # 6. JSON Header abfragen zur Kontrolle
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    resp = read_resp(dev, timeout=3000)
    if resp and b'{' in resp:
        try:
            import json
            start = resp.find(b'{')
            end = resp.rfind(b'}') + 1
            js = json.loads(resp[start:end].decode('ascii'))
            print("\nAktuelle Einstellungen (JSON):")
            print(f"CH1 Offset: {js.get('CHANNEL', [{}])[0].get('OFFSET')}")
            print(f"CH2 Coupling: {js.get('CHANNEL', [{}, {}])[1].get('COUPLING')}")
        except:
            print("Konnte JSON nicht parsen.")

if __name__ == "__main__":
    main()
