# pioneer-os/salt/states/core/cockpit.sls

cockpit_packages:
  pkg.installed:
    - pkgs:
      - cockpit
      - cockpit-networkmanager
      - cockpit-packagekit
      # Try to install cockpit-docker if available, otherwise ignore failure? 
      # No, better to stick to Portainer integration.

cockpit_service:
  service.running:
    - name: cockpit.socket
    - enable: True
    - require:
      - pkg: cockpit_packages

# Integration: Add "Advanced Apps" link to Cockpit Sidebar
/usr/share/cockpit/portainer-link:
  file.directory:
    - makedirs: True

/usr/share/cockpit/portainer-link/redirect.html:
  file.managed:
    - contents: |
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redirecting to Portainer...</title>
            <script>
                // Redirect to the same hostname but port 9000
                window.location.href = window.location.protocol + "//" + window.location.hostname + ":9000";
            </script>
        </head>
        <body>
            <p>Redirecting to Portainer App Manager...</p>
        </body>
        </html>

/usr/share/cockpit/portainer-link/manifest.json:
  file.managed:
    - contents: |
        {
            "version": "1.0",
            "tools": {
                "portainer-link": {
                    "label": "App Manager (Portainer)",
                    "path": "redirect.html",
                    "priority": 20
                }
            }
        }