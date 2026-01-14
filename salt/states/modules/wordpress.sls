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
