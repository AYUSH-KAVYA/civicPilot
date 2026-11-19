"""
Geospatial Tool: geo_lookup
Resolves citizen coordinates and addresses to administrative wards and offices.
Uses Shapely for point-in-polygon checks and OpenStreetMap Nominatim for geocoding with graceful fallback.
Source of truth: docs/CONTRACT.md Section 6.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from shapely.geometry import Point, shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.db.models import OfficeModel, WardModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.tools.registry import tools

DEFAULT_CITY_LAT = 37.750
DEFAULT_CITY_LNG = -122.420
DEFAULT_CITY_ADDRESS = "City Hall Plaza, Metroville"


async def geocode_address(address_text: str) -> Optional[Dict[str, Any]]:
    """Geocode address text to coordinates using OpenStreetMap Nominatim."""
    settings = get_settings()
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address_text, "format": "json", "limit": 1}

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return {
                        "lat": float(data[0]["lat"]),
                        "lng": float(data[0]["lon"]),
                        "formatted_address": data[0].get("display_name", address_text),
                    }
    except Exception as e:
        print(f"[geo_lookup warning] Nominatim geocoding failed: {e}. Using fallback.")
    return None


@tools.register("geo_lookup")
async def geo_lookup(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    address_text: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Look up administrative ward and municipal office for given coordinates or address.
    Returns: {ward_id, ward_name, office_id, office_name, lat, lng, formatted_address}
    """
    formatted_address = address_text

    # 1. Geocode if coordinates are missing
    if (lat is None or lng is None) and address_text:
        geocoded = await geocode_address(address_text)
        if geocoded:
            lat = geocoded["lat"]
            lng = geocoded["lng"]
            formatted_address = geocoded["formatted_address"]
        else:
            # Fallback to default city center coordinates
            lat = DEFAULT_CITY_LAT
            lng = DEFAULT_CITY_LNG
            formatted_address = f"{address_text}, Metroville"

    if lat is None or lng is None:
        lat = DEFAULT_CITY_LAT
        lng = DEFAULT_CITY_LNG
        formatted_address = DEFAULT_CITY_ADDRESS

    pt = Point(lng, lat)  # Note: Shapely Point is (x=longitude, y=latitude)

    # 2. Query wards and offices from database
    async def _resolve_ward(session: AsyncSession) -> Dict[str, Any]:
        result = await session.execute(select(WardModel))
        wards = result.scalars().all()

        matched_ward: Optional[WardModel] = None
        min_distance = float("inf")
        nearest_ward: Optional[WardModel] = None

        for w in wards:
            poly = shape(w.boundary_geojson)
            if poly.contains(pt) or poly.intersects(pt):
                matched_ward = w
                break
            # Calculate distance to polygon centroid for nearest-neighbor fallback
            dist = poly.centroid.distance(pt)
            if dist < min_distance:
                min_distance = dist
                nearest_ward = w

        chosen_ward = matched_ward or nearest_ward
        if not chosen_ward:
            # Fallback if wards table has not been seeded yet
            return {
                "ward_id": "ward-1",
                "ward_name": "Ward 1 - Downtown Core",
                "office_id": "office-ward-1",
                "office_name": "Downtown Municipal Center",
                "lat": lat,
                "lng": lng,
                "formatted_address": formatted_address or DEFAULT_CITY_ADDRESS,
            }

        # Resolve Office
        office_id = chosen_ward.office_id or f"office-{chosen_ward.id}"
        office_name = f"{chosen_ward.name} Office"
        if chosen_ward.office_id:
            office = await session.get(OfficeModel, chosen_ward.office_id)
            if office:
                office_name = office.name

        return {
            "ward_id": chosen_ward.id,
            "ward_name": chosen_ward.name,
            "office_id": office_id,
            "office_name": office_name,
            "lat": lat,
            "lng": lng,
            "formatted_address": formatted_address or f"{chosen_ward.name}, Metroville",
        }

    if db is not None:
        return await _resolve_ward(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _resolve_ward(session)
