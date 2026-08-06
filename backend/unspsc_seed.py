"""UNSPSC-lite seed — curated 60+ node subset relevant to PMC Managers.

Levels:  Segment (2-digit)  →  Family (4-digit)  →  Class (6-digit).
Sourced from the public UNSPSC v25 tree; only the segments PMC operates in.
"""

def _n(code, title, parent=None, category=None):
    return {
        "code": str(code),
        "title": title,
        "parent_code": parent,
        "level": {2: "segment", 4: "family", 6: "class"}.get(len(str(code)), "class"),
        "category": category,
    }


UNSPSC_NODES = [
    # ---- 30  Structures, Building & Construction Components ----
    _n("30", "Structures, Building & Construction Components"),
    _n("3010", "Structural building products", parent="30"),
    _n("301017", "Precast structural components", parent="3010"),
    _n("3011", "Building & construction materials", parent="30"),
    _n("301116", "Building sealants & caulks", parent="3011"),
    _n("3015", "Doors, windows & glass", parent="30"),
    _n("301510", "Doors and windows", parent="3015"),
    _n("3017", "Bulk materials", parent="30"),
    _n("301701", "Cement and lime", parent="3017"),

    # ---- 40  Distribution & Conditioning (HVAC, plumbing, gases) ----
    _n("40", "Distribution & Conditioning Systems, Equipment & Components"),
    _n("4014", "Fluid & gas distribution", parent="40"),
    _n("401416", "Pipes & pipe fittings", parent="4014"),
    _n("4015", "Industrial pumps", parent="40"),
    _n("4016", "Industrial filtering & purification", parent="40"),
    _n("4017", "Heating, ventilation & air-conditioning (HVAC)", parent="40"),
    _n("401716", "HVAC air-handling units", parent="4017"),

    # ---- 41  Laboratory & Measuring & Observing Equipment ----
    _n("41", "Laboratory, Measuring, Observing & Testing Equipment"),
    _n("4111", "Measuring & observing & testing", parent="41"),

    # ---- 42  Medical Equipment, Accessories & Supplies ----
    _n("42", "Medical Equipment, Accessories & Supplies"),
    _n("4218", "Medical apparel", parent="42"),
    _n("4219", "Medical facility products", parent="42"),
    _n("421917", "Modular operating theatre systems", parent="4219"),
    _n("422015", "Medical gases pipeline systems (MGPS)", parent="4219"),

    # ---- 43  IT, Telecom & Computing ----
    _n("43", "Information Technology Broadcasting & Telecommunications"),
    _n("4321", "Data & voice communication devices", parent="43"),
    _n("4322", "Computer equipment & accessories", parent="43"),
    _n("4323", "Software", parent="43"),
    _n("432315", "Business software", parent="4323"),
    _n("432316", "System-management software", parent="4323"),
    _n("432411", "Cloud & hosted services", parent="4323"),

    # ---- 44  Office equipment ----
    _n("44", "Office Equipment, Accessories & Supplies"),
    _n("4410", "Office equipment", parent="44"),
    _n("4412", "Office supplies", parent="44"),

    # ---- 46  Defence & Public Safety ----
    _n("46", "Defence, Law-Enforcement, Security & Safety Equipment"),
    _n("4617", "Public safety & control", parent="46"),

    # ---- 47  Cleaning & maintenance ----
    _n("47", "Cleaning Equipment & Supplies"),

    # ---- 55  Published Products ----
    _n("55", "Published Products"),
    _n("5510", "Printed publications", parent="55"),

    # ---- 71  Farming & Fishing (rarely used here) ----
    # skipped

    # ---- 72  Building & Facility Construction & Maintenance Services ----
    _n("72", "Building & Facility Construction & Maintenance Services"),
    _n("7210", "Building construction & support & maintenance services", parent="72"),
    _n("721015", "General building construction", parent="7210"),
    _n("721017", "Specialised trade construction", parent="7210"),
    _n("721025", "Facility building maintenance and repair", parent="7210"),
    _n("7211", "Heavy construction of civil & marine projects", parent="72"),
    _n("721114", "Highway & road construction", parent="7211"),
    _n("7212", "Specialised trade construction & maintenance", parent="72"),
    _n("721214", "Plumbing construction", parent="7212"),
    _n("721215", "Electrical construction", parent="7212"),
    _n("721216", "HVAC installation and maintenance", parent="7212"),

    # ---- 76  Industrial Cleaning ----
    _n("76", "Industrial Cleaning Services"),

    # ---- 77  Environmental services ----
    _n("77", "Environmental Services"),
    _n("7710", "Environmental management", parent="77"),
    _n("7712", "Environmental protection", parent="77"),

    # ---- 78  Transportation, Storage & Mail ----
    _n("78", "Transportation, Storage & Mail Services"),
    _n("7818", "Freight transportation", parent="78"),

    # ---- 80  Business & Corporate Management Services ----
    _n("80", "Management & Business Professionals & Administrative Services"),
    _n("8010", "Management advisory services", parent="80"),
    _n("801016", "Business intelligence consulting", parent="8010"),
    _n("801017", "Project management (PMC/PMO)", parent="8010"),
    _n("8011", "Human resources services", parent="80"),
    _n("8014", "Marketing & distribution", parent="80"),
    _n("8016", "Business administration services", parent="80"),
    _n("801611", "Financial-record services", parent="8016"),

    # ---- 81  Engineering, Research & Technology-Based Services ----
    _n("81", "Engineering, Research & Technology-Based Services"),
    _n("8110", "Professional engineering services", parent="81"),
    _n("811015", "Civil engineering", parent="8110"),
    _n("811017", "Mechanical engineering", parent="8110"),
    _n("811019", "Electrical & electronic engineering", parent="8110"),
    _n("8111", "Computer services", parent="81"),
    _n("811116", "Software development services", parent="8111"),
    _n("811117", "Application implementation services", parent="8111"),
    _n("811118", "Software or hardware maintenance", parent="8111"),

    # ---- 82  Editorial, Design & Media Services ----
    _n("82", "Editorial & Design & Graphic & Fine-Art Services"),

    # ---- 83  Public Utilities & Public Sector Services ----
    _n("83", "Public Utilities & Public-Sector-Related Services"),
    _n("8310", "Utilities", parent="83"),
    _n("831015", "Electric utilities", parent="8310"),
    _n("831016", "Water & wastewater utilities", parent="8310"),

    # ---- 84  Financial & Insurance Services ----
    _n("84", "Financial & Insurance Services"),

    # ---- 85  Healthcare Services ----
    _n("85", "Healthcare Services"),

    # ---- 86  Educational, Training & Library Services ----
    _n("86", "Educational, Training & Library Services"),
    _n("8610", "Vocational training", parent="86"),

    # ---- 91  Personal & Domestic Services ----
    # skipped

    # ---- 92  National Defence, Public Order & Security ----
    _n("92", "National Defence, Public Order, Security & Safety Services"),

    # ---- 93  Political / civic services ----
    _n("93", "Politics & Civic Affairs Services"),

    # ---- 95  Land & Buildings & Structures ----
    _n("95", "Land & Buildings & Structures & Thoroughfares"),
    _n("9512", "Permanent buildings & structures", parent="95"),
    _n("951217", "Educational buildings & structures (hostels, campuses)", parent="9512"),
    _n("951218", "Health-care buildings & structures", parent="9512"),
]
