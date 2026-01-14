# pioneer-os/salt/states/core/cockpit.sls

cockpit_packages:
  pkg.installed:
    - pkgs:
      - cockpit
      - cockpit-networkmanager
      - cockpit-packagekit

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
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>App Manager (Portainer)</title>
            <style>
                body {
                    font-family: 'Open Sans', Helvetica, Arial, sans-serif;
                    background-color: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    color: #333;
                }
                .container {
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    max-width: 400px;
                }
                h2 { margin-top: 0; }
                p { color: #666; margin-bottom: 25px; }
                .btn {
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: bold;
                    transition: background-color 0.2s;
                }
                .btn:hover { background-color: #0056b3; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Advanced App Manager</h2>
                <p>
                    Portainer provides advanced management for your Docker containers, images, and networks.
                </p>
                <p><small>Target: <span id="url-display">...</span></small></p>
                <a href="#" id="link" class="btn" target="_blank">Launch Portainer</a>
            </div>
            <script>
                // Use port 9443 for HTTPS (Cockpit default), or 9000 for HTTP
                var port = window.location.protocol === 'https:' ? '9443' : '9000';
                var url = window.location.protocol + "//" + window.location.hostname + ":" + port;
                
                document.getElementById('link').href = url;
                document.getElementById('url-display').innerText = url;
            </script>
        </body>
        </html>

/usr/share/cockpit/portainer-link/manifest.json:
  file.managed:
    - contents: |
        {
            "version": "1.1",
            "tools": {
                "portainer-link": {
                    "label": "App Manager (Portainer)",
                    "path": "redirect.html",
                    "priority": 20
                }
            }
        }
