"""Seed data — 30 representative KZ work packages across the programme.
Full 203 will be imported via CSV in production."""
from typing import List, Dict

KZ_PACKAGES: List[Dict] = [
    # Hospital / medical
    {"title": "Modular OT Suite — Astana Medical Campus Phase 1", "category": "Modular operation theatres (OTs)", "phase": "Health · Phase 1", "value": 6800000, "float_target_date": "2026-04-30", "status": "ready"},
    {"title": "Medical Gas Pipeline System — Wing A & B", "category": "Medical gas pipeline systems", "phase": "Health · Phase 1", "value": 2100000, "float_target_date": "2026-05-15", "status": "sbd_draft"},
    {"title": "OT Laminar Flow Ceilings & Ancillaries", "category": "OT equipment & laminar flow systems", "phase": "Health · Phase 1", "value": 1900000, "float_target_date": "2026-05-20", "status": "scoping"},
    {"title": "Hospital Civil & Superstructure — Block 1", "category": "Hospital civil & superstructure works", "phase": "Health · Phase 1", "value": 24000000, "float_target_date": "2026-06-01", "status": "sbd_draft"},
    {"title": "Hospital Civil & Superstructure — Block 2", "category": "Hospital civil & superstructure works", "phase": "Health · Phase 2", "value": 22500000, "float_target_date": "2026-08-15", "status": "backlog"},
    # Power / electrical
    {"title": "External 110/10 kV Grid Connection — University Precinct", "category": "External power supply grid connection", "phase": "Utilities · Phase 1", "value": 12500000, "float_target_date": "2026-05-20", "status": "ready"},
    {"title": "Substation Works HT/LT — Main Campus", "category": "Substation works (HT/LT)", "phase": "Utilities · Phase 1", "value": 4200000, "float_target_date": "2026-06-30", "status": "sbd_draft"},
    {"title": "Transformers Procurement & Installation — 4 units", "category": "Transformers procurement & installation", "phase": "Utilities · Phase 1", "value": 3600000, "float_target_date": "2026-07-15", "status": "scoping"},
    # Elevators & escalators
    {"title": "Elevators & Escalators — Academic Building", "category": "Elevators & escalators", "phase": "Academic · Phase 1", "value": 2800000, "float_target_date": "2026-07-01", "status": "backlog"},
    {"title": "Elevators — Hostel Blocks A–D", "category": "Elevators for hostel blocks", "phase": "Hostel · Phase 1", "value": 1400000, "float_target_date": "2026-06-15", "status": "scoping"},
    {"title": "Elevator & Escalator AMC (36 months)", "category": "Elevator & escalator AMC", "phase": "AMC · Ongoing", "value": 950000, "float_target_date": "2026-09-30", "status": "backlog"},
    # Fire safety
    {"title": "Fire Alarm & Safety Systems — Campus-wide", "category": "Fire alarm & safety systems", "phase": "Safety · Phase 1", "value": 3100000, "float_target_date": "2026-05-30", "status": "ready"},
    {"title": "External Firefighting Network — Hydrants Loop", "category": "External firefighting network (hydrants)", "phase": "Safety · Phase 1", "value": 1600000, "float_target_date": "2026-05-25", "status": "sbd_draft"},
    {"title": "Fire System AMC (24 months)", "category": "Fire system AMC", "phase": "AMC · Ongoing", "value": 480000, "float_target_date": "2026-10-15", "status": "backlog"},
    # Water / plumbing
    {"title": "Water Treatment Plant (WTP) — Main Campus", "category": "Water treatment plant (WTP)", "phase": "Utilities · Phase 1", "value": 5400000, "float_target_date": "2026-06-10", "status": "sbd_draft"},
    {"title": "Sewage Treatment Plant (STP) — Main Campus", "category": "Sewage treatment plant (STP)", "phase": "Utilities · Phase 1", "value": 4800000, "float_target_date": "2026-06-15", "status": "sbd_draft"},
    {"title": "Hostel Bathrooms & Plumbing — Blocks A–D", "category": "Hostel bathrooms & plumbing", "phase": "Hostel · Phase 1", "value": 1800000, "float_target_date": "2026-03-30", "status": "published"},
    # Academic / hostel
    {"title": "Main Academic Building Civil Works", "category": "Main academic building civil works", "phase": "Academic · Phase 1", "value": 38000000, "float_target_date": "2026-07-30", "status": "scoping"},
    # Hotel
    {"title": "Hotel Superstructure Works", "category": "Hotel superstructure works", "phase": "Hotel · Phase 1", "value": 28000000, "float_target_date": "2026-08-01", "status": "backlog"},
    # Additional variety across programme
    {"title": "HVAC Equipment — Academic Blocks A & B", "category": "HVAC", "phase": "Academic · Phase 1", "value": 3200000, "float_target_date": "2026-06-20", "status": "scoping"},
    {"title": "CCTV & Access Control — Campus-wide", "category": "CCTV", "phase": "Security · Phase 1", "value": 1400000, "float_target_date": "2026-06-25", "status": "backlog"},
    {"title": "PA & Audio Systems — Auditoriums", "category": "PA systems", "phase": "Academic · Phase 1", "value": 620000, "float_target_date": "2026-07-05", "status": "backlog"},
    {"title": "BMS Integration — Campus", "category": "BMS", "phase": "Utilities · Phase 1", "value": 1100000, "float_target_date": "2026-07-10", "status": "backlog"},
    {"title": "Modular Kitchen Equipment — Hostel Canteens", "category": "Kitchen equipment", "phase": "Hostel · Phase 1", "value": 780000, "float_target_date": "2026-06-05", "status": "backlog"},
    {"title": "Laundry Equipment — Hostel Blocks", "category": "Laundry", "phase": "Hostel · Phase 1", "value": 320000, "float_target_date": "2026-06-05", "status": "backlog"},
    {"title": "Signage & Wayfinding — Campus-wide", "category": "Signage", "phase": "Campus · Phase 1", "value": 460000, "float_target_date": "2026-08-15", "status": "backlog"},
    {"title": "Landscaping & External Roads", "category": "Landscaping", "phase": "Campus · Phase 2", "value": 5200000, "float_target_date": "2026-09-01", "status": "backlog"},
    {"title": "Solar PV Rooftop — Academic Roofs", "category": "Solar", "phase": "Utilities · Phase 2", "value": 2400000, "float_target_date": "2026-08-20", "status": "backlog"},
    {"title": "Diesel Gensets & UPS — Redundancy", "category": "Diesel gensets", "phase": "Utilities · Phase 1", "value": 1800000, "float_target_date": "2026-07-25", "status": "backlog"},
    {"title": "Boundary Walls & Storm Drainage", "category": "Boundary walls", "phase": "Campus · Phase 1", "value": 2900000, "float_target_date": "2026-07-30", "status": "backlog"},
]
