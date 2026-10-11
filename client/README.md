# Client Setup (Online Mode)

This client requires a deployed server backend. For standalone operation, use `offline_bypass.py` in the root directory instead.

## Prerequisites

### Linux
```bash
sudo apt install libimobiledevice-utils ifuse usbmuxd
pip install pymobiledevice3
sudo systemctl start usbmuxd
```

### macOS
```bash
brew install libimobiledevice ifuse
pip install pymobiledevice3
```

## Configuration

1. Open `activator.py` in a text editor
2. Locate line 32: `self.api_url = "https://your-domain.com/index.php"`
3. Change `your-domain.com` to your deployed server URL

## Usage

```bash
sudo python3 activator.py
```

The tool will:
1. Detect connected iOS device
2. Reboot device and collect system logs
3. Extract GUID from logs
4. Request payload from server
5. Deploy payload to device
6. Reboot device for activation
