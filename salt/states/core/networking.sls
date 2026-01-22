# pioneer-os/salt/states/core/networking.sls

# Ensure NetworkManager is the boss
network_manager_pkg:
  pkg.installed:
    - name: network-manager

enable_network_manager:
  service.running:
    - name: NetworkManager
    - enable: True

# Install DNSMasq
dnsmasq_pkg:
  pkg.installed:
    - name: dnsmasq

# Disable systemd-resolved to free up port 53 for dnsmasq
disable_systemd_resolved:
  service.dead:
    - name: systemd-resolved
    - enable: False

# Enable DNSMasq system service (Dashboard manages config in /etc/dnsmasq.d/)
enable_system_dnsmasq:
  service.running:
    - name: dnsmasq
    - enable: True
    - require:
      - pkg: dnsmasq
      - service: disable_systemd_resolved

# We will let NetworkManager handle the actual interface config (AP mode)
# via the 'nmcli' commands run in the setup script.
# But we ensure IP Forwarding is persistent.

ip_forwarding_conf:
  file.managed:
    - name: /etc/sysctl.d/99-pioneer-forwarding.conf
    - contents: |
        net.ipv4.ip_forward=1
    - user: root
    - group: root

apply_sysctl:
  cmd.run:
    - name: sysctl -p /etc/sysctl.d/99-pioneer-forwarding.conf
    - onchanges:
      - file: ip_forwarding_conf
