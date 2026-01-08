base:
  '*':
    - core.networking
    - core.security
    - core.cockpit
    - core.docker
    - core.portainer  # Added Portainer for "App UI"

  # The POC Role (Testing everything)
  'roles:poc':
    - match: grain
    - modules.captive_portal
    - modules.wordpress