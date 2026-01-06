#!/bin/bash
# Pioneer OS Bootstrap Script (MVP)
# Target: Raspberry Pi 4 (4GB) with External SSD + USB WiFi
#
# Usage: sudo ./setup.sh
#
# This script transforms a fresh Raspberry Pi OS Lite install into a Pioneer OS node.
# It is designed to be idempotent (can be run multiple times).

set -e
LOG_FILE="/var/log/pioneer-setup.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log ">>> [Pioneer OS] Starting Bootstrap..."

# --- Configuration ---
HOSTNAME="pioneer-core"
HOTSPOT_SSID="PIONEER_SETUP"
HOTSPOT_PASS="pioneer123"
AP_IFACE="wlan0"     # Onboard WiFi for Hotspot (Stable)
WAN_IFACE="wlan1"    # USB WiFi for Internet (if available)

# 1. System Prep
log ">>> [1/6] Updating System & Setting Hostname..."
apt-get update && apt-get upgrade -y
hostnamectl set-hostname $HOSTNAME
# Install essential utils
apt-get install -y curl wget git network-manager vim htop dnsmasq

# 2. Container Engine (Docker)
log ">>> [2/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
    rm get-docker.sh
    log "Docker installed."
else
    log "Docker already present."
fi

# 3. Cockpit Web Admin
log ">>> [3/6] Installing Cockpit..."
apt-get install -y cockpit cockpit-networkmanager cockpit-packagekit
# Allow cockpit on port 9090
systemctl enable --now cockpit.socket

# 4. SaltStack (Masterless)
log ">>> [4/6] Installing SaltStack Minion..."
if ! command -v salt-call &> /dev/null; then
    curl -fsSL https://bootstrap.saltproject.io -o install_salt.sh
    sh install_salt.sh -P -M -x python3
    rm install_salt.sh
fi

# Configure Salt for Masterless Mode
log "Configuring Salt for local (file) mode..."
mkdir -p /etc/salt/minion.d
cat <<EOF > /etc/salt/minion.d/local.conf
file_client: local
file_roots:
  base:
    - /srv/salt/states
pillar_roots:
  base:
    - /srv/salt/pillar
EOF

# Ensure Salt Directories Exist
mkdir -p /srv/salt/states
mkdir -p /srv/salt/pillar

# 5. Networking (Dual Interface Strategy)
log ">>> [5/6] Configuring NetworkManager..."

# Ensure NetworkManager is managing everything
cat <<EOF > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
[keyfile]
unmanaged-devices=none
EOF
systemctl restart NetworkManager
sleep 5

# Create Hotspot on Internal WiFi (wlan0)
if ! nmcli connection show "$HOTSPOT_SSID" &> /dev/null; then
    log "Creating Hotspot on $AP_IFACE..."
    nmcli con add type wifi ifname $AP_IFACE con-name "$HOTSPOT_SSID" autoconnect yes ssid "$HOTSPOT_SSID"
    nmcli con modify "$HOTSPOT_SSID" 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
    nmcli con modify "$HOTSPOT_SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$HOTSPOT_PASS"
    log "Hotspot '$HOTSPOT_SSID' created."
else
    log "Hotspot already exists."
fi

# Note: We assume the user configured WAN (wlan1 or eth0) via RPi Imager or manual setup for now
# to download these packages.

# 6. Finalize
log ">>> [6/6] Bootstrap Complete!"
log "    Access Cockpit at: https://<IP>:9090"
log "    Hotspot Active: $HOTSPOT_SSID ($HOTSPOT_PASS)"
log "    Please reboot to apply all changes."

# Optional: Run Salt Highstate immediately if states are present
if [ -f "/srv/salt/top.sls" ]; then
    log "Running Initial Salt State Apply..."
    salt-call --local state.apply
fi