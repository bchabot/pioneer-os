# pioneer-os/salt/states/core/landing.sls

/var/www/html/landing:
  file.directory:
    - makedirs: True
    - user: www-data
    - group: www-data

/var/www/html/landing/index.html:
  file.managed:
    - source: salt://salt/configs/landing/index.html
    - user: www-data
    - group: www-data
    - require:
      - file: /var/www/html/landing
