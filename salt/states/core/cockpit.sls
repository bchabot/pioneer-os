# pioneer-os/salt/states/core/cockpit.sls

cockpit_packages:
  pkg.installed:
    - pkgs:
      - cockpit
      - cockpit-networkmanager
      - cockpit-packagekit

# Configure Cockpit to run under a subpath
/etc/cockpit/cockpit.conf:
  file.managed:
    - makedirs: True
    - contents: |
        [WebService]
        UrlRoot = /advanced-admin
        ProtocolHeader = X-Forwarded-Proto
        AllowUnencrypted = true
    - require:
      - pkg: cockpit_packages

cockpit_service:
  service.running:
    - name: cockpit.socket
    - enable: True
    - watch:
      - file: /etc/cockpit/cockpit.conf
    - require:
      - pkg: cockpit_packages

# Integration: Add "Advanced Apps" link to Cockpit Sidebar
/usr/share/cockpit/portainer-link:
  file.directory:
    - makedirs: True

# HTML File
/usr/share/cockpit/portainer-link/launcher.html:
  file.managed:
    - contents: |
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>App Manager</title>
            <link rel="stylesheet" href="launcher.css">
        </head>
        <body>
            <div class="container">
                <h2>Advanced App Manager</h2>
                <p>
                    Manage your Docker containers (WordPress, etc.) using Portainer.
                    This runs on a separate secure port.
                </p>
                
                <button id="btn-launch" class="btn">Launch Portainer</button>
                
                <div class="url-box">Target: <span id="target-url">Detecting...</span></div>
            </div>
            <script src="launcher.js"></script>
        </body>
        </html>

# CSS File
/usr/share/cockpit/portainer-link/launcher.css:
  file.managed:
    - contents: |
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background-color: #f5f5f5;
            display: flex;
            flex-direction: column;
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
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 450px;
        }
        h2 { margin-top: 0; color: #2c3e50; }
        p { color: #666; margin-bottom: 25px; line-height: 1.5; }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            font-size: 16px;
            transition: background-color 0.2s;
            border: none;
            cursor: pointer;
        }
        .btn:hover { background-color: #0056b3; }
        .url-box {
            background: #eee;
            padding: 5px 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            margin-top: 20px;
            word-break: break-all;
        }

# JS File
/usr/share/cockpit/portainer-link/launcher.js:
  file.managed:
    - contents: |
        function getPortainerUrl() {
            var protocol = window.location.protocol;
            var hostname = window.location.hostname;
            var port = (protocol === 'https:') ? '9443' : '9000';
            return protocol + "//" + hostname + ":" + port;
        }

        function launch() {
            var url = getPortainerUrl();
            window.open(url, '_blank');
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            var url = getPortainerUrl();
            document.getElementById('target-url').innerText = url;
            document.getElementById('btn-launch').addEventListener('click', launch);
        });

/usr/share/cockpit/portainer-link/manifest.json:
  file.managed:
    - contents: |
        {
            "version": "1.3",
            "tools": {
                "portainer-link": {
                    "label": "App Manager (Portainer)",
                    "path": "launcher.html",
                    "priority": 20
                }
            }
        }