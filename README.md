# OT Industrial Topology v1.0 – Code-Defined Industrial OT Topology (GNS3 + Jenkins)

This repo builds a full OT lab **entirely from code**:

- **GNS3 + gns3fy**: programmatically creates a project, switch, nodes, links, and starts everything.
- **PLC simulators (Docker)**: 1 container per pump, each exposes **Modbus TCP** + **Siemens S7comm** + a small debug API.
- **Gateway API (Docker)**: polls all PLCs and provides:
  - `GET /api/tags`
  - `GET /api/cells/{cell_id}`
  - HMI at `/` (static HTML/JS, no build step)

## Network Plan (default)
- OT LAN: `10.10.30.0/24`
- Gateway: `10.10.30.10`
- Cells: 10 cells, 2 pumps each
  - cell01 pump1: `10.10.30.101`
  - cell01 pump2: `10.10.30.102`
  - ...
  - cell10 pump1: `10.10.30.191`
  - cell10 pump2: `10.10.30.192`

Ports:
- PLC Modbus: `1502`
- PLC S7comm: `1102`
- PLC Debug HTTP: `8080`
- Gateway HTTP: `8000`

## Jenkins (Model A – Recommended)
gns3fy runs on the GNS3 VM and uses `http://127.0.0.1:3080`.
Jenkins uses Ansible to:
- copy repo to `/opt/ot-industrial-topology`
- build Docker images on the GNS3 VM
- generate `services/gateway/plcs.yaml`
- run `gns3/deploy_topology.py`

HMI (from OT network):
- `http://10.10.30.10:8000/`
