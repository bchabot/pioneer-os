# pioneer-os/salt/states/core/proxy.sls

install_nginx:
  pkg.installed:
    - name: nginx

# Create SSL Directory
/etc/nginx/ssl:
  file.directory:
    - makedirs: True

# Generate Self-Signed Cert (Idempotent: only if missing)
generate_ssl_cert:
  cmd.run:
    - name: |
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/pioneer.key \
        -out /etc/nginx/ssl/pioneer.crt \
        -subj "/C=US/ST=State/L=City/O=PioneerOS/OU=Edge/CN=pioneer.local"
    - unless: test -f /etc/nginx/ssl/pioneer.crt

# Deploy Nginx Config
/etc/nginx/sites-available/pioneer:
  file.managed:
    - source: salt://salt/configs/nginx/pioneer.conf
    - require:
      - pkg: install_nginx

# Enable Site
enable_site:
  file.symlink:
    - name: /etc/nginx/sites-enabled/pioneer
    - target: /etc/nginx/sites-available/pioneer
    - require:
      - file: /etc/nginx/sites-available/pioneer

# Disable Default
disable_default:
  file.absent:
    - name: /etc/nginx/sites-enabled/default

# Restart Nginx
nginx_service:
  service.running:
    - name: nginx
    - enable: True
    - reload: True
    - watch:
      - file: /etc/nginx/sites-available/pioneer
