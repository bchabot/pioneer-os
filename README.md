# Pioneer OS (Project Pioneer)

**A modular, secure, and ruggedized operating system for Raspberry Pi-based appliances.**

## The Vision
Pioneer OS is a single, unified codebase that powers four distinct hardware products by applying different configuration "States." It turns a standard Raspberry Pi into a mission-critical appliance.

## The 4 Product Configurations (Skins)

| Product | Role | Core Apps | Hardware Target |
| :--- | :--- | :--- | :--- |
| **Digital Ark** | Offline Knowledge Library | Kiwix, Calibre, Maps | Pi 3B+ / 4 (Low Power) |
| **Field Team** | Local Comm Hub | NextCloud, Rocket.Chat, Gitea | Pi 4 / 5 (Performance) |
| **Sovereign Home** | Privacy Server | Home Assistant, Vaultwarden, Immich | Pi 4 / 5 (Storage Heavy) |
| **Yacht Library** | Marine Computer | OpenCPN, Signal K, AIS | Pi 3B+ / 4 (Low Power) |

## Tech Stack
*   **Base OS:** Raspberry Pi OS Lite (64-bit) / Debian Bookworm.
*   **Management:** SaltStack (Masterless Mode).
*   **UI:** Cockpit Project (Web Admin) + Custom Dashboard Plugin.
*   **App Layer:** Docker / Podman (Containerized).
*   **Networking:** NetworkManager (Hotspot), WireGuard (VPN).

## Getting Started
*(Instructions to be added: Bootstrap script usage)*
