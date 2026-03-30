
from pathlib import Path

APP_NAME = "AppraisalOS Next"
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "appraisalos_next.db"
STORAGE_DIR = BASE_DIR / "storage"

DEFAULT_SECTIONS = [
    "Subject",
    "Neighborhood",
    "Site",
    "Improvements",
    "Sales Comparison",
    "Cost Approach",
    "Reconciliation",
    "Scope of Work",
]

QC_CHECKLIST_ITEMS = [
    ("photos_complete", "Photos complete"),
    ("sections_complete", "All major sections saved"),
    ("comps_supported", "Comp selection documented"),
    ("adjustments_supported", "Adjustments supported"),
    ("scope_included", "USPAP scope of work included"),
    ("flood_verified", "Flood zone / map verified"),
]

ORDER_STATUSES = [
    "Pending",
    "Scheduled",
    "Inspected",
    "In Progress",
    "Review",
    "Ready for Delivery",
    "Completed",
    "On Hold",
    "Cancelled",
]

PROPERTY_TYPES = [
    "Single Family",
    "Condo",
    "Townhouse",
    "2-4 Family",
    "5+ Units",
    "Manufactured",
]

APPRAISAL_TYPES = ["1004", "1025", "1073", "2055", "1004D", "Other"]
FORM_TYPES = ["URAR", "FNMA", "FHLMC", "VA", "FHA", "Other"]

FOUNDATION_TYPES = ["", "Full Basement", "Partial Basement", "Crawl Space", "Slab", "Other"]
GARAGE_TYPES = [
    "None",
    "1-Car Attached",
    "2-Car Attached",
    "3-Car Attached",
    "1-Car Detached",
    "2-Car Detached",
    "Carport",
]
CONDITION_RATINGS = ["", "C1", "C2", "C3", "C4", "C5", "C6"]
QUALITY_RATINGS = ["", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]

DEFAULT_AI_MODEL = "gpt-5.4-mini"

SECTION_GUIDANCE = {
    "Subject": "Write a factual subject section using only provided data. Leave bracketed placeholders when facts are missing.",
    "Neighborhood": "Describe the neighborhood only from supplied facts and field notes. Do not invent streets, schools, or landmarks.",
    "Site": "Describe site size, zoning, utilities, flood data, and site characteristics only from supplied facts. Mark missing items clearly.",
    "Improvements": "Describe improvements, room counts, materials, condition, quality, basement, HVAC, and garage using only supplied facts.",
    "Sales Comparison": "Do not generate fake comparable sales. Write a framework that the appraiser can complete with verified comp data and adjustments.",
    "Cost Approach": "Write a framework only. Do not invent site value, cost rates, or depreciation.",
    "Reconciliation": "Write a framework that explains how the appraiser should reconcile approaches and state a final value with placeholders where needed.",
    "Scope of Work": "Write a scope-of-work and limiting-conditions draft using supplied engagement context only, with placeholders where facts are missing.",
}

COMPANY_SETTINGS_DEFAULTS = {
    "company_name": "A-Tech Appraisal Co., LLC",
    "company_address": "Warwick, RI",
    "company_phone": "",
    "ai_model": DEFAULT_AI_MODEL,
    "default_assignee": "",
}
