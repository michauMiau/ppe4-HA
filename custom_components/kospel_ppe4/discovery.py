"""Support for discovery via the heater's config webpage and SSDP-like probing.

The PPE4 does not advertise a standard mDNS service. Discovery works by:
1. Scanning for hosts with an open HTTP port serving the KOSPEL config page.
2. Verifying the device by requesting /api/1128/1 and checking the JSON shape.

This module provides a helper used by the config flow's "discovered devices"
list; zeroconf/mDNS is not supported natively by the heater firmware.
"""
from __future__ import annotations

import asyncio
import ipaddress

import aiohttp

API_CHECK = "/api/1128/1"
TIMEOUT = aiohttp.ClientTimeout(total=3)


async def _probe(session: aiohttp.ClientSession, ip: str, found: dict[str, str]) -> None:
    url = f"http://{ip}{API_CHECK}"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return
            data = await resp.json(content_type=None)
            # PPE4 answers with {"ver":"1.0","status":"OK","res":{...}}
            if isinstance(data, dict) and data.get("status") == "OK" and "res" in data:
                found[ip] = "KOSPEL PPE4"
    except Exception:  # noqa: BLE001 - probe errors are expected
        return


async def discover(hass, network: str = "192.168.1.0/24") -> dict[str, str]:
    """Probe a /24 network for PPE4 heaters. Returns {ip: name}."""
    net = ipaddress.ip_network(network, strict=False)
    found: dict[str, str] = {}
    session = aiohttp.async_get_clientsession(hass)
    async with asyncio.TaskGroup() as tg:
        for host in net.hosts():
            tg.create_task(_probe(session, str(host), found))
    return found
