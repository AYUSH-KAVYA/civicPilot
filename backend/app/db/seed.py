"""
Seed data for CivicPilot.
Creates:
- 6 city departments (Water, Roads, Sanitation, Electricity, Parks, Public Health)
- 10 sample wards with valid GeoJSON Polygons and an office per ward in fictional Metroville
- 15 municipal response crews with positions and contact info
- Sample policy chunks with SLA guidelines
"""

import asyncio
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    CrewModel,
    DepartmentModel,
    OfficeModel,
    PolicyChunkModel,
    WardModel,
)
from backend.app.db.session import AsyncSessionLocal, init_db_extensions

DEPARTMENTS_DATA = [
    {
        "id": "water",
        "name": "Water & Sewerage Department",
        "code": "WTR",
        "contact_email": "water.dispatch@metroville.gov",
        "description": "Responsible for water mains, leaks, sewage overflows, drainage, and water quality.",
        "sla_hours_default": 12.0,
    },
    {
        "id": "roads",
        "name": "Roads & Transportation Infrastructure",
        "code": "RDS",
        "contact_email": "roads.dispatch@metroville.gov",
        "description": "Responsible for potholes, asphalt damage, road signs, traffic signals, and sidewalk repairs.",
        "sla_hours_default": 24.0,
    },
    {
        "id": "sanitation",
        "name": "Sanitation & Solid Waste Management",
        "code": "SAN",
        "contact_email": "sanitation.dispatch@metroville.gov",
        "description": "Handles garbage collection, illegal dumping, street cleaning, and dead animal removal.",
        "sla_hours_default": 8.0,
    },
    {
        "id": "electricity",
        "name": "Public Lighting & Electrical Grid",
        "code": "ELE",
        "contact_email": "electricity.dispatch@metroville.gov",
        "description": "Maintains streetlights, exposed wiring, electrical poles, and municipal power fixtures.",
        "sla_hours_default": 6.0,
    },
    {
        "id": "parks",
        "name": "Parks & Urban Forestry",
        "code": "PRK",
        "contact_email": "parks.dispatch@metroville.gov",
        "description": "Cares for public parks, playground hazards, fallen tree branches, and city landscaping.",
        "sla_hours_default": 48.0,
    },
    {
        "id": "public_health",
        "name": "Public Health & Environmental Safety",
        "code": "HLT",
        "contact_email": "health.dispatch@metroville.gov",
        "description": "Manages pest control, standing contaminated water, hazardous bio-waste, and restaurant hygiene.",
        "sla_hours_default": 16.0,
    },
]

# Metroville center: lat 37.750, lng -122.420
# 10 adjacent grid wards (roughly 0.01 deg ~= 1.1 km)
WARDS_DATA = [
    {
        "id": "ward-1",
        "name": "Ward 1 - Downtown Core",
        "office_id": "office-ward-1",
        "min_lat": 37.745, "max_lat": 37.755,
        "min_lng": -122.425, "max_lng": -122.415,
        "office": {
            "id": "office-ward-1",
            "name": "Downtown Municipal Center",
            "address": "100 City Hall Plaza, Metroville",
            "lat": 37.750, "lng": -122.420,
        },
    },
    {
        "id": "ward-2",
        "name": "Ward 2 - North District",
        "office_id": "office-ward-2",
        "min_lat": 37.755, "max_lat": 37.765,
        "min_lng": -122.425, "max_lng": -122.415,
        "office": {
            "id": "office-ward-2",
            "name": "North District Office",
            "address": "450 North Boulevard, Metroville",
            "lat": 37.760, "lng": -122.420,
        },
    },
    {
        "id": "ward-3",
        "name": "Ward 3 - South Gate",
        "office_id": "office-ward-3",
        "min_lat": 37.735, "max_lat": 37.745,
        "min_lng": -122.425, "max_lng": -122.415,
        "office": {
            "id": "office-ward-3",
            "name": "South Gate Civic Annex",
            "address": "210 South Gateway Ave, Metroville",
            "lat": 37.740, "lng": -122.420,
        },
    },
    {
        "id": "ward-4",
        "name": "Ward 4 - East Riverfront",
        "office_id": "office-ward-4",
        "min_lat": 37.745, "max_lat": 37.755,
        "min_lng": -122.415, "max_lng": -122.405,
        "office": {
            "id": "office-ward-4",
            "name": "Riverfront Services Bureau",
            "address": "88 Waterfront Way, Metroville",
            "lat": 37.750, "lng": -122.410,
        },
    },
    {
        "id": "ward-5",
        "name": "Ward 5 - West Hills",
        "office_id": "office-ward-5",
        "min_lat": 37.745, "max_lat": 37.755,
        "min_lng": -122.435, "max_lng": -122.425,
        "office": {
            "id": "office-ward-5",
            "name": "West Hills Municipal Post",
            "address": "730 Skyline Road, Metroville",
            "lat": 37.750, "lng": -122.430,
        },
    },
    {
        "id": "ward-6",
        "name": "Ward 6 - Northeast Heights",
        "office_id": "office-ward-6",
        "min_lat": 37.755, "max_lat": 37.765,
        "min_lng": -122.415, "max_lng": -122.405,
        "office": {
            "id": "office-ward-6",
            "name": "Northeast Community Hub",
            "address": "512 Highland Drive, Metroville",
            "lat": 37.760, "lng": -122.410,
        },
    },
    {
        "id": "ward-7",
        "name": "Ward 7 - Northwest Ridge",
        "office_id": "office-ward-7",
        "min_lat": 37.755, "max_lat": 37.765,
        "min_lng": -122.435, "max_lng": -122.425,
        "office": {
            "id": "office-ward-7",
            "name": "Northwest District Center",
            "address": "334 Forest Crest Lane, Metroville",
            "lat": 37.760, "lng": -122.430,
        },
    },
    {
        "id": "ward-8",
        "name": "Ward 8 - Southeast Meadows",
        "office_id": "office-ward-8",
        "min_lat": 37.735, "max_lat": 37.745,
        "min_lng": -122.415, "max_lng": -122.405,
        "office": {
            "id": "office-ward-8",
            "name": "Southeast Administrative Post",
            "address": "902 Meadowland Court, Metroville",
            "lat": 37.740, "lng": -122.410,
        },
    },
    {
        "id": "ward-9",
        "name": "Ward 9 - Southwest Valley",
        "office_id": "office-ward-9",
        "min_lat": 37.735, "max_lat": 37.745,
        "min_lng": -122.435, "max_lng": -122.425,
        "office": {
            "id": "office-ward-9",
            "name": "Valley Civic Center",
            "address": "115 Orchard Pass, Metroville",
            "lat": 37.740, "lng": -122.430,
        },
    },
    {
        "id": "ward-10",
        "name": "Ward 10 - Harbor Industrial",
        "office_id": "office-ward-10",
        "min_lat": 37.745, "max_lat": 37.755,
        "min_lng": -122.405, "max_lng": -122.395,
        "office": {
            "id": "office-ward-10",
            "name": "Harbor Works Bureau",
            "address": "15 Dockside Terminal, Metroville",
            "lat": 37.750, "lng": -122.400,
        },
    },
]

