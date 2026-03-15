# Installation & Setup Guide: DS1102 MCP Projects

This guide outlines the steps to set up your environment for controlling your Owon/Abestop DS1102 oscilloscope via Python and Model Context Protocol (MCP).

## 📊 1. Hardware Connection
1. Connect the oscilloscope via USB.
2. In Windows **Device Manager**, identify the device with VID `0x5345` and PID `1234`.
3. If not recognized, use [Zadig](https://zadig.akeo.ie/) to replace the standard driver with `libusb-win32` or `WinUSB`.

## ⚙️ 2. Python Environment Setup
1. Create a virtual environment:
   ```powershell
   # Windows
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / Raspberry Pi OS
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install the core libraries:
   ```bash
   pip install mcp libusb-package pyusb numpy matplotlib pydantic
   ```

## 🐧 3. Linux / Raspberry Pi Specifics
On Linux, you must grant permissions to the USB device and ensure no kernel driver is blocking access.

1. **Create a udev rule**:
   ```bash
   echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="5345", ATTR{idProduct}=="1234", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ds1102.rules
   ```
2. **Reload rules**:
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
3. **Kernel Driver**: The scripts are configured to automatically detach the kernel driver if necessary.

## 🛠️ 4. Software Components
*   **`ds1102_grabber.py`**: A real-time plotting tool.
*   **`ds1102_mcp.py`**: The MCP server that acts as a bridge for AI assistants.
*   **`ds1102_protocol.md`**: Detailed technical breakdown of the USB protocol.

## 🤖 4. AI Assistant Integration (MCP)
To enable AI control (Claude Desktop or VS Code), add the project to the `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ds1102-scope": {
      "command": "C:/Path/To/Your/Oszi/.venv/Scripts/python.exe",
      "args": [
        "C:/Path/To/Your/Oszi/ds1102_mcp.py"
      ]
    }
  }
}
```

## ⚠️ Important Notes
- **Software Conflict**: Close the original "DSO-Wave" software before running these scripts.
- **Port Locking**: Only one script (Monitor or MCP Server) can access the scope at any given time.
- **Terminator**: Use only `\n` (Line Feed) for commands sent to the device.
