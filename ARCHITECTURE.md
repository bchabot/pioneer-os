# Architectural Decision Record (ADR)

## 001: Containerization vs. Bare Metal
**Status:** Decided
**Decision:** All "User Applications" (Apps) will be containerized. Core System Services will be Bare Metal.

### Context
We are building an appliance that needs to run on hardware ranging from a Raspberry Pi 3B (1GB RAM) to a Pi 5 (8GB RAM). We need to support diverse software stacks (PHP for NextCloud, Python for Home Assistant, C++ for OpenCPN) without creating "Dependency Hell."

### Options
1.  **Bare Metal (Apt/Pip):** Install everything directly on the OS.
    *   *Pros:* Max efficiency, lowest disk usage.
    *   *Cons:* Updates are risky. Uninstalling is messy. Config drift is likely. Hard to support 4 products on one codebase.
2.  **Containerization (Docker/Podman):** Run apps in isolated sandboxes.
    *   *Pros:* Atomic updates (pull new image), perfect isolation, easy rollback.
    *   *Cons:* CPU/RAM overhead.

### The Verdict
We will use **Docker (composed)** for all "Product Modules" (NextCloud, Kiwix, etc.).
*   **Efficiency Concern:** The overhead of Docker on Linux is minimal (namespaces/cgroups). The real cost is the application memory usage.
*   **Hardware Minimum:** 
    *   **Pi 3B (1GB):** Can run *Ark* and *Yacht* (Static content, lightweight C++ apps).
    *   **Pi 4 (2GB+):** Required for *Field* and *Home* (NextCloud/Home Assistant are RAM hungry).
*   **Implementation:** SaltStack will manage `docker-compose.yml` files, ensuring the system state is idempotent.

## 002: Management Engine
**Decision:** SaltStack (Masterless)
*   We do not need a central server controlling these devices (they may be offline).
*   The device manages itself using local Salt Formulas.
