# pioneer-os/salt/states/modules/wordpress.sls

# Create the directory for WordPress Data
/opt/pioneer/wordpress:
  file.directory:
    - user: root
    - group: root
    - mode: 755
    - makedirs: True

# Create subdirectories with open permissions to avoid Docker bind mount issues
/opt/pioneer/wordpress/wp-content:
  file.directory:
    - mode: 775
    - makedirs: True
    - require:
      - file: /opt/pioneer/wordpress

/opt/pioneer/wordpress/db-data:
  file.directory:
    - mode: 775
    - makedirs: True
    - require:
      - file: /opt/pioneer/wordpress

# Ensure permissions are set to correct UIDs (33 for www-data, 999 for mysql)
fix_wordpress_permissions:
  cmd.run:
    - name: |
        chown -R 33:33 /opt/pioneer/wordpress/wp-content
        chown -R 999:999 /opt/pioneer/wordpress/db-data
    - require:
      - file: /opt/pioneer/wordpress/wp-content
      - file: /opt/pioneer/wordpress/db-data

# Deploy Docker Compose for WordPress + DB
/opt/pioneer/wordpress/docker-compose.yml:
  file.managed:
    - source: salt://salt/configs/wordpress/docker-compose.yml
    - makedirs: True
    - require:
      - cmd: fix_wordpress_permissions

# Run the Container
wordpress_service:
  cmd.run:
    - name: docker compose up -d
    - cwd: /opt/pioneer/wordpress
    - onchanges:
      - file: /opt/pioneer/wordpress/docker-compose.yml
    - require:
      - file: /opt/pioneer/wordpress/docker-compose.yml