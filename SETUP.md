# Setup & Installation Guide

## Hardware Requirements
*   **Raspberry Pi 4 or 5** (4GB RAM minimum recommended).
*   **Storage:** 64GB+ External SSD (Preferred) or High-Endurance MicroSD.
*   **Networking:** 
    *   Onboard WiFi (`wlan0`) -> Used for the **Pioneer Hotspot (AP)**.
    *   USB WiFi Adapter (`wlan1`) -> Used for **Internet Access (WAN)**.
    *   Ethernet (`eth0`) -> Alternative WAN.

## Phase 1: Flashing the OS (Windows/Mac/Linux)
We use the **Raspberry Pi Imager** to prepare the drive. This allows us to inject settings without a monitor/keyboard.

1.  Download & Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2.  **Choose OS:** Raspberry Pi OS (other) -> **Raspberry Pi OS Lite (64-bit)**.
3.  **Choose Storage:** Select your SSD/SD Card.
4.  **Click NEXT**, then **EDIT SETTINGS** (The Gear Icon):
    *   **Hostname:** `pioneer-core`
    *   **Username:** `pioneer`
    *   **Password:** (Set a secure password)
    *   **Set up Wireless LAN:** 
        *   *Crucial:* Enter your **Home/Venue WiFi** credentials here. 
        *   This allows the Pi to connect to the internet on first boot to download the installer.
        *   *Note:* By default, this configures `wlan0`. Our script will later move this to `wlan1` or we will manage it via Cockpit.
    *   **Services:** Enable SSH (Use password authentication).
5.  **Write** the image.

## Phase 2: Installation (Headless)
Once the Pi is booted and connected to your home WiFi (or Ethernet):

1.  **Find the IP Address:** Check your router or use an app like *Fing* to find `pioneer-core`.
2.  **SSH into the Pi:**
    ```bash
    ssh pioneer@<IP_ADDRESS>
    ```
3.  **Run the One-Line Installer:**
    *(Copy and paste this entire block)*
    ```bash
    sudo apt-get update && sudo apt-get install -y git
    git clone https://github.com/bchabot/pioneer-os.git
    cd pioneer-os
    sudo chmod +x scripts/setup.sh
    sudo ./scripts/setup.sh
    ```

## Phase 3: The "Appliance" Experience
Once the script finishes and the Pi reboots:

1.  **Connect to the Pioneer Bubble:**
    *   Search for WiFi Network: `PIONEER_SETUP`
    *   Password: `pioneer123`
2.  **Access the Admin UI:**
    *   Open Browser: `https://10.42.0.1:9090` (Cockpit) or the IP assigned.
    *   Log in with user `pioneer`.
3.  **Configure Apps:**
    *   Go to Terminal in Cockpit or use Portainer (Port 9000) to manage containers.

---

## Advanced: True "Auto-Run" (Zero Console)
*Requires mounting the Linux partition on your PC.*

1.  Flash the OS as above.
2.  Copy `scripts/setup.sh` to the `/boot` partition.
3.  Edit `/boot/cmdline.txt` (Advanced users only) or create a systemd one-shot service to invoke the script on boot.
*(Note: The SSH method is recommended for stability.)*
