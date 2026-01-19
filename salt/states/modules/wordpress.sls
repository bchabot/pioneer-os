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
    - user: root
    - group: root
    - mode: 777
    - makedirs: True
    - require:
      - file: /opt/pioneer/wordpress

/opt/pioneer/wordpress/db-data:
  file.directory:
    - user: root
    - group: root
    - mode: 777
    - makedirs: True
    - require:
      - file: /opt/pioneer/wordpress

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
    - require:
      - file: /opt/pioneer/wordpress/wp-content
      - file: /opt/pioneer/wordpress/db-data