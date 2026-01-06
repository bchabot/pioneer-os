# Pioneer OS

Pioneer OS is a lightweight, appliance-like operating system built on top of Raspberry Pi OS Lite. It provides a robust platform for edge computing, featuring a web-based management interface (Cockpit), container orchestration (Docker), and automated configuration management (SaltStack).

## Quick Start

To convert a fresh Raspberry Pi OS Lite installation into a Pioneer OS node, run the following command:

```bash
wget -qO- https://raw.githubusercontent.com/bchabot/pioneer-os/master/scripts/setup.sh | sudo bash
```

### Debug Mode

For troubleshooting or development, you can run the setup script in debug mode. This enables verbose output and captures a system snapshot to `/var/log/pioneer-setup.log`.

```bash
wget -qO- https://raw.githubusercontent.com/bchabot/pioneer-os/master/scripts/setup.sh | sudo bash -s -- --debug
```

## Features

- **Web Admin Interface:** Managed via Cockpit on port 9090.
- **Hotspot:** Automatically creates a management hotspot if a wireless interface is detected.
- **Container Ready:** Docker pre-installed and configured.
- **Configuration Management:** Built on SaltStack for reliable state management.

## Default Credentials

- **Cockpit:** Uses your system user credentials.
- **Hotspot SSID:** `PIONEER_SETUP` (configurable during setup)
- **Hotspot Password:** `pioneer123` (configurable during setup)