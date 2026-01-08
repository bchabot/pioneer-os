# pioneer-os/salt/states/core/docker.sls

docker_service:
  service.running:
    - name: docker
    - enable: True
