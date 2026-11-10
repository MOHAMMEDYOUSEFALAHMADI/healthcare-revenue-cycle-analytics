"""Payers, service lines, denial reasons and benchmark targets. Generic names only."""

# Generic payer names; none represents a real insurer
PAYERS = {
    "Insurer A (Commercial)": {"share": 0.28, "denial": 0.09, "pay_days": 38, "rate": 1.00},
    "Insurer B (Commercial)": {"share": 0.20, "denial": 0.12, "pay_days": 45, "rate": 0.95},
    "Insurer C (Corporate)":  {"share": 0.14, "denial": 0.07, "pay_days": 32, "rate": 1.05},
    "Government Programme":   {"share": 0.22, "denial": 0.05, "pay_days": 60, "rate": 0.80},
    "Third-Party Admin (TPA)": {"share": 0.09, "denial": 0.15, "pay_days": 52, "rate": 0.90},
    "Self-pay":               {"share": 0.07, "denial": 0.00, "pay_days": 20, "rate": 0.70},
}

SERVICE_LINES = {
    # base charge SAR, direct cost ratio, volume weight
    "Emergency":        {"charge": 1800,  "cost_ratio": 0.62, "w": 0.24},
    "Outpatient Clinics": {"charge": 650, "cost_ratio": 0.48, "w": 0.34},
    "Inpatient Medical": {"charge": 14000, "cost_ratio": 0.71, "w": 0.10},
    "Surgery":          {"charge": 26000, "cost_ratio": 0.66, "w": 0.07},
    "Radiology":        {"charge": 1200,  "cost_ratio": 0.45, "w": 0.13},
    "Laboratory":       {"charge": 380,   "cost_ratio": 0.38, "w": 0.12},
}

DENIAL_REASONS = {
    "Missing / invalid prior authorisation": 0.24,
    "Eligibility / coverage not verified": 0.17,
    "Medical necessity not supported": 0.15,
    "Coding error (ICD / CPT mismatch)": 0.14,
    "Duplicate claim": 0.08,
    "Late submission (timely filing)": 0.07,
    "Missing documentation": 0.10,
    "Policy / benefit exclusion": 0.05,
}
PREVENTABLE = {"Missing / invalid prior authorisation", "Eligibility / coverage not verified",
               "Coding error (ICD / CPT mismatch)", "Duplicate claim", "Late submission (timely filing)",
               "Missing documentation"}

TARGETS = {
    "clean_claim_rate": 95.0,      # % claims accepted first pass
    "denial_rate": 5.0,            # % claims denied
    "days_in_ar": 45.0,            # days
    "net_collection_rate": 96.0,   # % of collectible collected
}
