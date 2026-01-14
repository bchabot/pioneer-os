# pioneer-os/salt/states/modules/wordpress.sls

# Create the directory for WordPress Data
/opt/pioneer/wordpress:
  file.directory:
    - user: root
    - group: root
    - mode: 755
    - makedirs: True

# Deploy Docker Compose for WordPress + DB
/opt/pioneer/wordpress/docker-compose.yml:
  file.managed:
    - source: salt://salt/configs/wordpress/docker-compose.yml
    - makedirs: True

# Run the Container
wordpress_service:
  cmd.run:
    - name: docker compose up -d
    - cwd: /opt/pioneer/wordpress
    - onchanges:
      - file: /opt/pioneer/wordpress/docker-compose.yml

# Force the database to use the correct HTTPS URL
# This prevents WordPress from generating redirects to the old :8080 port.
update_wordpress_urls:
  cmd.run:
    - name: |
        docker exec wordpress-wordpress-1 wp option update home "https://pioneer-core.local/"
        docker exec wordpress-wordpress-1 wp option update siteurl "https://pioneer-core.local/"
    - require:
      - cmd: wordpress_service
    # Only run if the siteurl is incorrect
    - unless: docker exec wordpress-wordpress-1 wp option get siteurl | grep "https://pioneer-core.local/"