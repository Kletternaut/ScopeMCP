import usb.core
import usb.util
import time

VID = 0x5345
PID = 0x1234

def force_waveform_dump():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("Oszi nicht gefunden.")
        return

    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except: pass

    dev.set_configuration()
    ep_out = 0x01
    ep_in = 0x81

    def send_cmd(cmd):
        full_cmd = f"{cmd}\r\n"
        print(f"Sende: {cmd}")
        dev.write(ep_out, full_cmd)
        time.sleep(0.2)

    try:
        # 1. Sicherstellen, dass das Gerät antwortet (Handshake)
        send_cmd(":MODel?")
        resp = dev.read(ep_in, 1024, timeout=1000)
        print(f"Modell: {bytes(resp).decode('ascii', errors='ignore').strip()}")

        # 2. Messwerte direkt abfragen
        print("\n--- Direkte Messung (SCPI) ---")
        meas_cmds = [
            ":MEASure:SOURce CH1",
            ":MEASure:SHOW ON",
            ":MEASure:ITEM? FREQuency,CH1",
            ":MEASure:ITEM? VPP,CH1",
            ":MEASure:CH1:PKPK?",
            ":MEASure:CH1:AVERage?",
            ":MEASure:FREQuency?",
            ":MEASure:VPP?",
            ":MEASure:PERIOD?",
            ":MEASure:SOURce?"
        ]

        for cmd in meas_cmds:
            try:
                send_cmd(cmd)
                response = dev.read(ep_in, 1024, timeout=2000)
                if len(response) > 0:
                    text = bytes(response).decode('ascii', errors='ignore').strip()
                    print(f"ERGEBNIS {cmd}: {text}")
                else:
                    print(f"KEINE DATEN für {cmd}")
            except Exception as e:
                print(f"FEHLER bei {cmd}: {e}")

        # 3. Waveform Request CH1 (Noch ein Versuch mit :DATA:WAVe:SCReen:CH1?)
        print("\n--- Finaler Waveform Request ---")
        # Wir versuchen verschiedene Varianten, falls :DATA:WAVE:SCREen:CH1? weiterhin nur Nullen liefert
        variants = [
            ":DATA:WAVE:SCREen:CH1?",
            ":WAVeform:DATA? CH1",
            ":DATA:DUMP?"
        ]

        for cmd in variants:
            send_cmd(cmd)
            print(f"Lese Daten für {cmd}...")
            total_data = bytearray()
            start_t = time.time()
            while time.time() - start_t < 3:
                try:
                    chunk = dev.read(ep_in, 1024*64, timeout=500)
                    if len(chunk) > 0:
                        total_data.extend(chunk)
                        print(f"Empfangen: {len(chunk)} bytes (Total: {len(total_data)})")
                except usb.core.USBError:
                    if len(total_data) > 0: break
                    continue
            
            if len(total_data) > 4:
                print(f"ERFOLG mit {cmd}: {len(total_data)} Bytes erhalten.")
                print(f"Anfang (hex): {total_data.hex()[:100]}")
                if b"{" in total_data:
                    print("JSON Metadaten gefunden!")
                break
            else:
                print(f"Fehlgeschlagen mit {cmd}: Nur {len(total_data)} Bytes.")

    except usb.core.USBError as e:
        print(f"USB Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    force_waveform_dump()
