#!/bin/bash
# Pioneer OS Bootstrap Script
# Usage: sudo curl -sSL https://raw.githubusercontent.com/bchabot/pioneer-os/master/scripts/setup.sh | bash

set -e
LOG_FILE="/var/log/pioneer-setup.log"
REPO_URL="https://github.com/bchabot/pioneer-os.git"
INSTALL_DIR="/opt/pioneer-os"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Ensure root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo bash)"
  exit 1
fi

log ">>> [Pioneer OS] Starting Bootstrap..."

# --- Interactive Configuration ---
echo ""
echo "Welcome to Pioneer OS Setup."
echo "Press Enter to accept defaults."
echo ""

read -p "Hostname [pioneer-core]: " HOSTNAME_INPUT
HOSTNAME=${HOSTNAME_INPUT:-pioneer-core}

read -p "Hotspot SSID [PIONEER_SETUP]: " SSID_INPUT
HOTSPOT_SSID=${SSID_INPUT:-PIONEER_SETUP}

read -p "Hotspot Password [pioneer123]: " PASS_INPUT
HOTSPOT_PASS=${PASS_INPUT:-pioneer123}

echo ""
log "Configuration:"
log "  Hostname: $HOSTNAME"
log "  SSID:     $HOTSPOT_SSID"
log "---------------------------------"

# 1. System Prep & Repo Clone
log ">>> [1/6] Preparing System..."
apt-get update
apt-get install -y curl wget git network-manager vim htop dnsmasq

# Clone/Update Repo
if [ -d "$INSTALL_DIR" ]; then
    log "Updating existing repository at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull
else
    log "Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

hostnamectl set-hostname $HOSTNAME

# 2. Container Engine (Docker)
log ">>> [2/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $USER
    log "Docker installed."
else
    log "Docker already present."
fi

# 3. Cockpit Web Admin
log ">>> [3/6] Installing Cockpit..."
apt-get install -y cockpit cockpit-networkmanager cockpit-packagekit
systemctl enable --now cockpit.socket

# 4. SaltStack (Masterless)
log ">>> [4/6] Installing SaltStack Minion..."
if ! command -v salt-call &> /dev/null; then
    curl -fsSL https://bootstrap.saltproject.io -o install_salt.sh
    sh install_salt.sh -P -M -x python3
    rm install_salt.sh
fi

# Configure Salt to use the Repo directly
log "Configuring Salt..."
mkdir -p /etc/salt/minion.d
cat <<EOF > /etc/salt/minion.d/local.conf
file_client: local
file_roots:
  base:
    - $INSTALL_DIR/salt/states
pillar_roots:
  base:
    - $INSTALL_DIR/salt/pillar
EOF

# Detect Wireless Interface
get_wireless_interface() {
    local iface=$(nmcli device | grep wifi | head -n 1 | awk '{print $1}')
    if [ -z "$iface" ]; then
        iface=$(ls /sys/class/net | grep -E '^wl' | head -n 1)
    fi
    echo "$iface"
}

AP_IFACE=$(get_wireless_interface)

if [ -n "$AP_IFACE" ]; then
    log "Detected Wireless Interface: $AP_IFACE"
    # Set Grain
    echo "pioneer_ap_iface: $AP_IFACE" > /etc/salt/grains
else
    log "ERROR: No wireless interface found! Hotspot might fail."
fi

# 5. Networking
log ">>> [5/6] Configuring Network..."

# NetworkManager Management
cat <<EOF > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
[keyfile]
unmanaged-devices=none
EOF
systemctl restart NetworkManager
sleep 5

# Create Hotspot
if [ -n "$AP_IFACE" ]; then
    if ! nmcli connection show "$HOTSPOT_SSID" &> /dev/null; then
        log "Creating Hotspot '$HOTSPOT_SSID' on $AP_IFACE..."
        nmcli con add type wifi ifname $AP_IFACE con-name "$HOTSPOT_SSID" autoconnect yes ssid "$HOTSPOT_SSID"
        nmcli con modify "$HOTSPOT_SSID" 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
        nmcli con modify "$HOTSPOT_SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$HOTSPOT_PASS"
    else
        log "Hotspot already exists."
    fi
fi

# 6. Apply Salt State
log ">>> [6/6] Applying Configuration..."
salt-call --local state.apply

log ">>> Bootstrap Complete!"
log "    Access Cockpit at: https://$(hostname -I | awk '{print $1}'):9090"
log "    Hotspot: $HOTSPOT_SSID / $HOTSPOT_PASS"
log "    Please reboot."
