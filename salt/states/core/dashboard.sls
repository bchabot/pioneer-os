# pioneer-os/salt/states/core/dashboard.sls

# Install Dependencies via APT (More stable than PIP for system tools)
dashboard_pkgs:
  pkg.installed:
    - pkgs:
      - python3-flask
      - python3-psutil
      - iputils-ping

# Deploy Files
dashboard_dir:
  file.directory:
    - name: /opt/pioneer-dashboard
    - makedirs: True

dashboard_files:
  file.recurse:
    - name: /opt/pioneer-dashboard
    - source: salt://dashboard
    - include_empty: True
    - require:
      - file: dashboard_dir

# Systemd Service
dashboard_service_file:
  file.managed:
    - name: /etc/systemd/system/pioneer-dashboard.service
    - contents: |
        [Unit]
        Description=Pioneer Easy Dashboard
        After=network.target

        [Service]
        User=root
        WorkingDirectory=/opt/pioneer-dashboard
        ExecStart=/usr/bin/python3 app.py
        Restart=always

        [Install]
        WantedBy=multi-user.target
    - require:
      - file: dashboard_files
      - pkg: dashboard_pkgs

dashboard_service_running:
  service.running:
    - name: pioneer-dashboard
    - enable: True
    - watch:
      - file: dashboard_service_file
      - file: dashboard_files