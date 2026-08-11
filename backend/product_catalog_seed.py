"""Wave 35 — Default product catalog derived from CA-02 (client) + CA-03 (supplier).

Every entry is a *default* — admins can edit any field (amount, currency,
pricing model, active state) from the Product Catalog panel. The seed only
inserts rows whose `code` doesn't already exist, so this stays idempotent
across restarts and reseed calls.
"""

DEFAULT_PRODUCTS = [
    # ----------------------------------------------------------------------
    # CLIENT-SIDE — CA-02 Pre-award advisory (11 rows)
    # ----------------------------------------------------------------------
    {"code": "cli-pre-strategic-advisory",   "name": "Strategic Project Advisory",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 25000,   "max_amount": 500000,
     "description": "Advisory on strategic needs, delivery options and initial viability.",
     "conditions": "Can be bundled with feasibility or business case. Do not repeat work already in a wider development mandate.",
     "display_order": 10},

    {"code": "cli-pre-feasibility",          "name": "Feasibility & Options Appraisal",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 25000,   "max_amount": 500000,
     "description": "Feasibility and options appraisal for a candidate project.",
     "conditions": "Can be bundled with business case. Credit earlier analysis where the same options are reassessed.",
     "display_order": 20},

    {"code": "cli-pre-business-case",        "name": "Business-Case Development",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 50000,   "max_amount": 1000000,
     "description": "Defines project outcomes, affordability, approvals, funding and financial model.",
     "conditions": "Can be bundled with funding-readiness support.",
     "display_order": 30},

    {"code": "cli-pre-funding-readiness",    "name": "Funding-Readiness Support",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 50000,   "max_amount": 750000,
     "description": "Prepares the project for funding conversations with lenders/sponsors.",
     "conditions": "Only permissible where non-regulated. Do not represent regulated financing unless properly authorised.",
     "display_order": 40},

    {"code": "cli-pre-procurement-strategy", "name": "Procurement Strategy",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 25000,   "max_amount": 500000,
     "description": "Route-to-market design: packaging, governance and evaluation methodology.",
     "conditions": "Separate strategic design from routine tender administration.",
     "display_order": 50},

    {"code": "cli-pre-market-engagement",    "name": "Market Engagement",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 15000,   "max_amount": 250000,
     "description": "Structured supplier outreach and market soundings.",
     "conditions": "Should be separate from routine tender administration.",
     "display_order": 60},

    {"code": "cli-pre-tender-docs",          "name": "Tender Documentation",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 25000,   "max_amount": 500000,
     "description": "Prepare tender / RFP / RFQ documents for the procurement process.",
     "conditions": "Usually bundled within a full procurement mandate.",
     "display_order": 70},

    {"code": "cli-pre-tender-admin",         "name": "Tender Administration",
     "side": "client", "category": "Pre-Award", "pricing_model": "percentage",
     "currency": "USD", "percentage": 0.5, "percentage_of": "contract_value",
     "description": "Managing the tender process incl. document control and correspondence.",
     "conditions": "Routine document control should not be charged twice. Typical range 0.25%-1.0%.",
     "display_order": 80},

    {"code": "cli-pre-evaluation-mgmt",      "name": "Evaluation Management",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 25000,   "max_amount": 300000,
     "description": "Managing tender evaluation and clarifications.",
     "conditions": "Maintain separation from bidder advisory or bid-writing support.",
     "display_order": 90},

    {"code": "cli-pre-probity",              "name": "Probity & Governance",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 10000,   "max_amount": 200000,
     "description": "Probity and governance oversight of the procurement/award process.",
     "conditions": "Independence and role separation must be demonstrable.",
     "display_order": 100},

    {"code": "cli-pre-award-support",        "name": "Award & Negotiation Support",
     "side": "client", "category": "Pre-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 25000,   "max_amount": 250000,
     "description": "Support during the award decision and contract finalisation.",
     "conditions": "Do not duplicate the evaluation report or routine award recommendation.",
     "display_order": 110},

    # ----------------------------------------------------------------------
    # CLIENT-SIDE — CA-02 Post-award delivery (11 rows)
    # ----------------------------------------------------------------------
    {"code": "cli-post-mobilisation",        "name": "Mobilisation Management",
     "side": "client", "category": "Post-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 50000,   "max_amount": 1000000,
     "description": "Establishing delivery governance, controls, systems and supplier interfaces post-award.",
     "conditions": "Do not repeat activities included in procurement close-out or programme-management mobilisation.",
     "display_order": 210},

    {"code": "cli-post-programme-mgmt",      "name": "Programme Management",
     "side": "client", "category": "Post-Award", "pricing_model": "percentage",
     "currency": "USD", "percentage": 2.0, "percentage_of": "programme_value",
     "description": "Strategic leadership and governance of related projects to achieve client outcomes.",
     "conditions": "Distinguish strategic programme leadership from project-level management. Typical 1.0%-3.0%.",
     "display_order": 220},

    {"code": "cli-post-project-mgmt",        "name": "Project Management",
     "side": "client", "category": "Post-Award", "pricing_model": "percentage",
     "currency": "USD", "percentage": 1.25, "percentage_of": "project_value",
     "description": "Coordinating delivery, performance and outcomes at project level.",
     "conditions": "Avoid parallel management fees where one integrated team performs both roles. Typical 0.5%-2.0%.",
     "display_order": 230},

    {"code": "cli-post-pmo",                 "name": "Programme Management Office (PMO)",
     "side": "client", "category": "Post-Award", "pricing_model": "annual",
     "currency": "USD", "amount": 500000,
     "description": "Controls, scheduling, reporting, governance support and information quality.",
     "conditions": "PMO should coordinate controls rather than duplicate project management. Typical $100k-$2m p.a.",
     "display_order": 240},

    {"code": "cli-post-contract-admin",      "name": "Contract Administration",
     "side": "client", "category": "Post-Award", "pricing_model": "annual",
     "currency": "USD", "amount": 250000,
     "description": "Administering contracts (cost, change, claims, payments).",
     "conditions": "Separate contractual notices/certification from commercial strategy. Typical $50k-$2m p.a.",
     "display_order": 250},

    {"code": "cli-post-commercial-mgmt",     "name": "Commercial Management",
     "side": "client", "category": "Post-Award", "pricing_model": "percentage",
     "currency": "USD", "percentage": 0.5, "percentage_of": "project_value",
     "description": "Contractual, financial, cost, change and commercial performance management.",
     "conditions": "Avoid overlap with contract administration and finance functions. Typical 0.25%-1.0%.",
     "display_order": 260},

    {"code": "cli-post-cost-change",         "name": "Cost & Change Control",
     "side": "client", "category": "Post-Award", "pricing_model": "annual",
     "currency": "USD", "amount": 300000,
     "description": "Cost planning, valuation and change register management.",
     "conditions": "Define ownership of cost reports, valuations and change registers. Typical $100k-$1m p.a.",
     "display_order": 270},

    {"code": "cli-post-risk-issue",          "name": "Risk & Issue Management",
     "side": "client", "category": "Post-Award", "pricing_model": "annual",
     "currency": "USD", "amount": 150000,
     "description": "Risk and issue management across the programme/project.",
     "conditions": "Use one authoritative risk register and reporting cycle. Typical $50k-$500k p.a.",
     "display_order": 280},

    {"code": "cli-post-governance-assurance","name": "Governance & Assurance",
     "side": "client", "category": "Post-Award", "pricing_model": "annual",
     "currency": "USD", "amount": 150000,
     "description": "Independent assurance on governance and delivery performance.",
     "conditions": "Assurance should evaluate, not reproduce, management reporting. Typical $50k-$500k p.a.",
     "display_order": 290},

    {"code": "cli-post-exec-portfolio-rep",  "name": "Executive & Portfolio Reporting",
     "side": "client", "category": "Post-Award", "pricing_model": "annual",
     "currency": "USD", "amount": 120000,
     "description": "Executive and portfolio-level reporting service.",
     "conditions": "Standard reports should be included unless premium analysis is commissioned. Typical $25k-$500k p.a.",
     "display_order": 300},

    {"code": "cli-post-closeout",            "name": "Close-out & Transition",
     "side": "client", "category": "Post-Award", "pricing_model": "range",
     "currency": "USD", "min_amount": 25000,   "max_amount": 500000,
     "description": "Handover, final accounts, benefits review and lessons learned.",
     "conditions": "Contract as a defined final phase with clear completion criteria.",
     "display_order": 310},

    # ----------------------------------------------------------------------
    # CLIENT-SIDE — EOP add-ons (7)
    # ----------------------------------------------------------------------
    {"code": "cli-eop-exec-dashboard",       "name": "Client Executive Dashboard",
     "side": "client", "category": "EOP", "pricing_model": "monthly",
     "currency": "USD", "amount": 2000,
     "description": "Portfolio-wide visibility and decision support dashboard.",
     "conditions": "Premium capability where it exceeds standard reporting. Included in Silver/Gold/Platinum.",
     "display_order": 410},

    {"code": "cli-eop-workspace",            "name": "Project Workspace",
     "side": "client", "category": "EOP", "pricing_model": "monthly",
     "currency": "USD", "amount": 500,
     "description": "Controlled environment for collaboration, tasks, records and workflow.",
     "conditions": "Core workspace included within delivery services. Included in all packages.",
     "display_order": 420},

    {"code": "cli-eop-governance-dashboard", "name": "Governance Dashboard",
     "side": "client", "category": "EOP", "pricing_model": "monthly",
     "currency": "USD", "amount": 1000,
     "description": "Real-time status of approvals, risks, issues and decisions.",
     "conditions": "Included in Silver and above or separately commissioned.",
     "display_order": 430},

    {"code": "cli-eop-doc-audit-trail",      "name": "Document & Audit Trail",
     "side": "client", "category": "EOP", "pricing_model": "monthly",
     "currency": "USD", "amount": 400,
     "description": "Authoritative repository plus complete decision history.",
     "conditions": "Standard governance functionality; no separate basic access fee.",
     "display_order": 440},

    {"code": "cli-eop-kpi-analytics",        "name": "KPI & Performance Analytics",
     "side": "client", "category": "EOP", "pricing_model": "monthly",
     "currency": "USD", "amount": 1500,
     "description": "Live indicators, trend analysis and exception management.",
     "conditions": "Premium capability. Included in Gold and Platinum.",
     "display_order": 450},

    {"code": "cli-eop-portfolio-analytics",  "name": "Portfolio Analytics",
     "side": "client", "category": "EOP", "pricing_model": "monthly",
     "currency": "USD", "amount": 3000,
     "description": "Cross-project insight and benchmarking.",
     "conditions": "Enterprise service for multi-project clients. Included in Platinum.",
     "display_order": 460},

    {"code": "cli-eop-ai-reporting",         "name": "AI-assisted Reporting",
     "side": "client", "category": "EOP", "pricing_model": "monthly",
     "currency": "USD", "amount": 2500,
     "description": "Drafting, synthesis and anomaly identification (human-reviewed).",
     "conditions": "Subject to AI governance controls.",
     "display_order": 470},

    # ----------------------------------------------------------------------
    # CLIENT-SIDE — Packages (4)
    # ----------------------------------------------------------------------
    {"code": "cli-pkg-bronze",               "name": "Bronze Package",
     "side": "client", "category": "Package", "pricing_model": "monthly",
     "currency": "USD", "amount": 3000, "package_tier": "Bronze",
     "description": "Basic advisory or procurement support, standard reporting, core EOP workspace.",
     "conditions": "For small or discrete projects.",
     "display_order": 510},

    {"code": "cli-pkg-silver",               "name": "Silver Package",
     "side": "client", "category": "Package", "pricing_model": "monthly",
     "currency": "USD", "amount": 8000, "package_tier": "Silver",
     "description": "Bronze plus programme management, PMO, governance reporting, executive dashboards.",
     "conditions": "For medium programmes.",
     "display_order": 520},

    {"code": "cli-pkg-gold",                 "name": "Gold Package",
     "side": "client", "category": "Package", "pricing_model": "monthly",
     "currency": "USD", "amount": 18000, "package_tier": "Gold",
     "description": "Silver plus commercial management, contract administration, enhanced reporting and analytics.",
     "conditions": "For major capital projects.",
     "display_order": 530},

    {"code": "cli-pkg-platinum",             "name": "Platinum Package",
     "side": "client", "category": "Package", "pricing_model": "monthly",
     "currency": "USD", "amount": 40000, "package_tier": "Platinum",
     "description": "Fully integrated programme delivery, portfolio governance, strategic advisory, advanced EOP.",
     "conditions": "For national programmes and mega-projects.",
     "display_order": 540},

    # ----------------------------------------------------------------------
    # SUPPLIER-SIDE — CA-03 Tender-stage
    # NOTE: Registration is DEACTIVATED by default per user's decision that the door fee stays free.
    # ----------------------------------------------------------------------
    {"code": "sup-tender-registration",      "name": "Supplier Registration Fee",
     "side": "supplier", "category": "Tender-Stage", "pricing_model": "fixed",
     "currency": "GBP", "amount": 500, "is_active": False,
     "description": "One-off supplier onboarding fee (identity, eligibility, platform access).",
     "conditions": "DISABLED by default per policy — network-effect play means registration stays free. Enable if pricing model changes.",
     "display_order": 610},

    {"code": "sup-tender-training",          "name": "Supplier Training (per delegate)",
     "side": "supplier", "category": "Tender-Stage", "pricing_model": "per_delegate",
     "currency": "GBP", "amount": 1500, "unit_label": "per delegate",
     "description": "Tender workshops and procurement education.",
     "conditions": "Optional unless critical for participation. Typical £500-£3,000.",
     "display_order": 620},

    {"code": "sup-tender-eop-cert",          "name": "EOP Certification",
     "side": "supplier", "category": "Tender-Stage", "pricing_model": "fixed",
     "currency": "GBP", "amount": 1000, "unit_label": "per organisation",
     "description": "Certified supplier programme for the Managed Operating Platform.",
     "conditions": "Optional but may be mandatory for specific roles. Typical £250-£2,000.",
     "display_order": 630},

    {"code": "sup-tender-integration",       "name": "Optional Integration (API)",
     "side": "supplier", "category": "Tender-Stage", "pricing_model": "range",
     "currency": "GBP", "min_amount": 2500, "max_amount": 25000,
     "description": "Optional inbound API/EOP integration setup.",
     "conditions": "Optional. Priced against complexity.",
     "display_order": 640},

    {"code": "sup-tender-project-setup",     "name": "Project-Specific Setup & Mobilisation",
     "side": "supplier", "category": "Award & Mobilisation", "pricing_model": "range",
     "currency": "GBP", "min_amount": 10000, "max_amount": 100000,
     "description": "Configuration/mobilisation of the supplier under an awarded contract (ERP integration up to £100k, EDI up to £50k).",
     "conditions": "For awarded contracts.",
     "display_order": 650},

    # ----------------------------------------------------------------------
    # SUPPLIER-SIDE — Post-award ongoing (13 monthly add-ons)
    # ----------------------------------------------------------------------
    {"code": "sup-post-premium-dashboards",  "name": "Premium Dashboards",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 600,
     "description": "Executive-grade dashboards over the supplier's own delivery data.",
     "conditions": "Typical £250-£1,000/month.",
     "display_order": 710},

    {"code": "sup-post-perf-analytics",      "name": "Performance Analytics",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 1500,
     "description": "Deep analytics on delivery performance and trends.",
     "conditions": "Typical £500-£2,500/month.",
     "display_order": 720},

    {"code": "sup-post-contract-archive",    "name": "Contract Archive",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 500,
     "description": "Long-term contract and evidence archive.",
     "conditions": "Typical £100-£1,000/month.",
     "display_order": 730},

    {"code": "sup-post-portfolio-reporting", "name": "Portfolio Reporting",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 1500,
     "description": "Cross-contract portfolio reporting for suppliers with multiple projects.",
     "conditions": "Typical £250-£3,000/month.",
     "display_order": 740},

    {"code": "sup-post-exec-reporting",      "name": "Executive Reporting",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 3000,
     "description": "Board-ready reporting pack for supplier executives.",
     "conditions": "Typical £1,000-£5,000/month.",
     "display_order": 750},

    {"code": "sup-post-additional-users",    "name": "Additional Users (seat)",
     "side": "supplier", "category": "Post-Award", "pricing_model": "per_user_monthly",
     "currency": "GBP", "amount": 60, "unit_label": "per user per month",
     "description": "Additional named user seats on the supplier workspace.",
     "conditions": "Typical £20-£100 per user per month.",
     "display_order": 760},

    {"code": "sup-post-delivery-perf",       "name": "Delivery Performance Reporting",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 800,
     "description": "Delivery performance reporting against contract KPIs.",
     "conditions": "Typical £250-£1,500/month.",
     "display_order": 770},

    {"code": "sup-post-quality-metrics",     "name": "Quality Metrics",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 800,
     "description": "Quality metric collection and reporting.",
     "conditions": "Typical £250-£1,500/month.",
     "display_order": 780},

    {"code": "sup-post-programme-compliance","name": "Programme Compliance",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 1500,
     "description": "Programme-level compliance tracking and reporting.",
     "conditions": "Typical £500-£2,500/month.",
     "display_order": 790},

    {"code": "sup-post-safety",              "name": "Safety Performance Reporting",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 800,
     "description": "HSE / safety performance reporting.",
     "conditions": "Typical £250-£1,500/month.",
     "display_order": 800},

    {"code": "sup-post-esg",                 "name": "ESG Reporting",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 1500,
     "description": "ESG/sustainability reporting pack.",
     "conditions": "Typical £250-£2,500/month.",
     "display_order": 810},

    {"code": "sup-post-payment-history",     "name": "Payment History Reporting",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 250,
     "description": "Payment history and cash-flow reporting.",
     "conditions": "Often included; premium £100-£500/month.",
     "display_order": 820},

    {"code": "sup-post-kpi-trend",           "name": "KPI Trend Analysis",
     "side": "supplier", "category": "Post-Award", "pricing_model": "monthly",
     "currency": "GBP", "amount": 1800,
     "description": "Long-horizon KPI trend analysis.",
     "conditions": "Typical £500-£3,000/month.",
     "display_order": 830},

    # ----------------------------------------------------------------------
    # SUPPLIER-SIDE — Supplier Success subscription tiers (3)
    # ----------------------------------------------------------------------
    {"code": "sup-success-sme",              "name": "Supplier Success — SME",
     "side": "supplier", "category": "Supplier Success", "pricing_model": "monthly",
     "currency": "GBP", "amount": 750, "package_tier": "SME",
     "description": "Benchmarking, portfolio insight and advisory for SMEs.",
     "conditions": "Typical £500-£1,000/month.",
     "display_order": 910},

    {"code": "sup-success-mid",              "name": "Supplier Success — Mid-market",
     "side": "supplier", "category": "Supplier Success", "pricing_model": "monthly",
     "currency": "GBP", "amount": 2000, "package_tier": "Mid",
     "description": "Supplier Success programme for mid-market suppliers.",
     "conditions": "Typical £1,000-£3,000/month.",
     "display_order": 920},

    {"code": "sup-success-tier1",            "name": "Supplier Success — Tier 1 / Strategic",
     "side": "supplier", "category": "Supplier Success", "pricing_model": "monthly",
     "currency": "GBP", "amount": 6000, "package_tier": "Tier1",
     "description": "Strategic supplier programme for Tier-1 partners.",
     "conditions": "Typical £3,000-£10,000/month.",
     "display_order": 930},

    # ----------------------------------------------------------------------
    # BOTH SIDES — Cost recovery
    # ----------------------------------------------------------------------
    {"code": "cost-recovery",                "name": "Cost-recovery line item",
     "side": "both", "category": "Cost Recovery", "pricing_model": "cost_recovery",
     "currency": "USD",
     "description": "Pass-through / cost-recovery invoice for services required to protect procurement integrity or comply with a client mandate.",
     "conditions": "Only for services not part of a bundle or otherwise funded.",
     "display_order": 990},
]
