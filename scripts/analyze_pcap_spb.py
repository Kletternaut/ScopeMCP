import pyshark
import struct
import binascii

def analyze_pcap(file_path):
    print(f"\n--- Analyzing {file_path} ---")
    try:
        # Use bulk transfers, endpoint depends on direction
        # In pcap, look for both in and out
        cap = pyshark.FileCapture(file_path, display_filter='usb.capdata')
        
        last_sent_cmd = "None"
        packet_count = 0
        
        for packet in cap:
            packet_count += 1
            try:
                # Direct data extraction from capdata field
                data_hex = packet.usb.get_field('capdata')
                if not data_hex:
                    continue
                    
                data = binascii.unhexlify(data_hex.replace(':', ''))
                
                # Try to see if it's a command sent TO the scope
                is_out = packet.usb.get_field('endpoint_number_direction') == '0' # OUT (often)
                # Note: direction labels might vary depending on how it was captured
                
                # Check for 'SPB'
                if b'SPB' in data:
                    idx = data.find(b'SPB')
                    print(f"[{packet_count}] Found 'SPB' at packet {packet.number}, index {idx}")
                    print(f"    Packet length: {len(data)}")
                    print(f"    Preceding command: {last_sent_cmd}")
                    
                    # Extract 4-byte float at offset 1076 (relative to packet start if it's the whole block)
                    # Or relative to 'SPB'? If 'SPB' is at 0, then 1076.
                    offset_1076 = idx + 1076
                    if len(data) >= offset_1076 + 4:
                        freq_bytes = data[offset_1076:offset_1076+4]
                        freq = struct.unpack('<f', freq_bytes)[0]
                        print(f"    Frequency at offset 1076: {freq} Hz")
                    else:
                        print(f"    Warning: Packet too short for offset 1076 ({len(data)} < {offset_1076+4})")

                    # Hex dump of start and end
                    print(f"    Start data (hex): {data[idx:idx+16].hex(' ')}")
                    if len(data) > 32:
                         print(f"    End data (hex):   {data[-16:].hex(' ')}")

                # Check for commands (usually shorter ASCII)
                if 2 < len(data) < 64:
                    try:
                        decoded = data.decode('ascii', errors='ignore').strip()
                        if any(c in decoded for c in [':', '?', 'START', 'STOP']):
                             last_sent_cmd = decoded
                             # logging commands to trace
                             # print(f"[{packet_count}] CMD: {last_sent_cmd}")
                    except:
                        pass
                        
            except Exception as e:
                pass
        
        cap.close()
        print(f"Processed {packet_count} packets.")
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")

if __name__ == "__main__":
    analyze_pcap(r'c:\Users\Tom\Oszi\analysis\dswave_complete_init.pcapng')
    analyze_pcap(r'c:\Users\Tom\Oszi\analysis\test2.pcapng')
