# pioneer-os/salt/states/modules/captive_portal.sls

# 1. Install Nodogsplash (Lightweight Captive Portal)
install_nodogsplash:
  pkg.installed:
    - name: nodogsplash

# 2. Configure Nodogsplash
/etc/nodogsplash/nodogsplash.conf:
  file.managed:
    - source: salt://configs/nodogsplash.conf.j2
    - template: jinja
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - require:
      - pkg: install_nodogsplash

# 3. Ensure IP Forwarding is ON (Crucial for routing traffic)
enable_ip_forwarding:
  sysctl.present:
    - name: net.ipv4.ip_forward
    - value: 1

# 4. Service Management
nodogsplash_service:
  service.running:
    - name: nodogsplash
    - enable: True
    - watch:
      - file: /etc/nodogsplash/nodogsplash.conf
