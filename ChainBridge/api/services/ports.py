"""Lightweight port lookup and distance utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


@dataclass
class Port:
    code: str
    name: str
    country: str
    lat: float
    lon: float


# Minimal world list for demo/analytics rollups. Expand as needed.
PORTS: List[Port] = [
    Port("USLAX", "Los Angeles", "US", 33.7406, -118.2760),
    Port("USNYC", "New York", "US", 40.7128, -74.0060),
    Port("USHOU", "Houston", "US", 29.7550, -95.3670),
    Port("MXVER", "Veracruz", "MX", 19.1738, -96.1342),
    Port("MXMZT", "Mazatlan", "MX", 23.2494, -106.4111),
    Port("CNSHA", "Shanghai", "CN", 31.2304, 121.4737),
    Port("CNSZX", "Shenzhen", "CN", 22.5431, 114.0579),
    Port("NLRDM", "Rotterdam", "NL", 51.9244, 4.4777),
    Port("GBFXT", "Felixstowe", "GB", 51.9550, 1.3500),
    Port("JPTYO", "Tokyo", "JP", 35.6762, 139.6503),
    Port("SGSIN", "Singapore", "SG", 1.3521, 103.8198),
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def nearest_port(lat: float, lon: float, ports: Iterable[Port] = PORTS) -> Tuple[Port, float]:
    closest: Optional[Tuple[Port, float]] = None
    for port in ports:
        dist = haversine_km(lat, lon, port.lat, port.lon)
        if closest is None or dist < closest[1]:
            closest = (port, dist)
    assert closest is not None
    return closest