CREWS_DATA = [
    {"id": "crew-wtr-01", "department_id": "water", "name": "Water Rapid Repair Unit 1", "lat": 37.749, "lng": -122.418, "status": "available", "contact": "+1-555-0101"},
    {"id": "crew-wtr-02", "department_id": "water", "name": "Sewer Maintenance Crew 2", "lat": 37.758, "lng": -122.422, "status": "available", "contact": "+1-555-0102"},
    {"id": "crew-wtr-03", "department_id": "water", "name": "Mains Emergency Crew 3", "lat": 37.738, "lng": -122.412, "status": "available", "contact": "+1-555-0103"},

    {"id": "crew-rds-01", "department_id": "roads", "name": "Pothole Patching Crew Alpha", "lat": 37.752, "lng": -122.421, "status": "available", "contact": "+1-555-0201"},
    {"id": "crew-rds-02", "department_id": "roads", "name": "Traffic Signals & Signs Unit", "lat": 37.762, "lng": -122.415, "status": "available", "contact": "+1-555-0202"},
    {"id": "crew-rds-03", "department_id": "roads", "name": "Asphalt Resurfacing Team Gamma", "lat": 37.742, "lng": -122.428, "status": "available", "contact": "+1-555-0203"},

    {"id": "crew-san-01", "department_id": "sanitation", "name": "Downtown Waste Removal Crew", "lat": 37.748, "lng": -122.419, "status": "available", "contact": "+1-555-0301"},
    {"id": "crew-san-02", "department_id": "sanitation", "name": "Street Sweeper Team West", "lat": 37.753, "lng": -122.432, "status": "available", "contact": "+1-555-0302"},
    {"id": "crew-san-03", "department_id": "sanitation", "name": "Bulk Debris & Dump Clearers", "lat": 37.739, "lng": -122.408, "status": "available", "contact": "+1-555-0303"},

    {"id": "crew-ele-01", "department_id": "electricity", "name": "Streetlight Repair Unit 1", "lat": 37.751, "lng": -122.423, "status": "available", "contact": "+1-555-0401"},
    {"id": "crew-ele-02", "department_id": "electricity", "name": "High Voltage & Grid Crew 2", "lat": 37.759, "lng": -122.429, "status": "available", "contact": "+1-555-0402"},

    {"id": "crew-prk-01", "department_id": "parks", "name": "Urban Forestry Tree Crew", "lat": 37.757, "lng": -122.411, "status": "available", "contact": "+1-555-0501"},
    {"id": "crew-prk-02", "department_id": "parks", "name": "Park Safety & Playgrounds Team", "lat": 37.743, "lng": -122.424, "status": "available", "contact": "+1-555-0502"},

    {"id": "crew-hlt-01", "department_id": "public_health", "name": "Vector & Pest Control Unit", "lat": 37.747, "lng": -122.417, "status": "available", "contact": "+1-555-0601"},
    {"id": "crew-hlt-02", "department_id": "public_health", "name": "Biohazard & Health Inspection", "lat": 37.761, "lng": -122.404, "status": "available", "contact": "+1-555-0602"},
]

