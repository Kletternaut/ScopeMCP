import pyshark
import struct
import binascii

def analyze_pcap(file_path):
    print(f"\n--- Analyzing {file_path} ---")
    try:
        # We use a broad filter and look at the frame data directly if capdata isn't parsed
        cap = pyshark.FileCapture(file_path, display_filter='usb')
        
        last_sent_cmd = "None"
        found_spb = False
        
        for packet in cap:
            try:
                # Access the underlying 'usb' layer
                usb = packet.usb
                
                # Depending on the capture/pyshark version, the data might be in 
                # 'capdata', 'data', or we might need to look for it.
                data_hex = None
                if hasattr(usb, 'capdata'):
                    data_hex = usb.capdata
                elif hasattr(packet, 'data') and hasattr(packet.data, 'usb_capdata'): # Some versions
                    data_hex = packet.data.usb_capdata
                elif hasattr(packet, 'usb_capdata'):
                    data_hex = packet.usb_capdata
                
                if not data_hex:
                    # Fallback: check if there is any 'data' layer at all
                    if hasattr(packet, 'data'):
                        data_hex = packet.data.data
                
                if not data_hex:
                    continue
                    
                data = binascii.unhexlify(data_hex.replace(':', ''))
                
                # 1. Track commands (OUT packets or specific strings)
                # Direction is often in usb.endpoint_number_direction (0=OUT, 1=IN)
                is_out = getattr(usb, 'endpoint_number_direction', None) == '0'
                
                if len(data) < 100:
                    try:
                        decoded = data.decode('ascii', errors='ignore').strip()
                        # Clean up non-printable characters
                        decoded = "".join(c for c in decoded if c.isprintable())
                        if decoded and (':' in decoded or 'START' in decoded or 'IDN' in decoded or decoded.isupper()):
                             last_sent_cmd = decoded
                             # For logging/debugging purposes
                             # print(f"Frame {packet.number}: CMD candidate: {decoded}")
                    except:
                        pass

                # 2. Look for 'SPB' (Hex: 53 50 42)
                if b'SPB' in data:
                    found_spb = True
                    idx = data.find(b'SPB')
                    print(f"\n[FRAME {packet.number}] Found 'SPB' marker!")
                    print(f"    - Preceding command: '{last_sent_cmd}'")
                    print(f"    - Offset in packet:  {idx}")
                    print(f"    - Packet size:       {len(data)} bytes")
                    
                    # 3. Extract frequency at offset 1076 (relative to start of packet metadata?)
                    # If the header follows SPB directly, maybe the user means offset 1076 in the protocol block.
                    # owondump.c says offset 1076. Let's assume absolute offset in response data.
                    # We'll check both relative to 'SPB' and absolute in packet.
                    
                    # Absolute in packet (often the case if packet matches protocol block start)
                    target_offset = 1076
                    if len(data) >= target_offset + 4:
                        freq_bytes = data[target_offset:target_offset+4]
                        try:
                            freq = struct.unpack('<f', freq_bytes)[0]
                            print(f"    - Frequency at ABSOLUTE offset 1076: {freq:.2f} Hz")
                        except:
                            print(f"    - Frequency bytes at 1076: {freq_bytes.hex(' ')}")
                    
                    # Relative to SPB
                    rel_offset = idx + 1076
                    if len(data) >= rel_offset + 4:
                        freq_bytes_rel = data[rel_offset:rel_offset+4]
                        try:
                            freq_rel = struct.unpack('<f', freq_bytes_rel)[0]
                            print(f"    - Frequency at RELATIVE (SPB+{target_offset}): {freq_rel:.2f} Hz")
                        except:
                            print(f"    - Frequency bytes (relative): {freq_bytes_rel.hex(' ')}")

                    # Hex dump for context
                    print(f"    - Start hex: {data[:20].hex(' ')}")
                    print(f"    - End hex:   {data[-20:].hex(' ')}")
                
            except Exception as e:
                pass
        
        if not found_spb:
            print("    No 'SPB' marker found in this file.")
        
        cap.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_pcap(r'c:\Users\Tom\Oszi\analysis\dswave_complete_init.pcapng')
    analyze_pcap(r'c:\Users\Tom\Oszi\analysis\test2.pcapng')
