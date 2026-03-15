import pyshark
import binascii

def look_at_responses(file_path):
    print(f"\n--- Checking responses to :DATA:WAVE:SCREEN:CH1? in {file_path} ---")
    cap = pyshark.FileCapture(file_path)
    
    last_cmd = "None"
    
    for packet in cap:
        try:
            # Basic Layer Inspection
            for layer in packet.layers:
                field_names = layer.field_names
                for field in field_names:
                    val = layer.get_field(field)
                    if not val or not isinstance(val, str): continue
                    
                    try:
                        data = binascii.unhexlify(val.replace(':', ''))
                        
                        # Direction check (simplified by command vs response length)
                        if 2 < len(data) < 100:
                            s = data.decode('ascii', errors='ignore').strip()
                            if ':DATA:WAVE:SCREEN:CH1?' in s:
                                print(f"[# {packet.number}] SENT: {s}")
                                last_cmd = s
                            elif ':MODel?' in s: last_cmd = s
                            elif ':DATA:WAVE:SCREEN:HEAD?' in s: last_cmd = s
                        
                        # Large response
                        if len(data) > 200:
                             print(f"[# {packet.number}] RECEIVED Response (Len: {len(data)})")
                             print(f"    - After Cmd: {last_cmd}")
                             print(f"    - Hex Start: {data[:64].hex(' ')}")
                             print(f"    - Hex End:   {data[-32:].hex(' ')}")
                             
                             # Search SPB in this large data
                             if b'SPB' in data:
                                 print(f"    *** FOUND 'SPB' at offset {data.find(b'SPB')}! ***")
                                 
                    except: pass
        except: pass
    cap.close()

if __name__ == "__main__":
    look_at_responses(r'c:\Users\Tom\Oszi\analysis\dswave_complete_init.pcapng')
