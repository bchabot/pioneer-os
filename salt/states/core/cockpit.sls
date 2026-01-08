# pioneer-os/salt/states/core/cockpit.sls

cockpit_service:
  service.running:
    - name: cockpit.socket
    - enable: True
