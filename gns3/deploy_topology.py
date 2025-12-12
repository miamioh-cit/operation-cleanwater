#!/usr/bin/env python3
"""
GNS3 topology builder (gns3fy).

Creates:
- 1 project
- 1 OT ethernet switch
- 1 gateway docker node (10.10.30.10/24)
- 20 PLC docker nodes (2 pumps x 10 cells) with static IPs
- Links all nodes to OT switch
- Starts all nodes

Runs on the GNS3 VM (Model A) using http://127.0.0.1:3080.

Requirements on GNS3 VM:
  pip3 install gns3fy pyyaml requests
"""

import yaml
from typing import Dict, Any
from gns3fy import Gns3Connector, Project, Node, Link


def ip_for(cell_index: int, pump: int, base_ip: int, stride: int) -> str:
    base = base_ip + (cell_index - 1) * stride
    return f"10.10.30.{base + pump}"


def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main(cfg_path: str = "gns3/config.yaml") -> None:
    cfg = load_cfg(cfg_path)
    gcfg = cfg["gns3"]
    images = cfg["images"]
    gateway_cfg = cfg.get("gateway", {})
    cells_cfg = cfg["cells"]

    gns3 = Gns3Connector(url=gcfg["url"])

    proj = Project(name=gcfg["project_name"], connector=gns3)
    try:
        proj.get()
        proj.open()
    except Exception:
        proj.create()
        proj.get()
        proj.open()

    # OT switch
    ot_sw = Node(
        project_id=proj.project_id,
        connector=gns3,
        name=gcfg["ot_switch_name"],
        node_type="ethernet_switch",
        compute_id=gcfg["compute_id"],
        x=0, y=0
    )
    try:
        ot_sw.create()
        ot_sw.get()
    except Exception:
        ot_sw.get()

    def docker_node(name: str, image: str, env: Dict[str, str], x: int, y: int) -> Node:
        n = Node(
            project_id=proj.project_id,
            connector=gns3,
            name=name,
            node_type="docker",
            compute_id=gcfg["compute_id"],
            x=x, y=y,
            properties={
                "image": image,
                "environment": env,
                "cap_add": ["NET_ADMIN"],
                "memory": 128,
                "console_type": "telnet",
            }
        )
        n.create()
        n.get()
        return n

    sw_port = 0

    def link_to_switch(node: Node) -> None:
        nonlocal sw_port
        link = Link(
            project_id=proj.project_id,
            connector=gns3,
            nodes=[
                {"node_id": node.node_id, "adapter_number": 0, "port_number": 0},
                {"node_id": ot_sw.node_id, "adapter_number": 0, "port_number": sw_port},
            ]
        )
        link.create()
        sw_port += 1

    # Gateway
    gw_name = gateway_cfg.get("name", "OT-Gateway")
    gw_ip_cidr = gateway_cfg.get("ip_cidr", "10.10.30.10/24")
    gw_gw = gateway_cfg.get("gw", "")

    gw = docker_node(
        name=gw_name,
        image=images["gateway_image"],
        env={"IP_CIDR": gw_ip_cidr, "GW": gw_gw},
        x=380, y=-260
    )
    link_to_switch(gw)

    # PLCs
    count = int(cells_cfg["count"])
    base_ip = int(cells_cfg.get("base_ip", 100))
    stride = int(cells_cfg.get("stride", 10))
    plc_image = images["plc_image"]

    for i in range(1, count + 1):
        cell = f"cell{i:02d}"
        x = -520 + (i - 1) * 115

        ip1 = ip_for(i, 1, base_ip, stride)
        ip2 = ip_for(i, 2, base_ip, stride)

        plc1 = docker_node(
            name=f"{cell}-pump1-plc",
            image=plc_image,
            env={
                "CELL_ID": cell,
                "PUMP_NAME": "pump1",
                "IP_CIDR": f"{ip1}/24",
                "GW": gw_gw,
                "MODBUS_PORT": "1502",
                "S7_PORT": "1102",
                "HTTP_PORT": "8080",
            },
            x=x, y=140
        )
        link_to_switch(plc1)

        plc2 = docker_node(
            name=f"{cell}-pump2-plc",
            image=plc_image,
            env={
                "CELL_ID": cell,
                "PUMP_NAME": "pump2",
                "IP_CIDR": f"{ip2}/24",
                "GW": gw_gw,
                "MODBUS_PORT": "1502",
                "S7_PORT": "1102",
                "HTTP_PORT": "8080",
            },
            x=x, y=270
        )
        link_to_switch(plc2)

    # Start everything
    proj.get()
    for n in proj.nodes:
        try:
            Node(project_id=proj.project_id, connector=gns3, node_id=n["node_id"]).start()
        except Exception:
            pass

    print("✅ Topology deployed and started.")
    print("HMI: http://10.10.30.10:8000/ (from OT network)")


if __name__ == "__main__":
    main()
