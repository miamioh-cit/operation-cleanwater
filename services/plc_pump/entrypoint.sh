#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${IP_CIDR:-}" ]]; then
  ip link set dev eth0 up || true
  ip addr flush dev eth0 || true
  ip addr add "${IP_CIDR}" dev eth0
fi
if [[ -n "${GW:-}" ]]; then
  ip route replace default via "${GW}" dev eth0
fi
exec python /app/app.py
