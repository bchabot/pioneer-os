# pioneer-os/salt/states/core/portainer.sls

# Install Portainer (The "App Store" UI)
# This gives the user a Web UI to manage WordPress, NextCloud, etc.

portainer_volume:
  cmd.run:
    - name: docker volume create portainer_data
    - unless: docker volume inspect portainer_data

portainer_container:
  cmd.run:
    - name: |
        docker run -d -p 9000:9000 -p 9443:9443 --name portainer \
        --restart=always \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v portainer_data:/data \
        portainer/portainer-ce:latest
    - unless: docker ps -a | grep portainer
