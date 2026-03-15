import usb.core
import usb.util
import time
import struct

# Owon / Abestop DS1102 VID/PID
VID = 0x5345
PID = 0x1234

def test_start_dump():
    # Device suchen
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    
    if dev is None:
        print("Oszi nicht gefunden. Check USB connection.")
        return

    # Linux-Spezifisch: Kernel Driver deattachen falls nötig
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
            print("Kernel driver detached.")
    except (NotImplementedError, usb.core.USBError):
        pass

    try:
        dev.set_configuration()
    except usb.core.USBError as e:
        print(f"Configuration error: {e}")

    # Endpunkte (Bulk Out 0x01, Bulk In 0x81)
    ep_out = 0x01
    ep_in = 0x81

    try:
        # Handshake / Initialisierung (SCPI Modus erzwingen)
        handshake = ":MODel?\r\n"
        print(f"Handshake senden: {handshake.strip()}")
        dev.write(ep_out, handshake)
        time.sleep(0.5)
        try:
            resp = dev.read(ep_in, 1024, timeout=1000)
            print(f"Handshake Antwort: {bytes(resp).decode('ascii', errors='ignore').strip()}")
        except:
            print("Keine Antwort auf Handshake (normal bei Timeout).")

        # Nun das :DATA:WAVE:SCReen:CH1? Kommando (SCPI-Weg zum Dump)
        cmd_wave = ":DATA:WAVE:SCREen:CH1?\r\n"
        print(f"Sende Wellenform-Anfrage: {cmd_wave.strip()}")
        # Wir schicken nur das Kommando
        dev.write(ep_out, cmd_wave)
        
        # JETZT: Lese so lange wie möglich
        print("Starte kontinuierliches Lesen...")
        total_data = bytearray()
        start_time = time.time()
        while time.time() - start_time < 5: # 5 Sekunden sammeln
            try:
                # Schneller Read mit kurzem Timeout
                chunk = dev.read(ep_in, 1024*64, timeout=100)
                if len(chunk) > 0:
                    total_data.extend(chunk)
                    print(f"Empfangen: {len(chunk)} bytes (Total: {len(total_data)})")
            except usb.core.USBError:
                if len(total_data) > 4: break # Wenn wir was haben und es stockt: raus
                continue
        
        if len(total_data) > 0:
            print(f"FINALE DATEN: {len(total_data)} bytes")
            print(f"Header hex: {total_data.hex()[:128]}")
            # Suche nach Marker
            if b"SPB" in total_data: print("!!! SPB GEFUNDEN !!!")
            if b"{" in total_data: print("!!! JSON GEFUNDEN !!!")
        else:
            print("Absolut keine Daten nach 5 Sekunden.")
            print(f"Empfangen: {len(response)} bytes")
            # Schauen wir uns die ersten 16 bytes an:
            hex_data = " ".join([f"{b:02x}" for b in response[:16]])
            print(f"Datenanfang (hex): {hex_data}")
            
            # Versuche als Text zu dekodieren (JSON Metadaten?)
            try:
                full_text = response.decode('ascii', errors='ignore')
                if '{' in full_text:
                    json_start = full_text.find('{')
                    print(f"JSON Metadaten bei Offset {json_start} gefunden:")
                    print(full_text[json_start:json_start+500] + "...")
            except:
                pass
        else:
            print(f"Zu wenig Daten empfangen ({len(response)} bytes): {response.hex()}")

    except usb.core.USBError as e:
        print(f"USB Fehler: {e}")
        print("Tipp: Eventuell muss zuerst :MODel?\\r\\n geschickt werden (Handshake).")
    finally:
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    test_start_dump()
