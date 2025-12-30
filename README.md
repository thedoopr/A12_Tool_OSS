# iOS Activation Tool Suite

A cross-platform (macOS/Linux) solution for iOS device activation management. This repository contains both the client-side automation logic and an optional server-side infrastructure.

## Features

- **Cross-Platform**: Works on both macOS and Linux
- **Two Modes**: Online (with server) or Offline (standalone)
- **Automatic Platform Detection**: Uses optimal methods per OS
- **Clean CLI**: Presentation-ready output with progress indicators

## Architecture

```
.
├── client/
│   └── activator.py       # Online client (requires server)
├── offline_bypass.py      # Standalone offline client (no server needed)
└── server/                # Optional PHP backend
    ├── assets/            # Device configuration files
    ├── public/            # Web root
    └── templates/         # SQL templates
```

## Quick Start

### Option 1: Offline Mode (Recommended for demos)

No server required - everything runs locally:

```bash
# Install dependencies
pip install pymobiledevice3

# On Linux, also install libimobiledevice
sudo apt install libimobiledevice-utils ifuse  # Debian/Ubuntu
# or
sudo dnf install libimobiledevice ifuse        # Fedora

# Run
sudo python3 offline_bypass.py
```

### Option 2: Online Mode (With Server)

```bash
# 1. Deploy server/ to your web host
# 2. Update API URL in client/activator.py
# 3. Run
sudo python3 client/activator.py
```

## Prerequisites

### All Platforms
- Python 3.6+
- `pymobiledevice3` (`pip install pymobiledevice3`)

### Linux
```bash
sudo apt install libimobiledevice-utils ifuse usbmuxd
sudo systemctl start usbmuxd
```

### macOS
```bash
brew install libimobiledevice ifuse
```

## Platform Support

| Feature | macOS | Linux |
|---------|-------|-------|
| Device Detection | Yes | Yes |
| Syslog Collection | Yes (archive) | Yes (live) |
| AFC Transfer (ifuse) | Yes | Yes |
| AFC Transfer (pymobiledevice3) | Yes | Yes |

## How It Works

1. **Device Detection**: Connects via USB using libimobiledevice
2. **Log Analysis**: Extracts device GUID from system logs
3. **Payload Generation**: Creates device-specific activation databases
4. **Deployment**: Pushes payload to device filesystem via AFC
5. **Activation**: Device processes payload on reboot

## Supported Devices

See `server/assets/Maker/` for the list of supported ProductTypes (iPad11-x through iPad14-x).

## Disclaimer

This tool is provided for educational and research purposes only. The authors are not responsible for any misuse of this software. Ensure you have proper authorization before use.

## License

MIT License - See [LICENSE](LICENSE)