POLICY_CHUNKS_DATA = [
    {
        "id": "policy-wtr-01",
        "department_id": "water",
        "doc_title": "Water Main Ruptures & Contamination Standard Operating Procedure",
        "text": "Critical water main breaks affecting drinking water or causing flooding must be triaged as critical urgency. SLA is 4 hours for containment and 12 hours for restoration. If hospital or school nearby, escalate to supervisor immediately.",
        "sla_hours": 4.0,
        "escalation_rule": "Escalate to supervisor if water outage affects >100 residents or sensitive health facility.",
    },
    {
        "id": "policy-rds-01",
        "department_id": "roads",
        "doc_title": "Pothole & Road Hazard Remediation Policy",
        "text": "Deep potholes (>10cm depth) or road collapse on arterial roads must be marked and repaired within 24 hours. Minor residential street fissures have standard 72 hour SLA. Potholes threatening cyclist safety near bike lanes carry high urgency.",
        "sla_hours": 24.0,
        "escalation_rule": "Notify transit authority if bus route is obstructed.",
    },
    {
        "id": "policy-san-01",
        "department_id": "sanitation",
        "doc_title": "Illegal Dumping & Waste Hazard Response",
        "text": "Illegal dumping of household waste or biohazard blocking sidewalks must be cleared within 8 hours. Rotting waste near food establishments is high priority. Standard non-hazardous litter collection within 48 hours.",
        "sla_hours": 8.0,
        "escalation_rule": "Report repeat commercial dumping to municipal enforcement officer.",
    },
    {
        "id": "policy-ele-01",
        "department_id": "electricity",
        "doc_title": "Exposed Wiring & Critical Lighting Outage Protocol",
        "text": "Downed electrical wires or sparking poles require immediate critical dispatch within 2 hours. Streetlight blackouts covering more than two consecutive blocks require resolution within 6 hours.",
        "sla_hours": 2.0,
        "escalation_rule": "Immediate dispatch of fire safety and police perimeter if wires are live on roadway.",
    },
]


def make_geojson_polygon(min_lat: float, max_lat: float, min_lng: float, max_lng: float) -> Dict[str, Any]:
    """Create a GeoJSON Polygon from bounding coordinates."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lng, min_lat],
                [max_lng, min_lat],
                [max_lng, max_lat],
                [min_lng, max_lat],
                [min_lng, min_lat],  # Closed ring
            ]
        ],
    }


async def seed_database(session: AsyncSession) -> None:
    """Populate database with initial master data."""
    # 1. Departments
    for dept_data in DEPARTMENTS_DATA:
        existing = await session.get(DepartmentModel, dept_data["id"])
        if not existing:
            dept = DepartmentModel(**dept_data)
            session.add(dept)

    # 2. Wards & Offices
    for w in WARDS_DATA:
        # Check and insert ward first so foreign keys succeed
        existing_ward = await session.get(WardModel, w["id"])
        if not existing_ward:
            polygon = make_geojson_polygon(w["min_lat"], w["max_lat"], w["min_lng"], w["max_lng"])
            ward = WardModel(
                id=w["id"],
                name=w["name"],
                office_id=w["office_id"],
                boundary_geojson=polygon,
            )
            session.add(ward)

    await session.flush()

    for w in WARDS_DATA:
        # Now insert office referencing ward_id
        office_data = w["office"]
        existing_office = await session.get(OfficeModel, office_data["id"])
        if not existing_office:
            office = OfficeModel(
                id=office_data["id"],
                name=office_data["name"],
                ward_id=w["id"],
                address=office_data["address"],
                lat=office_data["lat"],
                lng=office_data["lng"],
            )
            session.add(office)

    # 3. Crews
    for crew_data in CREWS_DATA:
        existing_crew = await session.get(CrewModel, crew_data["id"])
        if not existing_crew:
            crew = CrewModel(**crew_data)
            session.add(crew)

    # 4. Policy Chunks
    for policy_data in POLICY_CHUNKS_DATA:
        existing_chunk = await session.get(PolicyChunkModel, policy_data["id"])
        if not existing_chunk:
            chunk = PolicyChunkModel(**policy_data)
            session.add(chunk)

    await session.commit()
    print("[Seed] Database successfully seeded with 6 departments, 10 wards, 10 offices, 15 crews, and policies.")


async def main() -> None:
    await init_db_extensions()
    async with AsyncSessionLocal() as session:
        await seed_database(session)


if __name__ == "__main__":
    asyncio.run(main())
