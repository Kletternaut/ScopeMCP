# ScopeMCP (Owon/Abestop DS1102)

**ScopeMCP** is a high-performance Python-based bridge that integrates the **Owon/Abestop DS1102** oscilloscope into the **Model Context Protocol (MCP)** ecosystem. It transforms a standard USB oscilloscope into an intelligent, AI-controllable diagnostic tool.

Unlike traditional PC software, **ScopeMCP** allows AI agents (such as Claude Desktop or VS Code Copilot) to directly interact with hardware. It enables automated signal acquisition, real-time parameter tracking, and deep waveform analysis—making it an essential tool for **Automated Hardware Reverse Engineering** and **Embedded Systems Debugging**.

## Features

- **AI-Native Control**: AI agents can execute `Autoset`, toggle `RUN/STOP` states, and adjust vertical/horizontal scales through natural language.
- **Precision Data Capture**: Direct extraction of 16-bit binary waveform data for high-fidelity signal reconstruction.
- **Live Metadata Access**: Real-time JSON-based telemetry providing instant visibility into all scope settings via `:DATA:WAVE:SCREEN:HEAD?`.
- **Extensible Toolset**: Built-in support for multiple channels and custom measurement tools.
- **Hardware Reverse Engineering**: Perfect for automated signal analysis and protocol decoding (UART, I2C, SPI) when combined with an LLM.

## Prerequisites

- **Python 3.10+**
- **USB Permissions (Linux/Raspberry Pi)**: On Linux, you must grant permissions to the USB device. Create a udev rule:
  ```bash
  echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="5345", ATTR{idProduct}=="1234", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ds1102.rules
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```
- **LibUSB Drivers (Windows)**: On Windows, use [Zadig](https://zadig.akeo.ie/) to install the `libusb-win32` or `WinUSB` driver.
- **Original Software**: Ensure any original DSO software is closed.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd ds1102-scope-mcp
   ```

2. **Set up a Virtual Environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```bash
   pip install mcp libusb-package pyusb numpy pydantic
   ```

## Usage

### Running the Live Monitor
To see a real-time plot of the signal:
```bash
python ds1102_grabber.py
```
- **Key A**: Autoset
- **Key S**: Stop
- **Key R**: Run

### Running as an MCP Server
To use the device with AI agents, start the server:
```bash
python ds1102_mcp.py
```

## Configuration for Claude Desktop

Add the following to your `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ds1102-scope": {
      "command": "C:\\Path\\To\\Your\\Oszi\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Path\\To\\Your\\Oszi\\ds1102_mcp.py"
      ]
    }
  }
}
```

## Protocol Details

- **Interface**: USB Bulk (EP 0x01 OUT, 0x81 IN)
- **Terminator**: `\n` (Line Feed)
- **Data Format**: 16-bit **Little-Endian** Signed Integers.
- **Header**: JSON-based metadata for scope parameters.
- **Stability**: Required 1.5s delay after `:SCALe` commands for mechanical relay switching.

## License
MIT
