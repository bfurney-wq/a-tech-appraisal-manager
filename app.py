import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import xml.etree.ElementTree as ET
from PIL import Image
import json
import base64
import io
import math
import requests
import fitz  # PyMuPDF - for converting PDF pages to images

# ====================== CONFIG ======================
st.set_page_config(page_title="AppraisalOS", layout="wide", page_icon="🏠")

# ====================== CUSTOM CSS - PREMIUM DESIGN SYSTEM ======================
st.markdown("""
<style>
/* Premium design system with proper Streamlit selectors */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

#MainMenu {display: none;}
footer {display: none;}
header[data-testid="stHeader"] {
    background: rgba(255,255,255,0.8);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 0.5px solid rgba(0,0,0,0.1);
}

/* Base */
.main {
    background-color: #f5f5f7;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.block-container {
    max-width: 1200px;
    padding: 2rem 1rem;
}

/* Hero banner - Premium gradient */
.hero-banner {
    background: linear-gradient(135deg, #1d1d1f 0%, #2d2d30 50%, #1d1d1f 100%);
    padding: 2.5rem 3rem;
    border-radius: 18px;
    margin-bottom: 2rem;
    color: white;
    position: relative;
    overflow: hidden;
}
.hero-banner::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(0,122,255,0.15) 0%, transparent 70%);
}
.hero-banner h1 {
    color: white !important;
    font-size: 2rem;
    margin: 0;
    font-weight: 600;
    letter-spacing: -0.02em;
}
.hero-banner p {
    color: rgba(255,255,255,0.7);
    margin: 0.4rem 0 0 0;
    font-size: 0.95rem;
    font-weight: 300;
}

/* Metric cards - Glass morphism style */
.metric-card {
    background: white;
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
    border: 0.5px solid rgba(0,0,0,0.06);
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}
.metric-value {
    font-size: 2.2rem;
    font-weight: 600;
    color: #1d1d1f;
    margin: 0.5rem 0;
    letter-spacing: -0.03em;
}
.metric-label {
    font-size: 0.75rem;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
}

/* Feature cards */
.feature-card {
    background: white;
    border-radius: 14px;
    padding: 1.5rem;
    border: 0.5px solid rgba(0,0,0,0.06);
    box-shadow: 0 1px 8px rgba(0,0,0,0.03);
    margin-bottom: 0.75rem;
    border-left: 3px solid #0071E3;
    transition: all 0.2s ease;
}
.feature-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.feature-card h4 {
    margin: 0 0 0.5rem 0;
    color: #1d1d1f;
    font-size: 0.95rem;
}
.feature-card p {
    margin: 0;
    color: #555;
    font-size: 0.85rem;
    line-height: 1.4;
}

/* Tabs - Apple segmented control style */
.stTabs [data-baseweb="tab-list"] {
    background: #f5f5f7;
    border-radius: 10px;
    padding: 3px;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-weight: 500;
    font-size: 0.85rem;
    color: #1d1d1f;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #1d1d1f !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    border: none;
}
.stTabs [data-baseweb="tab-highlight"] {display: none;}
.stTabs [data-baseweb="tab-border"] {display: none;}

/* Typography */
h1, h2, h3 {
    color: #1d1d1f;
    letter-spacing: -0.02em;
    font-weight: 600;
}
h1 {font-size: 1.8rem;}
h2 {font-size: 1.4rem;}
h3 {font-size: 1.15rem;}

/* Buttons - Apple style */
.stButton > button {
    border-radius: 10px;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.5rem 1.25rem;
    border: none;
    transition: all 0.2s ease;
}
.stButton > button[kind="primary"] {
    background: #0071E3 !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background: #0066d6 !important;
}
.stButton > button[kind="secondary"] {
    background: #f5f5f7 !important;
    color: #1d1d1f !important;
    border: 0.5px solid rgba(0,0,0,0.1) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #e8e8ed !important;
}

/* Form inputs - proper Streamlit selectors */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    border-radius: 10px !important;
    border: 1px solid #d2d2d7 !important;
    font-size: 0.9rem;
    padding: 0.5rem 0.75rem !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #0071E3 !important;
    box-shadow: 0 0 0 3px rgba(0,122,255,0.15) !important;
}

/* Selectbox - using data-testid selectors for Streamlit compatibility */
[data-testid="stSelectbox"] > div > div {
    border-radius: 10px !important;
    border: 1px solid #d2d2d7 !important;
}
[data-testid="stSelectbox"] input {
    font-size: 0.9rem !important;
    padding: 0.5rem 0.75rem !important;
}
[data-testid="stSelectbox"] input:focus {
    border-color: #0071E3 !important;
    box-shadow: 0 0 0 3px rgba(0,122,255,0.15) !important;
}

/* Ensure selectbox text is readable */
[role="listbox"] {
    border-radius: 10px !important;
}
[role="option"] {
    padding: 0.5rem 0.75rem !important;
    font-size: 0.9rem !important;
}

/* Dataframes */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    border: 0.5px solid rgba(0,0,0,0.06);
}

/* Expanders */
.streamlit-expanderHeader {
    font-weight: 500;
    font-size: 0.95rem;
    color: #1d1d1f;
    background: #f5f5f7;
    border-radius: 10px;
}

/* Dividers */
hr {border-color: rgba(0,0,0,0.06) !important;}

/* Success/Error/Warning messages */
.stAlert {border-radius: 12px;}

/* Pricing cards */
.pricing-card {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    text-align: center;
    transition: all 0.3s ease;
}
.pricing-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.pricing-card.featured {
    border: 2px solid #0071E3;
    transform: scale(1.02);
}
.pricing-card h3 {
    margin: 0 0 0.5rem 0;
    font-size: 1.3rem;
}
.pricing-price {
    font-size: 2.5rem;
    font-weight: 700;
    color: #1d1d1f;
    margin: 1rem 0;
}
.pricing-price-period {
    font-size: 0.9rem;
    color: #86868b;
}
.pricing-features {
    text-align: left;
    margin: 1.5rem 0;
    min-height: 200px;
}
.pricing-features li {
    padding: 0.5rem 0;
    color: #555;
    font-size: 0.9rem;
    list-style: none;
    position: relative;
    padding-left: 1.5rem;
}
.pricing-features li:before {
    content: "✓";
    position: absolute;
    left: 0;
    color: #0071E3;
    font-weight: bold;
}
.pricing-features li.locked {
    color: #ccc;
}
.pricing-features li.locked:before {
    content: "🔒";
    color: #ccc;
}

/* Login form styling */
.login-container {
    max-width: 400px;
    margin: 0 auto;
    background: white;
    padding: 2rem;
    border-radius: 16px;
    border: 0.5px solid rgba(0,0,0,0.06);
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* Lock icon for features */
.feature-locked {
    color: #ccc;
    opacity: 0.6;
}
.lock-badge {
    display: inline-block;
    background: #f5f5f7;
    color: #1d1d1f;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    margin-left: 0.5rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ====================== SESSION STATE INIT ======================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_tier" not in st.session_state:
    st.session_state.user_tier = "starter"
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "show_form" not in st.session_state:
    st.session_state.show_form = False
if "edit_order_id" not in st.session_state:
    st.session_state.edit_order_id = None
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Dashboard"
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = {}
if "extracted_ps_data" not in st.session_state:
    st.session_state.extracted_ps_data = {}
if "advisor_messages" not in st.session_state:
    st.session_state.advisor_messages = []

# ====================== DATABASE ======================
DB_FILE = "a_tech_appraisals.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            client_name TEXT,
            client_email TEXT,
            client_phone TEXT,
            lender_name TEXT,
            loan_number TEXT,
            subject_address TEXT,
            city TEXT,
            state TEXT DEFAULT 'RI',
            zip_code TEXT,
            property_type TEXT,
            appraisal_type TEXT DEFAULT '1004',
            form_type TEXT DEFAULT 'URAR',
            assigned_appraiser TEXT,
            fee REAL,
            due_date TEXT,
            inspection_date TEXT,
            status TEXT DEFAULT 'Pending',
            field_notes TEXT,
            value_opinion TEXT,
            ai_narrative TEXT,
            created_at TEXT,
            updated_at TEXT,
            photos TEXT,
            property_details TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            action TEXT,
            details TEXT,
            timestamp TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            password_hash TEXT,
            organization_id INTEGER,
            role TEXT DEFAULT 'appraiser',
            tier TEXT DEFAULT 'starter',
            created_at TEXT,
            last_login TEXT
        );

        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner_id INTEGER,
            subscription_tier TEXT DEFAULT 'starter',
            subscription_status TEXT DEFAULT 'trial',
            stripe_customer_id TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS report_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            section_name TEXT,
            ai_draft TEXT,
            human_edited TEXT,
            is_reviewed INTEGER DEFAULT 0,
            reviewer_notes TEXT,
            evidence_sources TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS review_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            reviewer_name TEXT,
            item_type TEXT,
            description TEXT,
            status TEXT DEFAULT 'open',
            response TEXT,
            created_at TEXT,
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS ai_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            run_type TEXT,
            section_name TEXT,
            prompt_summary TEXT,
            input_data TEXT,
            output_text TEXT,
            model TEXT,
            tokens_used INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            old_status TEXT,
            new_status TEXT,
            changed_by TEXT,
            reason TEXT,
            created_at TEXT
        );
    ''')
    # Add property_details column if missing (existing DBs)
    try:
        conn.execute("ALTER TABLE orders ADD COLUMN property_details TEXT")
    except:
        pass
    conn.commit()
    conn.close()

init_db()

def get_prop(order_data, key, default=""):
    """Get a property detail from the order's property_details JSON."""
    pd_str = order_data.get("property_details", "") or "{}"
    try:
        pd_dict = json.loads(pd_str)
    except:
        pd_dict = {}
    return pd_dict.get(key, default)

def log_activity(order_id, action, details=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO activity_log (order_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
        (order_id, action, details, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ====================== EMAIL ======================
def send_email(to_email, subject, body, settings):
    """Send email via Gmail SMTP."""
    gmail_user = settings.get("gmail_user", "")
    gmail_app_password = settings.get("gmail_app_password", "")

    if not gmail_user or not gmail_app_password:
        return False, "Gmail not configured. Go to Settings to set up."

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, to_email, msg.as_string())
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

# ====================== AI NARRATIVE ======================
def generate_narrative(order_data, api_key):
    """Generate appraisal narrative using OpenAI GPT."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # Parse property details
        p = {}
        pd_str = order_data.get("property_details", "") or "{}"
        try:
            p = json.loads(pd_str)
        except:
            p = {}

        prop_info = f"""- Year Built: {p.get('year_built', 'Unknown')}
- Stories: {p.get('stories', 'Unknown')}
- Design/Style: {p.get('design_style', 'Unknown')}
- Exterior: {p.get('exterior_desc', 'Unknown')}
- GLA: {p.get('gla_sqft', 'Unknown')} sq ft
- Total Rooms: {p.get('total_rooms', 'Unknown')}, Bedrooms: {p.get('bedrooms', 'Unknown')}, Bathrooms: {p.get('bathrooms', 'Unknown')}
- Foundation: {p.get('foundation_type', 'Unknown')}
- Basement: {p.get('basement_sqft', 'Unknown')} sq ft, {p.get('basement_finished_pct', 'Unknown')}% finished
- Heating: {p.get('heating_type', 'Unknown')}, Cooling: {p.get('cooling_type', 'Unknown')}
- Garage: {p.get('garage_type', 'None')}
- Lot: {p.get('lot_dimensions', 'Unknown')} / {p.get('lot_area', 'Unknown')}
- Zoning: {p.get('zoning', 'Unknown')}
- Condition: {p.get('condition_rating', 'Unknown')}, Quality: {p.get('quality_rating', 'Unknown')}
- Neighborhood: {p.get('neighborhood_name', 'Unknown')}
- County: {p.get('county', 'Unknown')}
- Flood Zone: {p.get('flood_zone', 'Unknown')}, Flood Map #: {p.get('flood_map_id', 'Unknown')}
- Taxes: ${p.get('tax_amount', 'Unknown')} ({p.get('tax_year', 'Unknown')})
- Assessor Parcel #: {p.get('assessor_parcel', 'Unknown')}
- Legal Description: {p.get('legal_desc', 'Unknown')}"""

        prompt = f"""Write ONLY from the supplied property data and appraiser field notes below. DO NOT invent facts.

Property Details:
- Address: {order_data['subject_address']}, {order_data.get('city', '')}, {order_data.get('state', 'RI')} {order_data.get('zip_code', '')}
- Property Type: {order_data['property_type']}
{prop_info}
- Appraiser Field Notes: {order_data.get('field_notes', 'None provided')}
- Preliminary Value Opinion: {order_data.get('value_opinion', 'TBD')}

Write ALL of the following sections. For any data not supplied above, write '[NOT PROVIDED — appraiser to complete]':

1. SUBJECT SECTION
   - Describe ONLY the property characteristics provided above
   - For legal description, census tract, owner info, sale history: use placeholders if not supplied
   - State: "[NOT PROVIDED — appraiser to complete]" for any missing details

2. NEIGHBORHOOD ANALYSIS
   - Describe ONLY characteristics supported by supplied data
   - For schools, amenities, boundaries: write "[NOT PROVIDED — appraiser to complete]" if not in field notes
   - Do NOT invent street names or landmarks

3. SITE DESCRIPTION
   - Lot dimensions, area, utilities, zoning: use only supplied data
   - For drainage, easements, environmental conditions: mark as [NOT PROVIDED] if missing
   - FEMA flood zone: {p.get('flood_zone', '[NOT PROVIDED]')}, Flood Map ID: {p.get('flood_map_id', '[NOT PROVIDED]')}

4. IMPROVEMENT DESCRIPTION
   - Room-by-room: use only the counts and descriptions provided
   - Mechanical systems, condition ratings: use supplied data only
   - For details not provided: "[NOT PROVIDED — appraiser field inspection to verify]"

5. SALES COMPARISON APPROACH FRAMEWORK
   - DO NOT GENERATE fictional comparable sales
   - Instead, provide a framework for the appraiser to complete:
     "The following three comparable sales were selected based on [search parameters]:
     Comparable 1: [Address], Sale Price: [Price], Sale Date: [Date], GLA: [sqft], Lot: [dimensions], Beds: [#], Baths: [#], Year Built: [year], Condition: [C-rating], Quality: [Q-rating]
     [Appraiser to enter adjustment details and reasoning]

     Comparable 2: [Address], Sale Price: [Price], Sale Date: [Date], GLA: [sqft], Lot: [dimensions], Beds: [#], Baths: [#], Year Built: [year], Condition: [C-rating], Quality: [Q-rating]
     [Appraiser to enter adjustment details and reasoning]

     Comparable 3: [Address], Sale Price: [Price], Sale Date: [Date], GLA: [sqft], Lot: [dimensions], Beds: [#], Baths: [#], Year Built: [year], Condition: [C-rating], Quality: [Q-rating]
     [Appraiser to enter adjustment details and reasoning]

     Indicated Value (Sales Comparison): [Appraiser to calculate]"

6. COST APPROACH FRAMEWORK
   - Provide calculation structure using supplied data
   - Site value estimate: [Appraiser to complete with market support]
   - Cost new (cost per sq ft): [Appraiser to enter with source citation]
   - Depreciation rates: [Appraiser to calculate and document]
   - Indicated Value (Cost): [Appraiser to calculate]

7. RECONCILIATION
   - Weights to each approach and rationale: [Appraiser to complete]
   - Final opinion of value: [Appraiser to enter with effective date]
   - Exposure and marketing time: [Appraiser to estimate]

8. ADDENDUM / SCOPE OF WORK
   - Describe inspection performed, data sources reviewed, methods used
   - Include standard USPAP certifications and limiting conditions
   - Reference intended use and intended users as specified in engagement

Every factual claim must be traceable to the supplied data. NEVER invent street names, landmarks, schools, comp sales, owner names, or sale history.
Use UAD abbreviations where appropriate (C1-C6, Q1-Q6, N;Res;, etc.).
Keep professional appraisal language throughout."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional appraisal report writing assistant. You ONLY write from the data provided. If data is missing, write '[NOT PROVIDED — appraiser to complete]'. NEVER invent street names, landmarks, schools, comp sales, owners, or sale history. NEVER fabricate any factual claims. Your role is to create professional narrative frameworks that the appraiser will complete with verified data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8000,
            temperature=0.2
        )
        return response.choices[0].message.content, None
    except ImportError:
        return None, "OpenAI package not installed. Run: pip install openai"
    except Exception as e:
        return None, str(e)

def generate_section(order_data, api_key, section_name):
    """Generate a single section of the appraisal narrative using OpenAI GPT."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        p = {}
        pd_str = order_data.get("property_details", "") or "{}"
        try:
            p = json.loads(pd_str)
        except:
            p = {}

        section_prompts = {
            "Neighborhood": f"""Write ONLY from the supplied data below. For any missing information, use [NOT PROVIDED — appraiser to complete].

Property: {order_data.get('subject_address', '')}, {order_data.get('city', '')}, {order_data.get('state', 'RI')}
Appraiser Field Notes: {order_data.get('field_notes', '[NOT PROVIDED]')}

Write a Neighborhood Analysis section (2-3 paragraphs) describing ONLY what is provided above. For boundaries, amenities, schools, and market factors not in the data, write [NOT PROVIDED — appraiser to complete]. Do NOT invent street names, landmark names, or schools.""",

            "Site": f"""Write ONLY from the supplied data below. For any missing information, use [NOT PROVIDED — appraiser to complete].

Lot dimensions: {p.get('lot_dimensions', '[NOT PROVIDED]')}
Lot area: {p.get('lot_area', '[NOT PROVIDED]')} sq ft
Utilities: {p.get('utilities', '[NOT PROVIDED]')}
Zoning: {p.get('zoning', '[NOT PROVIDED]')}
Flood Zone: {p.get('flood_zone', '[NOT PROVIDED]')}, Map ID: {p.get('flood_map_id', '[NOT PROVIDED]')}
Appraiser Field Notes: {order_data.get('field_notes', '[NOT PROVIDED]')}

Write a Site Description section (2 paragraphs) using ONLY the supplied data. For drainage, easements, environmental issues, and other details not provided, write [NOT PROVIDED — appraiser field inspection to verify].""",

            "Improvements": f"""Write ONLY from the supplied data below. For any missing information, use [NOT PROVIDED — appraiser to complete].

Year Built: {p.get('year_built', '[NOT PROVIDED]')}
Foundation: {p.get('foundation_type', '[NOT PROVIDED]')}
Exterior: {p.get('exterior_desc', '[NOT PROVIDED]')}
Roof: {p.get('roof_type', '[NOT PROVIDED]')}
GLA: {p.get('gla_sqft', '[NOT PROVIDED]')} sq ft
Bedrooms: {p.get('bedrooms', '[NOT PROVIDED]')}, Bathrooms: {p.get('bathrooms', '[NOT PROVIDED]')}
Basement: {p.get('basement_sqft', '[NOT PROVIDED]')} sq ft, {p.get('basement_finished_pct', '[NOT PROVIDED]')}% finished
HVAC: {p.get('heating_type', '[NOT PROVIDED]')} / {p.get('cooling_type', '[NOT PROVIDED]')}
Garage: {p.get('garage_type', 'None')}
Condition: {p.get('condition_rating', '[NOT PROVIDED]')}, Quality: {p.get('quality_rating', '[NOT PROVIDED]')}
Appraiser Field Notes: {order_data.get('field_notes', '[NOT PROVIDED]')}

Write an Improvements/Interior description (3 paragraphs) using ONLY the data above. For room details, mechanical details, interior finishes, and exterior features not provided, mark as [NOT PROVIDED — appraiser to verify]. Use UAD condition (C1-C6) and quality (Q1-Q6) ratings.""",

            "Sales Comparison": f"""Create a framework for a Sales Comparison Approach section using facts-only principles.

Property: {order_data.get('subject_address', '')}, {order_data.get('city', '')}, {order_data.get('state', 'RI')}
GLA: {p.get('gla_sqft', '[NOT PROVIDED]')} sq ft, Beds: {p.get('bedrooms', '[NOT PROVIDED]')}, Baths: {p.get('bathrooms', '[NOT PROVIDED]')}

Write the framework for a Sales Comparison section that includes:
- Search parameters used (radius, date range, property type): [APPRAISER TO SPECIFY]
- Comparable 1: [Address], Sale Price: [Price], Sale Date: [Date], GLA: [sqft], Lots: [dimensions], Beds: [#], Baths: [#], Year Built: [year], Condition: [C-rating], Quality: [Q-rating]
  [Appraiser to enter adjustment reasoning]
- Comparable 2: [Address], Sale Price: [Price], Sale Date: [Date], GLA: [sqft], Lot: [dimensions], Beds: [#], Baths: [#], Year Built: [year], Condition: [C-rating], Quality: [Q-rating]
  [Appraiser to enter adjustment reasoning]
- Comparable 3: [Address], Sale Price: [Price], Sale Date: [Date], GLA: [sqft], Lot: [dimensions], Beds: [#], Baths: [#], Year Built: [year], Condition: [C-rating], Quality: [Q-rating]
  [Appraiser to enter adjustment reasoning]
- Indicated Value (Sales Comparison): [Appraiser to calculate]

Emphasize that this is a framework for the appraiser to complete with verified market data.""",

            "Cost Approach": f"""Create a Cost Approach framework using the supplied data.

GLA: {p.get('gla_sqft', '[NOT PROVIDED]')} sq ft
Year Built: {p.get('year_built', '[NOT PROVIDED]')}
Condition: {p.get('condition_rating', '[NOT PROVIDED]')}
Quality: {p.get('quality_rating', '[NOT PROVIDED]')}

Write a Cost Approach framework (2 paragraphs) that includes:
- Site value estimate: [Appraiser to complete with market support]
- Cost new (cost per sq ft): [Appraiser to enter with Marshall & Swift or similar source]
- Physical depreciation rate: [Appraiser to calculate based on effective age and economic life]
- Functional or external depreciation: [Appraiser to assess if applicable]
- Indicated Value (Cost): [Appraiser to calculate]

Make clear this is for the appraiser to complete with market data and professional judgment.""",

            "Reconciliation": f"""Create a Reconciliation section framework.

Write a Reconciliation section (2 paragraphs) that includes:
- Weight given to Sales Comparison Approach: [Appraiser to determine] %
  Rationale: [Appraiser to explain]
- Weight given to Cost Approach: [Appraiser to determine] %
  Rationale: [Appraiser to explain]
- Final Opinion of Value: $[Appraiser to enter] (Effective Date: [Appraiser to enter])
- Exposure Time estimate: [Appraiser to estimate based on market]
- Marketing Time estimate: [Appraiser to estimate]
- Confidence in value conclusion: [Appraiser to assess]

Note: This framework should be completed by the appraiser with professional judgment and market analysis."""
        }

        prompt = section_prompts.get(section_name, "Generate a professional appraisal section based on the property data provided.")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional appraisal report writing assistant. You ONLY write from the data provided. For missing data, use [NOT PROVIDED — appraiser to complete]. NEVER invent facts. Your role is to create professional frameworks that the appraiser will complete with verified data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.2
        )
        return response.choices[0].message.content, None
    except ImportError:
        return None, "OpenAI package not installed. Run: pip install openai"
    except Exception as e:
        return None, str(e)

def generate_report_data(order_data, api_key):
    """Generate structured report data (comps, adjustments, comments) as JSON for XML export."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        p = {}
        pd_str = order_data.get("property_details", "") or "{}"
        try:
            p = json.loads(pd_str)
        except:
            p = {}

        city = order_data.get('city', '')
        state = order_data.get('state', 'RI')
        zipcode = order_data.get('zip_code', '')

        prompt = f"""You are a licensed certified residential appraiser with 20+ years of experience
in {city}, {state}. Generate ONLY the URAR PAGE 1 data as JSON. This is for the Subject,
Neighborhood, and Site sections ONLY. Do NOT make up comparable sales, adjustments, or values.

ONLY use data that is provided below or that you can reasonably know about the area (like
neighborhood character, typical utilities, zoning descriptions, etc.).
If you don't have specific data for a field, leave it as an empty string "".
DO NOT FABRICATE specific numbers, addresses, or sale prices.

SUBJECT PROPERTY:
- Address: {order_data['subject_address']}, {city}, {state} {zipcode}
- Type: {order_data['property_type']}
- Year Built: {p.get('year_built', '')}, Stories: {p.get('stories', '')}, Style: {p.get('design_style', '')}
- Exterior: {p.get('exterior_desc', '')}
- GLA: {p.get('gla_sqft', '')} sqft, Rooms: {p.get('total_rooms', '')}, Beds: {p.get('bedrooms', '')}, Baths: {p.get('bathrooms', '')}
- Foundation: {p.get('foundation_type', '')}, Basement: {p.get('basement_sqft', '')} sqft, {p.get('basement_finished_pct', '')}% finished
- Heating: {p.get('heating_type', '')}, Cooling: {p.get('cooling_type', '')}
- Lot: {p.get('lot_dimensions', '')} / {p.get('lot_area', '')} sqft, Zoning: {p.get('zoning', '')}
- Garage: {p.get('garage_type', '')}
- Condition: {p.get('condition_rating', '')}, Quality: {p.get('quality_rating', '')}
- Neighborhood: {p.get('neighborhood_name', '')}
- County: {p.get('county', '')}
- Flood Zone: {p.get('flood_zone', '')}, Map #: {p.get('flood_map_id', '')}
- Tax: ${p.get('tax_amount', '')} ({p.get('tax_year', '')}), Parcel: {p.get('assessor_parcel', '')}
- Legal Desc: {p.get('legal_desc', '')}
- Value Opinion: {order_data.get('value_opinion', '')}
- Field Notes: {order_data.get('field_notes', '')}

RULES:
1. Only fill fields you have actual data for or general area knowledge about
2. Leave unknown fields as empty strings - DO NOT GUESS
3. Neighborhood description should reflect your general knowledge of {city}, {state} areas
4. All comments should be based on the provided subject data only
5. DO NOT generate comps, adjustments, or values - the appraiser will add those manually
6. All monetary values as strings without $ signs or commas

Return ONLY valid JSON (no markdown, no code fences) with this EXACT structure:
{{
  "comps": [],
  "neighborhood": {{
    "name": "{p.get('neighborhood_name', '')}",
    "boundaries": "",
    "description": "3+ sentences describing the general character of this area in {city}, {state} based on your knowledge. Housing types, age of homes, appeal, proximity to amenities.",
    "built_up": "",
    "growth_rate": "",
    "property_values": "",
    "demand": "",
    "supply": "",
    "marketing_time": ""
  }},
  "site": {{
    "lot_dimensions": "{p.get('lot_dimensions', '')}",
    "lot_area": "{p.get('lot_area', '')}",
    "shape": "",
    "topography": "",
    "drainage": "",
    "utilities": "Public water, Public sewer, Public gas, Public electric",
    "street": "",
    "flood_zone": "{p.get('flood_zone', '')}",
    "flood_map_id": "{p.get('flood_map_id', '')}",
    "zoning": "{p.get('zoning', '')}"
  }}
}}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a licensed appraiser generating structured data. Return ONLY valid JSON. Do NOT include markdown or explanations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        # Remove markdown code fences if present
        if result.startswith("```"):
            result = result.split("```")[1].strip()
            if result.startswith("json"):
                result = result[4:].strip()

        data = json.loads(result)
        return data, None
    except ImportError:
        return None, "OpenAI package not installed. Run: pip install openai"
    except Exception as e:
        return None, str(e)

def extract_document_data(uploaded_file, api_key, doc_type="engagement"):
    """Extract data from engagement letters, order forms, or P&S agreements using GPT-4o vision."""
    if not api_key:
        return {}, "OpenAI API key not configured"
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    b64_data = base64.b64encode(file_bytes).decode('utf-8')
    ext = uploaded_file.name.lower().split('.')[-1]
    media_map = {'pdf': 'application/pdf', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'webp': 'image/webp'}
    media_type = media_map.get(ext, 'application/octet-stream')

    if doc_type == "engagement":
        prompt = """Extract ALL information from this engagement letter or order form. Return ONLY valid JSON:
{"client_name":"","client_email":"","client_phone":"","lender_name":"","loan_number":"","borrower_name":"",
"subject_address":"","city":"","state":"","zip_code":"","property_type":"","appraisal_type":"","fee":"","due_date":""}
Include only fields you find. Omit empty fields."""
    else:
        prompt = """Extract ALL information from this Purchase & Sale Agreement. Return ONLY valid JSON:
{"buyer_name":"","seller_name":"","purchase_price":"","sale_date":"","property_address":"","city":"","state":"",
"zip_code":"","property_type":"","closing_date":"","loan_amount":"","lender_name":""}
Include only fields you find. Omit empty fields."""

    try:
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}

        # Build image content - PDFs need to be converted to images first
        image_contents = []
        if ext == 'pdf':
            # Convert PDF pages to images using PyMuPDF
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
            max_pages = min(len(pdf_doc), 5)  # Limit to first 5 pages
            for page_num in range(max_pages):
                page = pdf_doc[page_num]
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                image_contents.append({
                    'type': 'image_url',
                    'image_url': {'url': f'data:image/png;base64,{img_b64}', 'detail': 'high'}
                })
            pdf_doc.close()
        else:
            # Regular image file
            image_contents.append({
                'type': 'image_url',
                'image_url': {'url': f'data:{media_type};base64,{b64_data}', 'detail': 'high'}
            })

        payload = {
            'model': 'gpt-4o',
            'messages': [{'role': 'user', 'content': image_contents + [{'type': 'text', 'text': prompt}]}],
            'max_tokens': 2000, 'temperature': 0.1
        }
        resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            err_detail = resp.text[:200] if resp.text else str(resp.status_code)
            return {}, f"API error: {resp.status_code} - {err_detail}"
        content = resp.json()['choices'][0]['message']['content']
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(content[json_start:json_end]), None
        return {}, "Could not parse response"
    except Exception as e:
        return {}, str(e)

# ====================== SETTINGS ======================
def get_api_key(key_name):
    """Get API key from st.secrets first, then fall back to settings DB."""
    try:
        # Try streamlit secrets first
        if hasattr(st, 'secrets'):
            secret = st.secrets.get(key_name, "")
            if secret:
                return secret
            # Try nested api_keys structure
            api_keys = st.secrets.get("api_keys", {})
            if isinstance(api_keys, dict):
                secret = api_keys.get(key_name, "")
                if secret:
                    return secret
    except:
        pass
    # Fall back to settings DB
    settings = get_settings()
    return settings.get(key_name, "")

def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def save_settings(settings_dict):
    conn = get_db()
    for key, value in settings_dict.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ====================== FEATURE TIER GATING ======================
def has_feature(feature_name):
    """Check if user's tier has access to this feature."""
    tier_features = {
        "starter": ["order_management", "basic_tools"],
        "professional": ["order_management", "basic_tools", "ai_reports", "document_extraction", "ai_advisor", "xml_export"],
        "enterprise": ["order_management", "basic_tools", "ai_reports", "document_extraction", "ai_advisor",
                       "xml_export", "str_reports", "priority_support", "api_access"]
    }
    user_tier = st.session_state.get("user_tier", "starter")
    return feature_name in tier_features.get(user_tier, [])

def show_feature_lock(feature_name, tier_required="professional"):
    """Display a lock icon and message for locked features."""
    st.markdown(f'<span class="lock-badge">🔒 {tier_required.title()}</span>', unsafe_allow_html=True)

# ====================== AUTH SYSTEM ======================
def show_landing_page():
    """Display login and pricing page when user is not authenticated."""
    # Premium Hero Section
    st.markdown("""
    <div class="hero-banner">
        <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">AppraisalOS</h1>
        <p style="font-size: 1.25rem; color: rgba(255,255,255,0.8); font-weight: 300; margin: 0;">The complete platform for modern appraisers</p>
        <p style="font-size: 0.95rem; color: rgba(255,255,255,0.6); margin-top: 0.75rem; font-weight: 300;">AI-powered tools, USPAP compliance, and GSE-ready reports — all in one place</p>
    </div>
    """, unsafe_allow_html=True)

    # Trust Indicators
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin: 2rem 0; padding: 0 1rem;">
        <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03);">
            <div style="font-size: 1.5rem; font-weight: 700; color: #0071E3;">Beta</div>
            <div style="color: #86868b; font-size: 0.85rem; margin-top: 0.25rem;">Early Access</div>
        </div>
        <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03);">
            <div style="font-size: 1.25rem; color: #0071E3;">✓</div>
            <div style="color: #86868b; font-size: 0.85rem; margin-top: 0.25rem; font-weight: 500;">USPAP Compliant (AI-assisted)</div>
        </div>
        <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03);">
            <div style="font-size: 1.25rem; color: #0071E3;">✓</div>
            <div style="color: #86868b; font-size: 0.85rem; margin-top: 0.25rem; font-weight: 500;">UAD 3.6 Ready</div>
        </div>
        <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03);">
            <div style="font-size: 1.25rem; color: #0071E3;">✓</div>
            <div style="color: #86868b; font-size: 0.85rem; margin-top: 0.25rem; font-weight: 500;">GSE Guidelines Built-In</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Feature Showcase Section
    st.markdown("""
    <div style="margin: 3rem 0; padding: 0 1rem;">
        <h2 style="text-align: center; margin-bottom: 2rem; color: #1d1d1f;">Powerful Features Built for You</h2>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem;">
            <div style="background: white; padding: 2rem; border-radius: 14px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03); transition: all 0.3s ease;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">📊</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #1d1d1f; font-weight: 600;">Order Management</h4>
                <p style="margin: 0; color: #555; font-size: 0.9rem; line-height: 1.5;">Track all appraisal orders in one centralized dashboard with real-time status updates.</p>
            </div>
            <div style="background: white; padding: 2rem; border-radius: 14px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03); transition: all 0.3s ease;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">🤖</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #1d1d1f; font-weight: 600;">AI Report Writer</h4>
                <p style="margin: 0; color: #555; font-size: 0.9rem; line-height: 1.5;">Facts-only narrative generation that frameworks reports with verified data, never hallucinated facts.</p>
            </div>
            <div style="background: white; padding: 2rem; border-radius: 14px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03); transition: all 0.3s ease;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">📄</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #1d1d1f; font-weight: 600;">Document Extraction</h4>
                <p style="margin: 0; color: #555; font-size: 0.9rem; line-height: 1.5;">Automatically extract data from listing sheets, appraisals, and other documents.</p>
            </div>
            <div style="background: white; padding: 2rem; border-radius: 14px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03); transition: all 0.3s ease;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">💬</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #1d1d1f; font-weight: 600;">AI Advisor</h4>
                <p style="margin: 0; color: #555; font-size: 0.9rem; line-height: 1.5;">Get instant answers to appraisal questions from your personal AI assistant.</p>
            </div>
            <div style="background: white; padding: 2rem; border-radius: 14px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03); transition: all 0.3s ease;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">📈</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #1d1d1f; font-weight: 600;">STR Reports</h4>
                <p style="margin: 0; color: #555; font-size: 0.9rem; line-height: 1.5;">Generate short-term rental analysis reports powered by AirDNA data.</p>
            </div>
            <div style="background: white; padding: 2rem; border-radius: 14px; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 1px 8px rgba(0,0,0,0.03); transition: all 0.3s ease;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">🔧</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #1d1d1f; font-weight: 600;">Calculator Tools</h4>
                <p style="margin: 0; color: #555; font-size: 0.9rem; line-height: 1.5;">Access a complete suite of appraisal calculators and reference tools.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pricing Section Header
    st.markdown("""
    <div style="margin: 3rem 0 2rem 0; text-align: center; padding: 0 1rem;">
        <h2 style="color: #1d1d1f; margin-bottom: 0.5rem;">Simple, Transparent Pricing</h2>
        <p style="color: #86868b; font-size: 1rem;">Choose the plan that works for you. Start free for 7 days.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 1])

    with col1:
        # Pricing tier cards
        pricing_cols = st.columns(3, gap="medium")

        tiers = [
            {
                "name": "Starter",
                "price": "29",
                "description": "For independent appraisers",
                "features": [
                    "Order management",
                    "Basic calculator tools",
                    "Up to 5 orders/month",
                    "Email support",
                    "Community access"
                ],
                "key": "starter",
                "cta": "Start Free Trial"
            },
            {
                "name": "Professional",
                "price": "59",
                "description": "Most popular choice",
                "features": [
                    "Everything in Starter",
                    "AI Report Writer (GPT-4o)",
                    "Document Extraction AI",
                    "AI Advisor chatbot",
                    "Unlimited orders",
                    "Priority email support"
                ],
                "key": "professional",
                "featured": True,
                "cta": "Start Free Trial"
            },
            {
                "name": "Enterprise",
                "price": "99",
                "description": "For teams & firms",
                "features": [
                    "Everything in Professional",
                    "UAD 3.6 Package Export",
                    "STR Reports (AirDNA)",
                    "Priority phone support",
                    "API Access",
                    "Advanced analytics"
                ],
                "key": "enterprise",
                "cta": "Contact Sales"
            }
        ]

        for i, tier in enumerate(tiers):
            with pricing_cols[i]:
                featured = tier.get("featured", False)
                badge_html = '<div style="display: inline-block; background: linear-gradient(135deg, #0071E3 0%, #0066d6 100%); color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem;">⭐ Most Popular</div>' if featured else ''
                card_style = "border: 2.5px solid #0071E3; box-shadow: 0 12px 32px rgba(0,122,255,0.15);" if featured else "border: 1px solid rgba(0,0,0,0.06); box-shadow: 0 2px 12px rgba(0,0,0,0.04);"
                transform = "transform: scale(1.02);" if featured else ""
                features_html = ""
                for feature in tier["features"]:
                    features_html += '<li style="padding: 0.6rem 0; color: #555; font-size: 0.9rem; position: relative; padding-left: 1.75rem;"><span style="position: absolute; left: 0; color: #0071E3; font-weight: bold; font-size: 1.1rem;">✓</span>' + feature + '</li>'
                card_html = '<div style="background: white; border-radius: 18px; padding: 2rem 1.5rem; text-align: center; ' + card_style + ' ' + transform + ' transition: all 0.3s ease;">' + badge_html + '<div style="margin: 0 0 0.25rem 0; font-size: 1.4rem; font-weight: 700; color: #1d1d1f;">' + tier['name'] + '</div><div style="color: #86868b; font-size: 0.85rem; margin-bottom: 1.5rem;">' + tier['description'] + '</div><div style="font-size: 2.8rem; font-weight: 700; color: #1d1d1f; margin: 0.75rem 0;"><span style="font-size: 1.5rem; vertical-align: super;">$</span>' + str(tier['price']) + '<span style="font-size: 1rem; color: #86868b; font-weight: 400;">/mo</span></div><ul style="text-align: left; margin: 2rem 0; min-height: 200px; list-style: none; padding: 0;">' + features_html + '</ul></div>'
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button(tier['cta'], key=f"tier_{tier['key']}", use_container_width=True):
                    st.session_state.user_tier = tier['key']
                    st.session_state.show_login = True
                    st.rerun()

    with col2:
        if st.session_state.get("show_login", False):
            st.markdown("""
            <div style="background: white; border-radius: 16px; padding: 2rem; border: 0.5px solid rgba(0,0,0,0.06); box-shadow: 0 2px 12px rgba(0,0,0,0.04);">
                <h3 style="margin: 0 0 1.5rem 0; color: #1d1d1f;">Sign In</h3>
            </div>
            """, unsafe_allow_html=True)

            with st.form("login_form", border=False):
                email = st.text_input("Email", value="", placeholder="demo@example.com")
                password = st.text_input("Password", type="password", value="", placeholder="demo123")

                col_submit, col_demo = st.columns(2)
                with col_submit:
                    login_btn = st.form_submit_button("Sign In", use_container_width=True)
                with col_demo:
                    demo_btn = st.form_submit_button("Demo Login", use_container_width=True)

                if login_btn:
                    if email and password:
                        # Simple demo authentication
                        if email.lower() == "demo@appraiser.com" and password == "demo123":
                            st.session_state.authenticated = True
                            st.session_state.user_name = "Demo Appraiser"
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Try demo@appraiser.com / demo123")
                    else:
                        st.error("Please enter email and password")

                if demo_btn:
                    st.session_state.authenticated = True
                    st.session_state.user_name = "Demo Appraiser"
                    st.session_state.user_tier = "professional"
                    st.rerun()
        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(0,122,255,0.05) 0%, rgba(0,122,255,0.02) 100%); border: 1px solid rgba(0,122,255,0.1); border-radius: 12px; padding: 1.5rem; margin-top: 0.5rem;">
                <h4 style="margin: 0 0 1rem 0; color: #1d1d1f; font-weight: 600;">Ready to Get Started?</h4>
                <p style="margin: 0 0 0.75rem 0; color: #555; font-size: 0.9rem; line-height: 1.5;">Try a plan free for 7 days. No credit card required.</p>
                <p style="margin: 0.75rem 0 0 0; color: #555; font-size: 0.85rem;"><strong>Demo Credentials:</strong></p>
                <p style="margin: 0.25rem 0; color: #555; font-size: 0.85rem;">Email: demo@appraiser.com</p>
                <p style="margin: 0.25rem 0 0.75rem 0; color: #555; font-size: 0.85rem;">Password: demo123</p>
                <p style="margin: 0; color: #86868b; font-size: 0.85rem; font-style: italic;">Or click "Demo Login" on any pricing tier.</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem 1rem; color: #86868b; font-size: 0.85rem;">
        <p style="margin: 0;">Powered by <strong>A-Tech Appraisal Co., LLC</strong> • Warwick, RI</p>
        <p style="margin: 0.5rem 0 0 0;">AppraisalOS is the complete platform for modern appraisers</p>
    </div>
    """, unsafe_allow_html=True)

# ====================== AUTH GATE ======================
if not st.session_state.authenticated:
    show_landing_page()
    st.stop()

# ====================== MAIN APP (ONLY SHOWN IF AUTHENTICATED) ======================

# Hero banner with user greeting
st.markdown(f"""
<div class="hero-banner">
    <h1>AppraisalOS</h1>
    <p>Welcome, {st.session_state.user_name} • {st.session_state.user_tier.title()} Plan</p>
</div>
""", unsafe_allow_html=True)

# Logout button in sidebar
with st.sidebar:
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_name = ""
        st.session_state.user_tier = "starter"
        st.rerun()

# ====================== NAVIGATION ======================
tab0, tab1, tab2, tab3, tab5_tools, tab6_str, tab7_advisor, tab7_qc, tab4, tab5 = st.tabs([
    "🏠 Home", "📊 Dashboard", "📝 New Order", "🤖 AI Reports",
    "🔧 Tools", "📈 STR Reports", "💬 AI Advisor", "🔍 QC Review", "📋 Activity Log", "⚙️ Settings"
])

# ====================== TAB 0: HOME ======================
with tab0:
    conn = get_db()
    df_home = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    conn.close()
    total_h = len(df_home)
    pending_h = len(df_home[df_home["status"] == "Pending"]) if not df_home.empty else 0
    completed_h = len(df_home[df_home["status"] == "Completed"]) if not df_home.empty else 0
    revenue_h = df_home["fee"].sum() if not df_home.empty else 0

    st.markdown(f"### Welcome, {st.session_state.user_name}!")
    st.markdown("Your appraisal management command center.")

    st.markdown("---")
    st.markdown("## Quick Stats")

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [(c1, total_h, "Total Orders"), (c2, pending_h, "Pending"), (c3, completed_h, "Completed"), (c4, f"${revenue_h:,.0f}", "Revenue")]:
        col.markdown(f'<div class="metric-card"><div class="metric-label">{lbl}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Due Today
    today_str = datetime.now().strftime('%Y-%m-%d')
    st.markdown("## Due Today")
    due_today = df_home[df_home["due_date"].str.startswith(today_str, na=False)] if not df_home.empty else pd.DataFrame()
    if not due_today.empty:
        due_display = due_today[["order_id", "subject_address", "client_name", "status"]].copy()
        st.dataframe(due_display, use_container_width=True, hide_index=True)
    else:
        st.info("No appraisals due today")

    st.markdown("---")

    # Inspections This Week
    st.markdown("## Inspections This Week")
    week_start = datetime.now()
    week_end = week_start + pd.Timedelta(days=7)
    if not df_home.empty:
        week_inspections = df_home[
            (df_home["inspection_date"] >= week_start.strftime('%Y-%m-%d')) &
            (df_home["inspection_date"] <= week_end.strftime('%Y-%m-%d'))
        ]
        if not week_inspections.empty:
            week_display = week_inspections[["order_id", "subject_address", "client_name", "inspection_date"]].copy()
            st.dataframe(week_display, use_container_width=True, hide_index=True)
        else:
            st.info("No inspections scheduled this week")
    else:
        st.info("No inspections scheduled")

    st.markdown("---")

    # Needs Review
    st.markdown("## Needs Review")
    review_needed = df_home[df_home["status"] == "Review"] if not df_home.empty else pd.DataFrame()
    if not review_needed.empty:
        review_display = review_needed[["order_id", "subject_address", "client_name"]].copy()
        st.dataframe(review_display, use_container_width=True, hide_index=True)
    else:
        st.info("All reviewed orders are current")

    st.markdown("---")

    # Recent AI Drafts
    st.markdown("## Recent AI Drafts")
    ai_drafts = df_home[df_home["ai_narrative"].notna()] if not df_home.empty else pd.DataFrame()
    if not ai_drafts.empty:
        recent_drafts = ai_drafts.head(5)[["order_id", "subject_address", "updated_at"]].copy()
        st.dataframe(recent_drafts, use_container_width=True, hide_index=True)
    else:
        st.info("No AI narratives generated yet")

# ====================== TAB 1: DASHBOARD ======================
with tab1:
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    conn.close()

    # KPI row with custom metric cards
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    pending = len(df[df["status"] == "Pending"]) if not df.empty else 0
    in_progress = len(df[df["status"] == "In Progress"]) if not df.empty else 0
    completed = len(df[df["status"] == "Completed"]) if not df.empty else 0

    col1.markdown(f'<div class="metric-card"><div class="metric-label">Total Orders</div><div class="metric-value">{total}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><div class="metric-label">Pending</div><div class="metric-value">{pending}</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><div class="metric-label">In Progress</div><div class="metric-value">{in_progress}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-card"><div class="metric-label">Completed</div><div class="metric-value">{completed}</div></div>', unsafe_allow_html=True)

    st.divider()

    # Filter controls with better layout
    st.markdown("### Filter Orders")
    fcol1, fcol2, fcol3 = st.columns(3)

    with fcol1:
        st.markdown('<label style="font-size: 0.8rem; color: #86868b;">Status</label>', unsafe_allow_html=True)
        status_filter = st.selectbox("Filter by Status", ["All", "Pending", "In Progress", "Completed", "On Hold", "Cancelled"], label_visibility="collapsed")

    with fcol2:
        st.markdown('<label style="font-size: 0.8rem; color: #86868b;">Appraiser</label>', unsafe_allow_html=True)
        appraiser_filter = st.selectbox("Filter by Appraiser", ["All"] + (df["assigned_appraiser"].dropna().unique().tolist() if not df.empty else []), label_visibility="collapsed")

    with fcol3:
        st.markdown('<label style="font-size: 0.8rem; color: #86868b;">Search</label>', unsafe_allow_html=True)
        search = st.text_input("Search (address, client, order ID)", label_visibility="collapsed")

    # Apply filters
    filtered = df.copy()
    if not filtered.empty:
        if status_filter != "All":
            filtered = filtered[filtered["status"] == status_filter]
        if appraiser_filter != "All":
            filtered = filtered[filtered["assigned_appraiser"] == appraiser_filter]
        if search:
            mask = (
                filtered["subject_address"].str.contains(search, case=False, na=False) |
                filtered["client_name"].str.contains(search, case=False, na=False) |
                filtered["order_id"].str.contains(search, case=False, na=False)
            )
            filtered = filtered[mask]

    if not filtered.empty:
        # Status indicators
        status_icons = {"Pending": "🔴", "In Progress": "🟡", "Completed": "🟢", "On Hold": "🟠", "Cancelled": "⚫"}
        filtered["Status Display"] = filtered["status"].apply(lambda s: f"{status_icons.get(s, '⚪')} {s}")

        display_cols = ["order_id", "subject_address", "client_name", "status", "fee", "created_at"]
        available = [c for c in display_cols if c in filtered.columns]
        st.dataframe(filtered[available], use_container_width=True, hide_index=True)

        # Order detail expander
        st.markdown("---")
        st.markdown("### Order Details")
        selected = st.selectbox("Select an order to view", filtered["order_id"].tolist(), key="dash_select")
        if selected:
            conn = get_db()
            order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (selected,)).fetchone()
            conn.close()
            if order:
                dcol1, dcol2 = st.columns(2)
                with dcol1:
                    st.write(f"**Client:** {order['client_name']}")
                    st.write(f"**Email:** {order['client_email']}")
                    st.write(f"**Phone:** {order['client_phone'] or 'N/A'}")
                    st.write(f"**Lender:** {order['lender_name'] or 'N/A'}")
                    st.write(f"**Loan #:** {order['loan_number'] or 'N/A'}")
                with dcol2:
                    st.write(f"**Address:** {order['subject_address']}")
                    st.write(f"**City/State/Zip:** {order['city'] or ''}, {order['state'] or 'RI'} {order['zip_code'] or ''}")
                    st.write(f"**Type:** {order['property_type']} | **Form:** {order['form_type']}")
                    st.write(f"**Fee:** ${order['fee'] or 0:.2f}")
                    st.write(f"**Due:** {order['due_date'] or 'Not set'}")
                    st.write(f"**Inspection:** {order['inspection_date'] or 'Not set'}")

                if order["field_notes"]:
                    with st.expander("📝 Field Notes"):
                        st.write(order["field_notes"])

                if order["ai_narrative"]:
                    with st.expander("🤖 AI Narrative"):
                        st.write(order["ai_narrative"])

                # Photo gallery
                if order["photos"]:
                    with st.expander("📸 Photos"):
                        photo_paths = [p.strip() for p in order["photos"].split(",") if p.strip()]
                        photo_cols = st.columns(min(4, len(photo_paths)))
                        for i, path in enumerate(photo_paths):
                            if os.path.exists(path):
                                with photo_cols[i % 4]:
                                    st.image(path, use_container_width=True)

                # Quick status update
                st.divider()
                st.markdown("### Quick Status Update")
                qcol1, qcol2 = st.columns([3, 1])
                with qcol1:
                    new_status = st.selectbox("Update Status",
                        ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"],
                        index=["Pending", "In Progress", "Completed", "On Hold", "Cancelled"].index(order["status"]),
                        key="quick_status", label_visibility="collapsed"
                    )
                with qcol2:
                    if st.button("✓ Update", use_container_width=True):
                        conn = get_db()
                        conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?",
                                    (new_status, datetime.now().isoformat(), selected))
                        conn.commit()
                        conn.close()
                        log_activity(selected, "Status Changed", f"Changed to {new_status}")

                        # Auto-email on completion
                        if new_status == "Completed" and order["client_email"]:
                            settings = get_settings()
                            body = f"""
                            <h2>Appraisal Complete</h2>
                            <p>Your appraisal for <strong>{order['subject_address']}</strong> has been completed.</p>
                            <p><strong>Value Opinion:</strong> {order['value_opinion'] or 'See attached report'}</p>
                            <p>Your report will be delivered shortly.</p>
                            <br>
                            <p>AppraisalOS<br>Powered by A-Tech Appraisal Co.</p>
                            """
                            success, msg = send_email(
                                order["client_email"],
                                f"Appraisal Complete - {order['subject_address']}",
                                body, settings
                            )
                            if success:
                                st.success(f"Completion email sent to {order['client_email']}")
                            else:
                                st.warning(f"Email not sent: {msg}")

                        st.success(f"Status updated to {new_status}")
                        st.rerun()
    else:
        st.info("No orders found matching your filters.")

# ====================== TAB 2: NEW ORDER ======================
with tab2:
    st.markdown("### Create New Order")
    st.info("**Tip:** Upload an engagement letter or P&S agreement below to auto-fill the order form. The AI will read your document and fill in client info, property address, lender details, and more.")

    # ---- Quick Import Section ----
    settings_for_extract = get_settings()
    extract_api_key = get_api_key("openai_api_key") if 'get_api_key' in dir() else settings_for_extract.get("openai_api_key", "")

    with st.expander("📄 Upload Documents to Auto-Fill Order", expanded=True):
        ei_col1, ei_col2 = st.columns(2)
        with ei_col1:
            st.markdown("**Engagement Letter / Order Form**")
            eng_file = st.file_uploader("Upload engagement letter or order form", type=["pdf", "jpg", "jpeg", "png"], key="eng_upload")
            if eng_file and st.button("Extract & Auto-Fill", key="extract_eng"):
                if not extract_api_key:
                    st.error("Set your OpenAI API key in Settings first.")
                else:
                    with st.spinner("AI is reading your document..."):
                        data, err = extract_document_data(eng_file, extract_api_key, "engagement")
                        if err:
                            st.error(f"Extraction error: {err}")
                        elif data:
                            st.session_state.extracted_data = data
                            st.success(f"Extracted {len(data)} fields! Form below has been pre-filled.")
                            with st.expander("Preview extracted data"):
                                st.json(data)
                        else:
                            st.warning("No data could be extracted from this document.")

        with ei_col2:
            st.markdown("**Purchase & Sale Agreement**")
            ps_file = st.file_uploader("Upload P&S agreement", type=["pdf", "jpg", "jpeg", "png"], key="ps_upload")
            if ps_file and st.button("Extract P&S Data", key="extract_ps"):
                if not extract_api_key:
                    st.error("Set your OpenAI API key in Settings first.")
                else:
                    with st.spinner("AI is reading your P&S agreement..."):
                        data, err = extract_document_data(ps_file, extract_api_key, "purchase")
                        if err:
                            st.error(f"Extraction error: {err}")
                        elif data:
                            st.session_state.extracted_ps_data = data
                            st.success(f"Extracted {len(data)} fields from P&S!")
                            with st.expander("Preview P&S data"):
                                st.json(data)
                        else:
                            st.warning("No data could be extracted.")

    # Merge extracted data for form defaults (engagement letter + P&S)
    ex = st.session_state.get("extracted_data", {})
    ps = st.session_state.get("extracted_ps_data", {})
    merged = {**ps, **ex}  # engagement letter data takes priority

    st.divider()

    with st.form("new_order_form", border=False):
        st.markdown("#### Client Information")
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            client_name = st.text_input("Client Name *", value=merged.get("client_name", merged.get("borrower_name", "")), placeholder="John Doe")
        with fcol2:
            client_email = st.text_input("Email *", value=merged.get("client_email", merged.get("contact_email", "")), placeholder="john@example.com")

        fcol3, fcol4 = st.columns(2)
        with fcol3:
            client_phone = st.text_input("Phone", value=merged.get("client_phone", merged.get("contact_phone", "")), placeholder="(401) 555-1234")
        with fcol4:
            assigned_appraiser = st.text_input("Assigned Appraiser", value=merged.get("appraiser_name", ""), placeholder="Your Name")

        st.markdown("#### Lender Information")
        lcol1, lcol2 = st.columns(2)
        with lcol1:
            lender_name = st.text_input("Lender Name", value=merged.get("lender_name", merged.get("lender", "")), placeholder="First National Bank")
        with lcol2:
            loan_number = st.text_input("Loan Number", value=merged.get("loan_number", merged.get("case_number", "")), placeholder="LN-123456")

        st.markdown("#### Property Information")
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            subject_address = st.text_input("Subject Address *", value=merged.get("subject_address", merged.get("property_address", "")), placeholder="123 Main St")
        with pcol2:
            property_type = st.selectbox("Property Type *",
                ["Single Family", "Condo", "Townhouse", "Multi-Family 2-4", "Multi-Family 5+"],
                label_visibility="collapsed")

        pcol3, pcol4, pcol5 = st.columns(3)
        with pcol3:
            city = st.text_input("City *", value=merged.get("city", merged.get("property_city", "")), placeholder="Warwick")
        with pcol4:
            _states = ["RI", "MA", "CT", "NY", "Other"]
            _ext_state = merged.get("state", merged.get("property_state", ""))
            _state_idx = _states.index(_ext_state) if _ext_state in _states else 0
            state = st.selectbox("State", _states, index=_state_idx, label_visibility="collapsed")
        with pcol5:
            zip_code = st.text_input("Zip", value=merged.get("zip_code", merged.get("property_zip", "")), placeholder="02886")

        st.markdown("#### Appraisal Details")
        acol1, acol2 = st.columns(2)
        with acol1:
            appraisal_type = st.selectbox("Appraisal Type", ["1004", "1025", "1073"], index=0, label_visibility="collapsed")
        with acol2:
            form_type = st.selectbox("Form Type", ["URAR", "FNMA", "FHLMC", "VA"], index=0, label_visibility="collapsed")

        acol3, acol4 = st.columns(2)
        with acol3:
            _fee_val = 0.0
            try:
                _fee_str = merged.get("fee", "0")
                if _fee_str:
                    _fee_val = float(str(_fee_str).replace("$", "").replace(",", ""))
            except:
                _fee_val = 0.0
            fee = st.number_input("Fee", min_value=0.0, value=_fee_val, step=50.0)
        with acol4:
            due_date = st.date_input("Due Date")

        acol5, acol6 = st.columns(2)
        with acol5:
            inspection_date = st.date_input("Inspection Date")
        with acol6:
            value_opinion = st.text_input("Preliminary Value Opinion", placeholder="$500,000")

        st.markdown("#### Property Details (for URAR)")
        prefill_pd = merged if merged else {}

        pdcol1, pdcol2, pdcol3 = st.columns(3)
        with pdcol1:
            pd_year_built = st.text_input("Year Built", value=prefill_pd.get("year_built", ""))
            pd_stories = st.text_input("Stories", value=prefill_pd.get("stories", ""))
            pd_design_style = st.text_input("Design/Style", value=prefill_pd.get("design_style", ""), placeholder="e.g. Colonial, Ranch, Cape Cod")
            pd_exterior = st.text_input("Exterior", value=prefill_pd.get("exterior_desc", ""), placeholder="e.g. Vinyl Siding")
            pd_foundation = st.selectbox("Foundation", ["Full Basement", "Partial Basement", "Crawl Space", "Slab", "Other"],
                index=["Full Basement", "Partial Basement", "Crawl Space", "Slab", "Other"].index(prefill_pd.get("foundation_type", "Full Basement")) if prefill_pd.get("foundation_type") in ["Full Basement", "Partial Basement", "Crawl Space", "Slab", "Other"] else 0)
            pd_basement_sqft = st.text_input("Basement Sq Ft", value=prefill_pd.get("basement_sqft", ""))
            pd_basement_fin = st.text_input("Basement Finished %", value=prefill_pd.get("basement_finished_pct", ""))
        with pdcol2:
            pd_total_rooms = st.text_input("Total Rooms", value=prefill_pd.get("total_rooms", ""))
            pd_bedrooms = st.text_input("Bedrooms", value=prefill_pd.get("bedrooms", ""))
            pd_bathrooms = st.text_input("Bathrooms", value=prefill_pd.get("bathrooms", ""))
            pd_gla = st.text_input("GLA (Sq Ft)", value=prefill_pd.get("gla_sqft", ""))
            pd_heating = st.text_input("Heating", value=prefill_pd.get("heating_type", ""), placeholder="e.g. FWA/Gas")
            pd_cooling = st.text_input("Cooling", value=prefill_pd.get("cooling_type", ""), placeholder="e.g. Central AC")
            pd_condition = st.selectbox("Condition (C1-C6)", ["", "C1", "C2", "C3", "C4", "C5", "C6"],
                index=["", "C1", "C2", "C3", "C4", "C5", "C6"].index(prefill_pd.get("condition_rating", "")) if prefill_pd.get("condition_rating", "") in ["", "C1", "C2", "C3", "C4", "C5", "C6"] else 0)
        with pdcol3:
            pd_quality = st.selectbox("Quality (Q1-Q6)", ["", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6"],
                index=["", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6"].index(prefill_pd.get("quality_rating", "")) if prefill_pd.get("quality_rating", "") in ["", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6"] else 0)
            pd_lot_dims = st.text_input("Lot Dimensions", value=prefill_pd.get("lot_dimensions", ""))
            pd_lot_area = st.text_input("Lot Area (Sq Ft or Acres)", value=prefill_pd.get("lot_area", ""))
            pd_zoning = st.text_input("Zoning", value=prefill_pd.get("zoning", ""), placeholder="e.g. R-1")
            pd_garage = st.selectbox("Garage", ["None", "1-Car Attached", "2-Car Attached", "3-Car Attached", "1-Car Detached", "2-Car Detached", "Carport"],
                index=["None", "1-Car Attached", "2-Car Attached", "3-Car Attached", "1-Car Detached", "2-Car Detached", "Carport"].index(prefill_pd.get("garage_type", "None")) if prefill_pd.get("garage_type") in ["None", "1-Car Attached", "2-Car Attached", "3-Car Attached", "1-Car Detached", "2-Car Detached", "Carport"] else 0)
            pd_county = st.text_input("County", value=prefill_pd.get("county", ""))
            pd_neighborhood = st.text_input("Neighborhood", value=prefill_pd.get("neighborhood_name", ""))

        pdcol4, pdcol5 = st.columns(2)
        with pdcol4:
            pd_assessor = st.text_input("Assessor Parcel #", value=prefill_pd.get("assessor_parcel", ""))
            pd_tax_year = st.text_input("Tax Year", value=prefill_pd.get("tax_year", ""))
            pd_tax_amount = st.text_input("Annual Taxes ($)", value=prefill_pd.get("tax_amount", ""))
        with pdcol5:
            pd_flood_zone = st.text_input("Flood Zone", value=prefill_pd.get("flood_zone", ""), placeholder="e.g. X, A, AE")
            pd_flood_map = st.text_input("Flood Map #", value=prefill_pd.get("flood_map_id", ""))
            pd_legal = st.text_input("Legal Description", value=prefill_pd.get("legal_desc", ""))

        st.markdown("#### Additional Notes")
        field_notes = st.text_area("Field Notes", placeholder="Any notes about the inspection or appraisal...")

        # Photo upload
        uploaded_files = st.file_uploader("Upload Photos", accept_multiple_files=True, type=["jpg", "png", "jpeg"])

        submit_btn = st.form_submit_button("✓ Create Order", use_container_width=True)

        if submit_btn:
            if not client_name or not client_email or not subject_address or not property_type:
                st.error("Please fill in all required fields (*)")
            else:
                order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                # Handle photos
                photos_saved = []
                if uploaded_files:
                    os.makedirs("photos", exist_ok=True)
                    for file in uploaded_files:
                        path = f"photos/{order_id}_{file.name}"
                        with open(path, "wb") as f:
                            f.write(file.getbuffer())
                        photos_saved.append(path)

                # Build property_details JSON
                property_details = {
                    "year_built": pd_year_built,
                    "stories": pd_stories,
                    "design_style": pd_design_style,
                    "exterior_desc": pd_exterior,
                    "foundation_type": pd_foundation,
                    "basement_sqft": pd_basement_sqft,
                    "basement_finished_pct": pd_basement_fin,
                    "total_rooms": pd_total_rooms,
                    "bedrooms": pd_bedrooms,
                    "bathrooms": pd_bathrooms,
                    "gla_sqft": pd_gla,
                    "heating_type": pd_heating,
                    "cooling_type": pd_cooling,
                    "condition_rating": pd_condition,
                    "quality_rating": pd_quality,
                    "lot_dimensions": pd_lot_dims,
                    "lot_area": pd_lot_area,
                    "zoning": pd_zoning,
                    "garage_type": pd_garage,
                    "county": pd_county,
                    "neighborhood_name": pd_neighborhood,
                    "assessor_parcel": pd_assessor,
                    "tax_year": pd_tax_year,
                    "tax_amount": pd_tax_amount,
                    "flood_zone": pd_flood_zone,
                    "flood_map_id": pd_flood_map,
                    "legal_desc": pd_legal
                }
                property_details_json = json.dumps(property_details)
                all_photos = ",".join(photos_saved) if photos_saved else ""

                conn = get_db()
                conn.execute("""
                    INSERT INTO orders (
                        order_id, client_name, client_email, client_phone, lender_name, loan_number,
                        subject_address, city, state, zip_code, property_type, appraisal_type, form_type,
                        assigned_appraiser, fee, due_date, inspection_date, status, value_opinion,
                        field_notes, property_details, photos, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_id, client_name, client_email, client_phone, lender_name, loan_number,
                    subject_address, city, state, zip_code, property_type, appraisal_type, form_type,
                    assigned_appraiser, fee, due_date.isoformat() if due_date else None,
                    inspection_date.isoformat() if inspection_date else None,
                    "Pending", value_opinion, field_notes, property_details_json, all_photos,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                conn.commit()
                conn.close()
                log_activity(order_id, "Created", f"New order: {subject_address}")
                st.success(f"Order created: {order_id}")
                st.session_state.show_form = False

# ====================== TAB 3: AI REPORTS ======================
with tab3:
    if not has_feature("ai_reports"):
        st.warning("🔒 AI Reports require Professional plan or higher")
        st.info("Upgrade your plan to unlock AI-powered report generation")
    else:
        st.markdown("### AI Report Generator")
        st.markdown("Generate comprehensive appraisal narratives and reports using GPT-4o")

        conn = get_db()
        orders = conn.execute("SELECT order_id, subject_address FROM orders ORDER BY created_at DESC").fetchall()
        conn.close()

        if orders:
            selected_order_id = st.selectbox("Select Order", [o["order_id"] for o in orders])

            if selected_order_id:
                conn = get_db()
                order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (selected_order_id,)).fetchone()
                conn.close()

                if order:
                    st.markdown(f"**Order:** {order['order_id']}")
                    st.markdown(f"**Property:** {order['subject_address']}, {order['city']}, {order['state']} {order['zip_code']}")

                    settings = get_settings()
                    api_key = settings.get("openai_api_key", "")

                    if not api_key:
                        st.error("OpenAI API key not configured. Go to Settings to add it.")
                    else:
                        st.markdown("#### Section-by-Section AI Generation")
                        st.caption("Generate individual sections to review and edit independently")

                        sec_col1, sec_col2, sec_col3 = st.columns(3)
                        with sec_col1:
                            if st.button("📍 Neighborhood", use_container_width=True):
                                with st.spinner("Generating Neighborhood section..."):
                                    section_text, error = generate_section(dict(order), api_key, "Neighborhood")
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        st.success("Neighborhood section generated!")
                                        st.text_area("Edit Neighborhood Section:", value=section_text, height=200, key="neighborhood_edit")

                        with sec_col2:
                            if st.button("🏠 Site", use_container_width=True):
                                with st.spinner("Generating Site section..."):
                                    section_text, error = generate_section(dict(order), api_key, "Site")
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        st.success("Site section generated!")
                                        st.text_area("Edit Site Section:", value=section_text, height=200, key="site_edit")

                        with sec_col3:
                            if st.button("🏢 Improvements", use_container_width=True):
                                with st.spinner("Generating Improvements section..."):
                                    section_text, error = generate_section(dict(order), api_key, "Improvements")
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        st.success("Improvements section generated!")
                                        st.text_area("Edit Improvements Section:", value=section_text, height=200, key="improvements_edit")

                        sec_col4, sec_col5, sec_col6 = st.columns(3)
                        with sec_col4:
                            if st.button("📊 Sales Comp", use_container_width=True):
                                with st.spinner("Generating Sales Comparison framework..."):
                                    section_text, error = generate_section(dict(order), api_key, "Sales Comparison")
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        st.success("Sales Comparison framework generated!")
                                        st.text_area("Edit Sales Comparison:", value=section_text, height=200, key="salescomp_edit")

                        with sec_col5:
                            if st.button("💰 Cost", use_container_width=True):
                                with st.spinner("Generating Cost Approach framework..."):
                                    section_text, error = generate_section(dict(order), api_key, "Cost Approach")
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        st.success("Cost Approach framework generated!")
                                        st.text_area("Edit Cost Approach:", value=section_text, height=200, key="cost_edit")

                        with sec_col6:
                            if st.button("✓ Reconciliation", use_container_width=True):
                                with st.spinner("Generating Reconciliation framework..."):
                                    section_text, error = generate_section(dict(order), api_key, "Reconciliation")
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        st.success("Reconciliation framework generated!")
                                        st.text_area("Edit Reconciliation:", value=section_text, height=200, key="reconciliation_edit")

                        st.divider()

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🤖 Generate Full Narrative"):
                                with st.spinner("Generating narrative (this may take 1-2 minutes)..."):
                                    narrative, error = generate_narrative(dict(order), api_key)
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        conn = get_db()
                                        conn.execute("UPDATE orders SET ai_narrative = ? WHERE order_id = ?",
                                                   (narrative, selected_order_id))
                                        conn.commit()
                                        conn.close()
                                        st.success("Narrative generated and saved!")
                                        st.rerun()

                        with col2:
                            if st.button("📊 Generate Report Data"):
                                with st.spinner("Generating report structure..."):
                                    report_data, error = generate_report_data(dict(order), api_key)
                                    if error:
                                        st.error(f"Error: {error}")
                                    else:
                                        st.session_state.extracted_data = report_data
                                        st.success("Report data generated!")
                                        st.json(report_data)

                        st.divider()

                        if order["ai_narrative"]:
                            with st.expander("📄 View Generated Narrative"):
                                st.write(order["ai_narrative"])
                                if st.button("📋 Copy Narrative"):
                                    st.info("Narrative copied to clipboard (feature depends on browser)")

                        # XML Export Section (UAD 3.6GSE)
                        if has_feature("xml_export"):
                            st.divider()
                            st.markdown("#### UAD 3.6 Export & Integration")
                            ecol1, ecol2 = st.columns(2)
                            with ecol1:
                                if st.button("📦 Export UAD 3.6 Package", use_container_width=True):
                                        order_data = dict(order)
                                        # Build UAD XML matching TOTAL/a la mode format (UAD 3.6GSE)
                                        addr = order_data.get("subject_address", "")
                                        city = order_data.get("city", "")
                                        state = order_data.get("state", "RI")
                                        zipcode = order_data.get("zip_code", "")
                                        appraiser_name = order_data.get("assigned_appraiser", "")
                                        borrower_name = order_data.get("borrower_name", order_data.get("client_name", ""))
                                        lender_name = order_data.get("lender_name", "")
                                        loan_num = order_data.get("loan_number", "")
                                        val_opinion = str(order_data.get("value_opinion", ""))
                                        ptype = order_data.get("property_type", "Single Family")
                                        form_type_map = {"Single Family": "FNM1004", "Condo": "FNM1073", "Multi-Family": "FNM1025", "Townhouse": "FNM1004", "Co-op": "FNM1004"}
                                        form_type = form_type_map.get(ptype, "FNM1004")
                                        title_map = {"FNM1004": "Uniform Residential Appraisal Report", "FNM1073": "Individual Condominium Unit Appraisal Report", "FNM1025": "Small Residential Income Property Appraisal Report"}
                                        title_desc = title_map.get(form_type, "Uniform Residential Appraisal Report")
                                        today_str = datetime.now().strftime("%m/%d/%Y")
                                        insp_date = order_data.get("inspection_date", "") or ""

                                        # Extract property details
                                        p = {}
                                        pd_str = order_data.get("property_details", "") or "{}"
                                        try:
                                            p = json.loads(pd_str)
                                        except:
                                            p = {}

                                        # Load AI-generated report data if available
                                        rd = {}
                                        rd_str = settings.get(f"report_data_{order_data['order_id']}", "")
                                        if rd_str:
                                            try:
                                                rd = json.loads(rd_str)
                                            except:
                                                rd = {}
                                        comps = rd.get("comps", []) or []
                                        nb = rd.get("neighborhood", {}) or {}
                                        comments = rd.get("comments", {}) or {}
                                        cost = rd.get("cost_approach", {}) or {}
                                        sd = rd.get("site", {}) or {}
                                        si = rd.get("subject_improvements", {}) or {}
                                        prior_sales = rd.get("prior_sales", {}) or {}
                                        val_summary = rd.get("valuation_summary", {}) or {}
                                        addendum_text = comments.get("addendum", "")
                                        narrative_text = order_data.get("ai_narrative", "")

                                        yr = str(p.get("year_built", "") or si.get("year_built", "") or "")
                                        stories = str(p.get("stories", "") or si.get("stories", "") or "")
                                        design = str(p.get("design_style", "") or si.get("design_style", "") or "")
                                        ext_desc = str(p.get("exterior_desc", "") or si.get("exterior_walls", "") or "")
                                        found_type = str(p.get("foundation_type", "") or si.get("foundation", "") or sd.get("foundation", "") or "Full Basement")
                                        bsmt_sqft = str(p.get("basement_sqft", "") or si.get("basement_total_sqft", "") or "")
                                        bsmt_fin = str(p.get("basement_finished_pct", "") or si.get("basement_finished_sqft", "") or "")
                                        tot_rooms = str(p.get("total_rooms", "") or si.get("total_rooms", "") or "")
                                        beds = str(p.get("bedrooms", "") or si.get("bedrooms", "") or "")
                                        baths = str(p.get("bathrooms", "") or si.get("bathrooms", "") or "")
                                        gla = str(p.get("gla_sqft", "") or si.get("gla", "") or "")
                                        heat = str(p.get("heating_type", "") or si.get("heating_cooling", "") or "")
                                        cool = str(p.get("cooling_type", "") or si.get("cooling", "") or "")
                                        cond = str(p.get("condition_rating", "") or si.get("condition", "") or "")
                                        qual = str(p.get("quality_rating", "") or si.get("quality", "") or "")
                                        exterior_walls = str(p.get("exterior_walls", "") or si.get("exterior_walls", "") or "")
                                        roof_surface = str(p.get("roof_surface", "") or si.get("roof_surface", "") or "")
                                        view_desc = str(p.get("view", "") or sd.get("view", "") or si.get("view", "") or "")
                                        lot_dims = str(p.get("lot_dimensions", "") or sd.get("dimensions", "") or "")
                                        lot_area = str(p.get("lot_area", "") or sd.get("area", "") or "")
                                        zoning = str(p.get("zoning", "") or sd.get("zoning_class", "") or "")
                                        garage = str(p.get("garage_type", "") or si.get("garage_parking", "") or "None")
                                        garage_spaces_raw = str(p.get("garage_spaces", "") or si.get("garage_spaces", "") or "")
                                        eff_age_subj = str(p.get("effective_age", "") or si.get("effective_age", "") or "")
                                        county = p.get("county", "")
                                        neighborhood = p.get("neighborhood_name", "")
                                        assessor = p.get("assessor_parcel", "")
                                        tax_yr = p.get("tax_year", "")
                                        tax_amt = p.get("tax_amount", "")
                                        flood_z = p.get("flood_zone", "")
                                        flood_map = p.get("flood_map_id", "")
                                        legal = p.get("legal_desc", "")
                                        # Garage parsing
                                        garage_spaces = garage_spaces_raw
                                        garage_xml_type = "None"
                                        if not garage_spaces:
                                            if "1-Car" in garage or "1 car" in garage.lower():
                                                garage_spaces = "1"
                                            elif "2-Car" in garage or "2 car" in garage.lower():
                                                garage_spaces = "2"
                                            elif "3-Car" in garage or "3 car" in garage.lower():
                                                garage_spaces = "3"
                                        if "Attached" in garage:
                                            garage_xml_type = "Attached"
                                        elif "Detached" in garage:
                                            garage_xml_type = "Detached"
                                        elif "Carport" in garage:
                                            garage_xml_type = "Carport"
                                        # Foundation mapping
                                        found_map = {"Full Basement": "Basement", "Partial Basement": "Basement", "Crawl Space": "CrawlSpace", "Slab": "Slab", "Other": "Other"}
                                        found_xml = found_map.get(found_type, "Basement")
                                        found_cond = "Full" if "Full" in found_type else ("Partial" if "Partial" in found_type else "")

                                        # XML escape helper
                                        import xml.sax.saxutils as saxutils
                                        def xesc(val):
                                            if val is None:
                                                return ""
                                            return saxutils.escape(str(val), {'"': '&quot;', "'": '&apos;'})

                                        xml_lines = []
                                        xml_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
                                        xml_lines.append('<VALUATION_RESPONSE MISMOVersionID="2.6">')

                                        # DOCUMENT_CLASSIFICATION - required for TOTAL to recognize UAD format
                                        xml_lines.append('  <DOCUMENT_CLASSIFICATION>')
                                        xml_lines.append('    <DOCUMENT_CLASSES>')
                                        xml_lines.append('      <DOCUMENT_CLASS _Name="VALUATION" />')
                                        xml_lines.append('    </DOCUMENT_CLASSES>')
                                        xml_lines.append('  </DOCUMENT_CLASSIFICATION>')

                                        # REPORT section
                                        xml_lines.append(f'  <REPORT USPAPReportDescription="{xesc(addr)} - Appraisal" AppraiserFileIdentifier="{xesc(order_data.get("order_id", ""))}" AppraiserAdditionalFileIdentifierName="Other File Number" AppraiserAdditionalFileIdentifier="" AppraisalSoftwareProductName="A-Tech Appraisal Manager" AppraisalSoftwareProductVersionIdentifier="1.0" AppraiserReportSignedDate="" SupervisorReportSignedDate="" AppraisalFormType="{xesc(form_type)}" _TitleDescription="{xesc(title_desc)}" AppraisalFormVersionIdentifier="March 2005" OtherLoanPurposeDescription="" AppraisalPurposeTypeOtherDescription="">')
                                        xml_lines.append(f'    <FORM AppraisalReportContentSequenceIdentifier="1" AppraisalReportContentType="AppraisalForm" AppraisalReportContentName="URAR [UAD Version]" AppraisalReportContentIdentifier="UAD Version 9/2011" AppraisalReportContentIsPrimaryFormIndicator="Y" />')
                                        # Add addendum text if available
                                        combined_addendum = ""
                                        if addendum_text:
                                            combined_addendum += addendum_text
                                        if narrative_text:
                                            if combined_addendum:
                                                combined_addendum += "\n\n"
                                            combined_addendum += narrative_text
                                        if combined_addendum:
                                            xml_lines.append(f'    <FORM AppraisalReportContentSequenceIdentifier="2" AppraisalReportContentType="Addendum" AppraisalReportContentName="Supplemental Addendum" AppraisalReportContentIdentifier="" AppraisalReportContentIsPrimaryFormIndicator="N" _TextDescription="{xesc(combined_addendum)}" />')
                                        xml_lines.append(f'  </REPORT>')

                                        # PARTIES section
                                        xml_lines.append(f'  <PARTIES>')
                                        xml_lines.append(f'    <APPRAISER _Name="{xesc(appraiser_name)}" _CompanyName="A-Tech Appraisal Co., LLC" _StreetAddress="" _City="Warwick" _State="RI" _PostalCode="02886">')
                                        xml_lines.append(f'      <CONTACT_DETAIL>')
                                        xml_lines.append(f'        <CONTACT_POINT _Type="Phone" _Value="" />')
                                        xml_lines.append(f'        <CONTACT_POINT _Type="Email" _Value="" />')
                                        xml_lines.append(f'      </CONTACT_DETAIL>')
                                        xml_lines.append(f'      <APPRAISER_LICENSE _ExpirationDate="" _State="RI" />')
                                        xml_lines.append(f'      <INSPECTION AppraisalInspectionPropertyType="Subject" InspectionDate="{insp_date}" />')
                                        xml_lines.append(f'    </APPRAISER>')
                                        xml_lines.append(f'    <SUPERVISOR _Name="" _CompanyName="" _StreetAddress="" _City="" _State="" _PostalCode="">')
                                        xml_lines.append(f'      <CONTACT_DETAIL>')
                                        xml_lines.append(f'        <CONTACT_POINT _Type="Phone" _Value="" />')
                                        xml_lines.append(f'        <CONTACT_POINT _Type="Email" _Value="" />')
                                        xml_lines.append(f'      </CONTACT_DETAIL>')
                                        xml_lines.append(f'      <APPRAISER_LICENSE _ExpirationDate="" _State="" />')
                                        xml_lines.append(f'      <INSPECTION AppraisalInspectionPropertyType="Comparable" />')
                                        xml_lines.append(f'    </SUPERVISOR>')
                                        xml_lines.append(f'    <REVIEW_APPRAISER />')
                                        xml_lines.append(f'    <REAL_ESTATE_AGENT>')
                                        xml_lines.append(f'      <CONTACT_DETAIL />')
                                        xml_lines.append(f'    </REAL_ESTATE_AGENT>')
                                        xml_lines.append(f'    <LENDER _UnparsedName="{xesc(lender_name)}" AppraisalFormsUnparsedAddress="" _StreetAddress="">')
                                        xml_lines.append(f'      <CONTACT_DETAIL _Name="">')
                                        xml_lines.append(f'        <CONTACT_POINT _Type="Email" _Value="" />')
                                        xml_lines.append(f'      </CONTACT_DETAIL>')
                                        xml_lines.append(f'    </LENDER>')
                                        xml_lines.append(f'    <BORROWER _UnparsedName="{xesc(borrower_name)}">')
                                        xml_lines.append(f'      <BORROWER_EXTENSION>')
                                        xml_lines.append(f'        <BORROWER_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <BORROWER_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <BORROWER_NAME GSEBorrowerName="{xesc(borrower_name)}" />')
                                        xml_lines.append(f'          </BORROWER_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </BORROWER_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </BORROWER_EXTENSION>')
                                        xml_lines.append(f'    </BORROWER>')
                                        xml_lines.append(f'    <MANAGEMENT_COMPANY_EXTENSION>')
                                        xml_lines.append(f'      <MANAGEMENT_COMPANY_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'        <MANAGEMENT_COMPANY_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'          <MANAGEMENT_COMPANY GSEManagementCompanyName="Absolute Value Management" />')
                                        xml_lines.append(f'        </MANAGEMENT_COMPANY_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'      </MANAGEMENT_COMPANY_EXTENSION_SECTION>')
                                        xml_lines.append(f'    </MANAGEMENT_COMPANY_EXTENSION>')
                                        xml_lines.append(f'  </PARTIES>')

                                        # PROPERTY section
                                        xml_lines.append(f'  <PROPERTY _StreetAddress="{xesc(addr)}" _City="{xesc(city)}" _State="{xesc(state)}" _PostalCode="{xesc(zipcode)}" _County="{xesc(county)}" _RightsTypeOtherDescription="">')
                                        xml_lines.append(f'    <_IDENTIFICATION AssessorsParcelIdentifier="{xesc(assessor)}" MapReferenceIdentifier="" CensusTractIdentifier="">')
                                        xml_lines.append(f'      <PROPERTY_IDENTIFICATION_EXTENSION>')
                                        xml_lines.append(f'        <PROPERTY_IDENTIFICATION_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <PROPERTY_IDENTIFICATION_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <PARCEL_IDENTIFIER GSEAssessorsParcelIdentifier="{xesc(assessor)}" />')
                                        xml_lines.append(f'          </PROPERTY_IDENTIFICATION_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </PROPERTY_IDENTIFICATION_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </PROPERTY_IDENTIFICATION_EXTENSION>')
                                        xml_lines.append(f'    </_IDENTIFICATION>')
                                        xml_lines.append(f'    <_LEGAL_DESCRIPTION _Type="Other" _TypeOtherDescription="LongLegal" _TextDescription="{xesc(legal)}" />')
                                        # STRUCTURE
                                        xml_lines.append(f'    <STRUCTURE StoriesCount="{stories}" _DesignDescription="{xesc(design)}" PropertyStructureBuiltYear="{yr}" TotalRoomCount="{tot_rooms}" TotalBedroomCount="{beds}" TotalBathroomCount="{baths}" GrossLivingAreaSquareFeetCount="{gla}">')
                                        xml_lines.append(f'      <FOUNDATION _Type="{found_xml}" _ConditionDescription="{xesc(found_cond)}" _ExistsIndicator="{"Y" if found_type != "Slab" else "N"}">')
                                        xml_lines.append(f'        <_CONDITION _Type="Infestation" _Comment="" />')
                                        xml_lines.append(f'      </FOUNDATION>')
                                        xml_lines.append(f'      <BASEMENT SquareFeetCount="{bsmt_sqft}" _FinishedPercent="{bsmt_fin}" />')
                                        xml_lines.append(f'      <EXTERIOR_FEATURE _Type="Foundation" _Description="{xesc(found_type)}" />')
                                        xml_lines.append(f'      <EXTERIOR_FEATURE _Type="Walls" _Description="{xesc(exterior_walls)}" />')
                                        xml_lines.append(f'      <EXTERIOR_FEATURE _Type="RoofSurface" _Description="{xesc(roof_surface)}" />')
                                        xml_lines.append(f'      <INTERIOR_FEATURE _Type="Floors" _ConditionDescription="{xesc(si.get("flooring", ""))}" />')
                                        xml_lines.append(f'      <INTERIOR_FEATURE _Type="Walls" _ConditionDescription="{xesc(si.get("walls_trim", ""))}" />')
                                        xml_lines.append(f'      <INTERIOR_FEATURE _Type="TrimAndFinish" _ConditionDescription="{xesc(si.get("walls_trim", ""))}" />')
                                        xml_lines.append(f'      <INTERIOR_FEATURE _Type="BathroomFloors" _ConditionDescription="{xesc(si.get("bath_floor", ""))}" />')
                                        xml_lines.append(f'      <INTERIOR_FEATURE _Type="BathroomWainscot" _ConditionDescription="{xesc(si.get("bath_wainscot", ""))}" />')
                                        xml_lines.append(f'      <HEATING _FuelDescription="{xesc(heat)}" />')
                                        xml_lines.append(f'      <COOLING _Description="{xesc(cool)}" />')
                                        xml_lines.append(f'      <KITCHEN_EQUIPMENT _Type="Other" _TypeOtherDescription="{xesc(si.get("kitchen_appliances", ""))}" />')
                                        xml_lines.append(f'      <ATTIC _Description="{xesc(si.get("attic", ""))}" />')
                                        amenities_str = si.get("amenities", "") or ""
                                        has_fp = "Y" if "fireplace" in amenities_str.lower() or "fp" in amenities_str.lower() else "N"
                                        has_pool = "Y" if "pool" in amenities_str.lower() else "N"
                                        xml_lines.append(f'      <AMENITY _Type="WoodStove" _Count="" />')
                                        xml_lines.append(f'      <AMENITY _Type="Fireplace" _ExistsIndicator="{has_fp}" _Count="" />')
                                        xml_lines.append(f'      <AMENITY _Type="Fence" _DetailedDescription="" />')
                                        xml_lines.append(f'      <AMENITY _Type="Patio" _DetailedDescription="" />')
                                        xml_lines.append(f'      <AMENITY _Type="Porch" _DetailedDescription="" />')
                                        xml_lines.append(f'      <AMENITY _Type="Pool" _ExistsIndicator="{has_pool}" _DetailedDescription="" />')
                                        xml_lines.append(f'      <AMENITY _Type="Other" _TypeOtherDescription="{xesc(amenities_str)}" />')
                                        xml_lines.append(f'      <CAR_STORAGE>')
                                        xml_lines.append(f'        <CAR_STORAGE_LOCATION _Type="Driveway" ParkingSpacesCount="" />')
                                        xml_lines.append(f'        <CAR_STORAGE_LOCATION _Type="Garage" ParkingSpacesCount="{garage_spaces}" _AttachmentType="{garage_xml_type}" />')
                                        xml_lines.append(f'        <CAR_STORAGE_LOCATION _Type="Carport" ParkingSpacesCount="" />')
                                        xml_lines.append(f'      </CAR_STORAGE>')
                                        eff_age = eff_age_subj or si.get("effective_age", cost.get("effective_age", ""))
                                        rem_life = si.get("remaining_economic_life", cost.get("remaining_economic_life", ""))
                                        xml_lines.append(f'      <STRUCTURE_ANALYSIS EffectiveAgeYearsCount="{eff_age}">')
                                        xml_lines.append(f'        <STRUCTURE_ANALYSIS_RATING />')
                                        xml_lines.append(f'        <STRUCTURE_ANALYSIS_EXTENSION>')
                                        xml_lines.append(f'          <STRUCTURE_ANALYSIS_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'            <STRUCTURE_ANALYSIS_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'              <EFFECTIVE_AGE GSEEffectiveAgeDescription="{eff_age}" />')
                                        xml_lines.append(f'            </STRUCTURE_ANALYSIS_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'          </STRUCTURE_ANALYSIS_EXTENSION_SECTION>')
                                        xml_lines.append(f'        </STRUCTURE_ANALYSIS_EXTENSION>')
                                        xml_lines.append(f'      </STRUCTURE_ANALYSIS>')
                                        xml_lines.append(f'      <CONDITION_DETAIL_EXTENSION>')
                                        xml_lines.append(f'        <CONDITION_DETAIL_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <CONDITION_DETAIL_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <CONDITION_DETAIL _SequenceIdentifier="1" GSEImprovementAreaType="Kitchen" />')
                                        xml_lines.append(f'            <CONDITION_DETAIL _SequenceIdentifier="2" GSEImprovementAreaType="Bathrooms" />')
                                        xml_lines.append(f'          </CONDITION_DETAIL_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </CONDITION_DETAIL_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </CONDITION_DETAIL_EXTENSION>')
                                        xml_lines.append(f'      <OVERALL_CONDITION_RATING_EXTENSION>')
                                        xml_lines.append(f'        <OVERALL_CONDITION_RATING_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <OVERALL_CONDITION_RATING_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <OVERALL_CONDITION_RATING GSEUpdateLastFifteenYearIndicator="Y" />')
                                        xml_lines.append(f'          </OVERALL_CONDITION_RATING_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </OVERALL_CONDITION_RATING_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </OVERALL_CONDITION_RATING_EXTENSION>')
                                        xml_lines.append(f'      <STRUCTURE_EXTENSION>')
                                        xml_lines.append(f'        <STRUCTURE_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <STRUCTURE_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <STRUCTURE_INFORMATION GSEYearBuiltEstimationIndicator="N" GSEStoriesCount="{stories}" />')
                                        xml_lines.append(f'          </STRUCTURE_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </STRUCTURE_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </STRUCTURE_EXTENSION>')
                                        xml_lines.append(f'    </STRUCTURE>')
                                        # OFF_SITE_IMPROVEMENTS
                                        xml_lines.append(f'    <_OFF_SITE_IMPROVEMENT _Type="Street" _Description="" _OwnershipType="Public" _ExistsIndicator="N" />')
                                        xml_lines.append(f'    <_OFF_SITE_IMPROVEMENT _Type="Street" _Description="" _OwnershipType="Private" _ExistsIndicator="N" />')
                                        xml_lines.append(f'    <_OFF_SITE_IMPROVEMENT _Type="Alley" _Description="" _OwnershipType="Public" _ExistsIndicator="N" />')
                                        xml_lines.append(f'    <_OFF_SITE_IMPROVEMENT _Type="Alley" _Description="" _OwnershipType="Private" _ExistsIndicator="N" />')
                                        # SITE
                                        s_zoning_desc = sd.get("zoning_description", "Single Family Residential")
                                        s_zoning_comply = sd.get("zoning_compliance", "Legal conforming")
                                        s_hbu = sd.get("highest_best_use", "Present use as improved")
                                        s_shape = sd.get("shape", "")
                                        s_view = sd.get("view", "")
                                        s_topo = sd.get("topography", "Level")
                                        s_elec = "Y" if sd.get("utilities_electric", "").lower() == "public" else "N"
                                        s_gas = "Y" if sd.get("utilities_gas", "").lower() == "public" else "N"
                                        s_water = "Y" if sd.get("utilities_water", "").lower() == "public" else "N"
                                        s_sewer = "Y" if sd.get("utilities_sewer", "").lower() == "public" else "N"
                                        s_fema_date = sd.get("fema_map_date", "")
                                        xml_lines.append(f'    <SITE _DimensionsDescription="{xesc(lot_dims)}" _AreaDescription="{xesc(lot_area)}" _ZoningClassificationIdentifier="{xesc(zoning)}" _ZoningClassificationDescription="{xesc(s_zoning_desc)}" _ZoningComplianceDescription="{xesc(s_zoning_comply)}" HighestBestUseDescription="{xesc(s_hbu)}" _HighestAndBestUseCurrentDescription="{xesc(sd.get("highest_best_use", ""))}">')
                                        xml_lines.append(f'      <SITE_FEATURE _Type="Shape" _Comment="{xesc(s_shape)}" />')
                                        xml_lines.append(f'      <SITE_FEATURE _Type="View" _Comment="{xesc(s_view)}" />')
                                        xml_lines.append(f'      <SITE_FEATURE _Type="Driveway" _Comment="{xesc(sd.get("driveway", ""))}" />')
                                        xml_lines.append(f'      <SITE_FEATURE _Type="Topography" _Comment="{xesc(s_topo)}" />')
                                        xml_lines.append(f'      <SITE_FEATURE _Type="Drainage" _Comment="{xesc(sd.get("drainage", "Adequate"))}" />')
                                        xml_lines.append(f'      <FLOOD_ZONE NFIPFloodZoneIdentifier="{flood_z}" NFIPMapIdentifier="{flood_map}" NFIPMapPanelDate="{s_fema_date}">')
                                        xml_lines.append(f'        <FLOOD_ZONE_EXTENSION>')
                                        xml_lines.append(f'          <FLOOD_ZONE_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'            <FLOOD_ZONE_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'              <FLOOD_ZONE_INFORMATION GSENFIPFloodZoneIdentifier="{flood_z}" GSEFEMAFloodMapIdentifier="{flood_map}" />')
                                        xml_lines.append(f'            </FLOOD_ZONE_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'          </FLOOD_ZONE_EXTENSION_SECTION>')
                                        xml_lines.append(f'        </FLOOD_ZONE_EXTENSION>')
                                        xml_lines.append(f'      </FLOOD_ZONE>')
                                        xml_lines.append(f'      <SITE_UTILITY _Type="Electricity" _PublicIndicator="{s_elec}" _NonPublicIndicator="{"N" if s_elec == "Y" else "Y"}" _NonPublicDescription="" />')
                                        xml_lines.append(f'      <SITE_UTILITY _Type="Gas" _PublicIndicator="{s_gas}" _NonPublicIndicator="{"N" if s_gas == "Y" else "Y"}" _NonPublicDescription="" />')
                                        xml_lines.append(f'      <SITE_UTILITY _Type="Water" _PublicIndicator="{s_water}" _NonPublicIndicator="{"N" if s_water == "Y" else "Y"}" _NonPublicDescription="" />')
                                        xml_lines.append(f'      <SITE_UTILITY _Type="SanitarySewer" _PublicIndicator="{s_sewer}" _NonPublicIndicator="{"N" if s_sewer == "Y" else "Y"}" _NonPublicDescription="" />')
                                        xml_lines.append(f'    </SITE>')
                                        # PROJECT
                                        xml_lines.append(f'    <PROJECT _Name="" _ConversionDate="" _ContainsMultipleDwellingUnitsDataSourceDescription="" _CommonElementsStatusDescription="" _CommonElementsLeaseTermsDescription="" _CommonElementsDescription="">')
                                        xml_lines.append(f'      <DEVELOPMENT_STAGE _TotalPhasesCount="" CompletedUnitsCount="" PlannedUnitsCount="" UnitsSoldCount="" UnitsRentedCount="" UnitsForSaleCount="" DataSourceDescription="" />')
                                        xml_lines.append(f'      <_PER_UNIT_FEE _Amount="" />')
                                        xml_lines.append(f'    </PROJECT>')
                                        # NEIGHBORHOOD
                                        nb_name = nb.get("name", neighborhood) or neighborhood
                                        nb_bounds = nb.get("boundaries", "")
                                        nb_desc = nb.get("description", "")
                                        nb_market = nb.get("market_conditions", "")
                                        nb_factors = nb.get("neighborhood_factors", "")
                                        nb_full_desc = nb_desc
                                        if nb_factors:
                                            nb_full_desc += " " + nb_factors
                                        xml_lines.append(f'    <NEIGHBORHOOD _Name="{xesc(nb_name)}" _BoundaryAndCharacteristicsDescription="{xesc(nb_bounds)}" _Description="{xesc(nb_full_desc)}" _MarketConditionsDescription="{xesc(nb_market)}" _BuiltupRangeType="{xesc(nb.get("built_up", "Over 75%"))}" _GrowthPaceType="{xesc(nb.get("growth_rate", "Stable"))}" _PropertyValueTrendType="{xesc(nb.get("property_values", "Stable"))}" _DemandSupplyType="{xesc(nb.get("demand_supply", "In Balance"))}" _TypicalMarketingTimeDurationType="{xesc(nb.get("marketing_time", "3-6 Months"))}">')
                                        xml_lines.append(f'      <_HOUSING _Type="SingleFamily" _LowPriceAmount="{xesc(nb.get("price_low", ""))}" _HighPriceAmount="{xesc(nb.get("price_high", ""))}" _PredominantPriceAmount="{xesc(nb.get("price_predominant", ""))}" _OldestYearsCount="{xesc(nb.get("age_high", ""))}" _NewestYearsCount="{xesc(nb.get("age_low", ""))}" _PredominantAgeYearsCount="{xesc(nb.get("age_predominant", ""))}" />')
                                        xml_lines.append(f'      <_PRESENT_LAND_USE _Type="SingleFamily" _Percent="{xesc(nb.get("land_use_sf_pct", ""))}" />')
                                        xml_lines.append(f'      <_PRESENT_LAND_USE _Type="TwoToFourFamily" _Percent="{xesc(nb.get("land_use_24_pct", ""))}" />')
                                        xml_lines.append(f'      <_PRESENT_LAND_USE _Type="Apartment" _Percent="{xesc(nb.get("land_use_apt_pct", ""))}" />')
                                        xml_lines.append(f'      <_PRESENT_LAND_USE _Type="Commercial" _Percent="{xesc(nb.get("land_use_comm_pct", ""))}" />')
                                        xml_lines.append(f'      <_PRESENT_LAND_USE _Type="Other" _TypeOtherDescription="Other" _Percent="{xesc(nb.get("land_use_other_pct", ""))}" />')
                                        xml_lines.append(f'      <NEIGHBORHOOD_EXTENSION>')
                                        xml_lines.append(f'        <NEIGHBORHOOD_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <NEIGHBORHOOD_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <NEIGHBORHOOD_BOUNDARIES GSENeighborhoodBoundariesDescription="{xesc(nb_bounds)}" />')
                                        xml_lines.append(f'          </NEIGHBORHOOD_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </NEIGHBORHOOD_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </NEIGHBORHOOD_EXTENSION>')
                                        xml_lines.append(f'    </NEIGHBORHOOD>')
                                        # TAX
                                        xml_lines.append(f'    <_TAX _YearIdentifier="{tax_yr}" _TotalTaxAmount="{tax_amt}" _TotalSpecialTaxAmount="">')
                                        xml_lines.append(f'      <PROPERTY_TAX_EXTENSION>')
                                        xml_lines.append(f'        <PROPERTY_TAX_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <PROPERTY_TAX_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <PROPERTY_TAX_AMOUNT GSEPropertyTaxTotalTaxAmount="{tax_amt}" />')
                                        xml_lines.append(f'          </PROPERTY_TAX_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </PROPERTY_TAX_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </PROPERTY_TAX_EXTENSION>')
                                        xml_lines.append(f'    </_TAX>')
                                        xml_lines.append(f'    <LISTING_HISTORY ListedWithinPreviousYearDescription="" />')
                                        # PROPERTY_ANALYSIS entries
                                        xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="AdditionalFeatures" _Comment="{xesc(comments.get("additional_features", ""))}" />')
                                        xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="QualityAndAppearance" _Comment="{xesc(comments.get("quality_comment", ""))}" />')
                                        xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="PhysicalDeficiency" _Comment="{xesc(comments.get("condition_comment", ""))}" />')
                                        xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="ConformsToNeighborhood" _Comment="{xesc(comments.get("conforms_to_neighborhood", ""))}" />')
                                        xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="UtilitiesAndOffSiteImprovementsConformToNeighborhood" _Comment="{xesc(comments.get("conforms_to_neighborhood", ""))}" />')
                                        xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="AdverseSiteConditions" _Comment="{xesc(comments.get("adverse_conditions", ""))}" />')
                                        xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="PropertyCondition" _Comment="{xesc(comments.get("condition_comment", ""))}" />')
                                        # OWNER
                                        xml_lines.append(f'    <_OWNER _Name="">')
                                        xml_lines.append(f'      <CONTACT_DETAIL />')
                                        xml_lines.append(f'      <PROPERTY_OWNER_EXTENSION>')
                                        xml_lines.append(f'        <PROPERTY_OWNER_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <PROPERTY_OWNER_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <PROPERTY_OWNER GSEPropertyOwnerName="" />')
                                        xml_lines.append(f'          </PROPERTY_OWNER_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </PROPERTY_OWNER_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </PROPERTY_OWNER_EXTENSION>')
                                        xml_lines.append(f'    </_OWNER>')
                                        # SALES_CONTRACT
                                        xml_lines.append(f'    <SALES_CONTRACT _ReviewComment="" _Amount="" _Date="" DataSourceDescription="" SalesConcessionAmount="" SalesConcessionDescription="">')
                                        xml_lines.append(f'      <SALES_CONCESSION_EXTENSION>')
                                        xml_lines.append(f'        <SALES_CONCESSION_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <SALES_CONCESSION_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <SALES_CONCESSION GSEUndefinedConcessionAmountIndicator="N" />')
                                        xml_lines.append(f'          </SALES_CONCESSION_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </SALES_CONCESSION_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </SALES_CONCESSION_EXTENSION>')
                                        xml_lines.append(f'    </SALES_CONTRACT>')
                                        # PROPERTY_EXTENSION
                                        xml_lines.append(f'    <PROPERTY_EXTENSION>')
                                        xml_lines.append(f'      <PROPERTY_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'        <PROPERTY_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'          <PROPERTY_TYPE GSE_PUDIndicator="N" />')
                                        xml_lines.append(f'        </PROPERTY_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'      </PROPERTY_EXTENSION_SECTION>')
                                        xml_lines.append(f'    </PROPERTY_EXTENSION>')
                                        xml_lines.append(f'  </PROPERTY>')

                                        # VALUATION_METHODS section
                                        xml_lines.append(f'  <VALUATION_METHODS _AdditionalDescription="">')
                                        xml_lines.append(f'    <COST_ANALYSIS SiteEstimatedValueComment="" DataSourceDescription="" CostServiceQualityRatingDescription="" DataSourceEffectiveDate="" _Comment="{xesc(comments.get("cost_comment", ""))}" EstimatedRemainingEconomicLifeYearsCount="{xesc(cost.get("remaining_economic_life", ""))}" SiteEstimatedValueAmount="{xesc(cost.get("site_value", ""))}" NewImprovementTotalCostAmount="{xesc(cost.get("total_new_cost", ""))}" NewImprovementDepreciatedCostAmount="{xesc(cost.get("depreciated_cost", ""))}" SiteOtherImprovementsAsIsAmount="{xesc(cost.get("site_improvements", ""))}" ValueIndicatedByCostApproachAmount="{xesc(cost.get("indicated_value", ""))}">')
                                        xml_lines.append(f'      <NEW_IMPROVEMENT _Type="Dwelling" SquareFeetCount="{xesc(cost.get("dwelling_sqft", gla))}" PricePerSquareFootAmount="{xesc(cost.get("dwelling_cost_per_sqft", ""))}" _CostAmount="{xesc(cost.get("dwelling_cost", ""))}" />')
                                        xml_lines.append(f'      <NEW_IMPROVEMENT _Type="Other" _TypeOtherDescription="" SquareFeetCount="" PricePerSquareFootAmount="" _CostAmount="" />')
                                        xml_lines.append(f'      <NEW_IMPROVEMENT _Type="Additional" _SequenceIdentifier="1" _CostDescription="" _CostAmount="" />')
                                        xml_lines.append(f'      <NEW_IMPROVEMENT _Type="Garage" SquareFeetCount="{xesc(cost.get("garage_sqft", ""))}" PricePerSquareFootAmount="{xesc(cost.get("garage_cost_per_sqft", ""))}" _CostAmount="{xesc(cost.get("garage_cost", ""))}" />')
                                        xml_lines.append(f'      <DEPRECIATION _PhysicalPercent="{xesc(cost.get("physical_depreciation_pct", ""))}" _PhysicalAmount="{xesc(cost.get("physical_depreciation_amt", ""))}" _FunctionalPercent="" _FunctionalAmount="{xesc(cost.get("functional_depreciation_amt", ""))}" _ExteriorPercent="" _ExteriorAmount="{xesc(cost.get("external_depreciation_amt", ""))}" _TotalAmount="{xesc(cost.get("total_depreciation", ""))}" />')
                                        xml_lines.append(f'      <COST_ANALYSIS_EXTENSION>')
                                        xml_lines.append(f'        <COST_ANALYSIS_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'          <COST_ANALYSIS_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            <COST_APPROACH_DATA_SOURCE GSECostDataSourceEffectiveDateDescription="" />')
                                        xml_lines.append(f'          </COST_ANALYSIS_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'        </COST_ANALYSIS_EXTENSION_SECTION>')
                                        xml_lines.append(f'      </COST_ANALYSIS_EXTENSION>')
                                        xml_lines.append(f'    </COST_ANALYSIS>')
                                        # SALES_COMPARISON with subject as COMPARABLE_SALE 0
                                        xml_lines.append(f'    <SALES_COMPARISON _CurrentSalesAgreementAnalysisComment="" _Comment="{xesc(comments.get("sales_comparison_comment", ""))}" ValueIndicatedBySalesComparisonApproachAmount="{val_opinion}">')
                                        xml_lines.append(f'      <RESEARCH ComparableListingsResearchedCount="" ComparableListingsPriceRangeLowAmount="" ComparableListingsPriceRangeHighAmount="" ComparableSalesResearchedCount="" ComparableSalesPriceRangeLowAmount="" ComparableSalesPriceRangeHighAmount="" SalesHistoryNotResearchedComment="">')
                                        xml_lines.append(f'        <SUBJECT DataSourceDescription="" />')
                                        xml_lines.append(f'        <COMPARABLE DataSourceDescription="" />')
                                        xml_lines.append(f'      </RESEARCH>')
                                        xml_lines.append(f'      <COMPARABLE_SALE PropertySequenceIdentifier="0" PropertySalesAmount="" SalesPricePerGrossLivingAreaAmount="">')
                                        xml_lines.append(f'        <LOCATION LatitudeNumber="" LongitudeNumber="" PropertyStreetAddress="{xesc(addr)}" PropertyStreetAddress2="{xesc(city)}, {xesc(state)} {xesc(zipcode)}" />')
                                        xml_lines.append(f'        <ROOM_ADJUSTMENT TotalRoomCount="{tot_rooms}" TotalBedroomCount="{beds}" TotalBathroomCount="{baths}" />')
                                        subj_garage_desc = f'{garage_xml_type} {garage_spaces}' if garage_spaces else garage
                                        subj_heat_cool = heat
                                        if cool and cool != heat:
                                            subj_heat_cool = f'{heat}/{cool}'
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Location" _Description="{xesc(nb.get("name", neighborhood) or neighborhood)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PropertyRights" _Description="Fee Simple" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="SiteArea" _Description="{xesc(lot_area)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="View" _Description="{xesc(view_desc)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="DesignStyle" _Description="{xesc(si.get("design_style", design))}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Quality" _Description="{xesc(qual)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Age" _Description="{xesc(yr)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Condition" _Description="{xesc(cond)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="GrossLivingArea" _Description="{xesc(gla)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementArea" _Description="{xesc(bsmt_sqft)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementFinish" _Description="{xesc(bsmt_fin)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="FunctionalUtility" _Description="{xesc(si.get("functional_utility", ""))}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="HeatingCooling" _Description="{xesc(subj_heat_cool)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="EnergyEfficient" _Description="{xesc(si.get("energy_efficiency", ""))}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="CarStorage" _Description="{xesc(subj_garage_desc)}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PorchDeck" _Description="{xesc(si.get("porch_patio_deck", ""))}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Other" _TypeOtherDescription="Fireplace" _Description="{xesc(si.get("fireplace", ""))}" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Other" _TypeOtherDescription="" _Description="" />')
                                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Other" _TypeOtherDescription="" _Description="" />')
                                        xml_lines.append(f'        <PRIOR_SALES PropertySalesDate="" PropertySalesAmount="" DataSourceDescription="" DataSourceEffectiveDate="">')
                                        xml_lines.append(f'          <PRIOR_SALES_EXTENSION>')
                                        xml_lines.append(f'            <PRIOR_SALES_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'              <PRIOR_SALES_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'                <PRIOR_SALE GSEPriorSaleDate="" GSEPriorSaleComment="" />')
                                        xml_lines.append(f'              </PRIOR_SALES_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'            </PRIOR_SALES_EXTENSION_SECTION>')
                                        xml_lines.append(f'          </PRIOR_SALES_EXTENSION>')
                                        xml_lines.append(f'        </PRIOR_SALES>')
                                        xml_lines.append(f'        <COMPARISON_DETAIL_EXTENSION>')
                                        xml_lines.append(f'          <COMPARISON_DETAIL_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                        xml_lines.append(f'            <COMPARISON_DETAIL_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'              <COMPARISON_DETAIL GSEDaysOnMarketDescription="" GSEAgeEstimationIndicator="N" GSEBelowGradeTotalSquareFeetNumber="" />')
                                        xml_lines.append(f'            </COMPARISON_DETAIL_EXTENSION_SECTION_DATA>')
                                        xml_lines.append(f'          </COMPARISON_DETAIL_EXTENSION_SECTION>')
                                        xml_lines.append(f'        </COMPARISON_DETAIL_EXTENSION>')
                                        xml_lines.append(f'      </COMPARABLE_SALE>')
                                        # Add AI-generated comparable sales (1, 2, 3)
                                        for ci, comp in enumerate(comps[:3], start=1):
                                            c_addr = comp.get("address", "")
                                            c_city = comp.get("city", city)
                                            c_state = comp.get("state", state)
                                            c_zip = comp.get("zip", zipcode)
                                            c_price = comp.get("sale_price", "")
                                            c_gla = comp.get("gla", "")
                                            c_price_gla = ""
                                            try:
                                                if c_price and c_gla:
                                                    c_price_gla = str(round(int(c_price) / int(c_gla)))
                                            except:
                                                pass
                                            xml_lines.append(f'      <COMPARABLE_SALE PropertySequenceIdentifier="{ci}" PropertySalesAmount="{c_price}" SalesPricePerGrossLivingAreaAmount="{c_price_gla}">')
                                            xml_lines.append(f'        <LOCATION LatitudeNumber="" LongitudeNumber="" PropertyStreetAddress="{xesc(c_addr)}" PropertyStreetAddress2="{xesc(c_city)}, {xesc(c_state)} {xesc(c_zip)}" />')
                                            xml_lines.append(f'        <ROOM_ADJUSTMENT TotalRoomCount="{xesc(comp.get("total_rooms", ""))}" TotalBedroomCount="{xesc(comp.get("bedrooms", ""))}" TotalBathroomCount="{xesc(comp.get("bathrooms", ""))}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="SaleOrFinancingConcessions" _Description="{xesc(comp.get("financing_type", "Conv;0"))}" _Amount="{comp.get("financing_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Concessions" _Description="{xesc(comp.get("concessions", "0"))}" _Amount="{comp.get("concessions_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Location" _Description="{xesc(comp.get("location", ""))}" _Amount="{comp.get("location_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PropertyRights" _Description="{xesc(comp.get("property_rights", "Fee Simple"))}" _Amount="{comp.get("lease_fee_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="SiteArea" _Description="{xesc(comp.get("lot_size", ""))}" _Amount="{comp.get("site_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="View" _Description="{xesc(comp.get("view", ""))}" _Amount="{comp.get("view_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="DesignStyle" _Description="{xesc(comp.get("design_style", ""))}" _Amount="{comp.get("design_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Quality" _Description="{xesc(comp.get("quality", ""))}" _Amount="{comp.get("quality_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Age" _Description="{xesc(comp.get("year_built", ""))}" _Amount="{comp.get("age_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Condition" _Description="{xesc(comp.get("condition", ""))}" _Amount="{comp.get("condition_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="GrossLivingArea" _Description="{xesc(c_gla)}" _Amount="{comp.get("gla_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementArea" _Description="{xesc(comp.get("basement_total_sqft", ""))}" _Amount="{comp.get("basement_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementFinish" _Description="{xesc(comp.get("basement_finished_sqft", ""))}" _Amount="0" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="FunctionalUtility" _Description="{xesc(comp.get("functional_utility", ""))}" _Amount="{comp.get("functional_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="HeatingCooling" _Description="{xesc(comp.get("heating_cooling", ""))}" _Amount="{comp.get("heating_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="EnergyEfficient" _Description="{xesc(comp.get("energy_efficiency", ""))}" _Amount="{comp.get("energy_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="CarStorage" _Description="{xesc(comp.get("garage_parking", ""))}" _Amount="{comp.get("garage_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PorchDeck" _Description="{xesc(comp.get("porch_patio_deck", ""))}" _Amount="{comp.get("porch_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Other" _TypeOtherDescription="Fireplace" _Description="{xesc(comp.get("fireplace", ""))}" _Amount="{comp.get("fireplace_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Other" _TypeOtherDescription="Pool" _Description="{xesc(comp.get("pool", ""))}" _Amount="{comp.get("pool_adj", "0")}" />')
                                            xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Other" _TypeOtherDescription="Fence" _Description="{xesc(comp.get("fence", ""))}" _Amount="{comp.get("fence_adj", "0")}" />')
                                            c_prior_date = comp.get("prior_sale_date", "")
                                            c_prior_price = comp.get("prior_sale_price", "")
                                            xml_lines.append(f'        <PRIOR_SALES PropertySalesDate="{c_prior_date}" PropertySalesAmount="{c_prior_price}" DataSourceDescription="{xesc(comp.get("data_source", ""))};{xesc(comp.get("verification_source", ""))}" DataSourceEffectiveDate="">')
                                            xml_lines.append(f'          <PRIOR_SALES_EXTENSION>')
                                            xml_lines.append(f'            <PRIOR_SALES_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                            xml_lines.append(f'              <PRIOR_SALES_EXTENSION_SECTION_DATA>')
                                            xml_lines.append(f'                <PRIOR_SALE GSEPriorSaleDate="{c_prior_date}" GSEPriorSaleComment="" />')
                                            xml_lines.append(f'              </PRIOR_SALES_EXTENSION_SECTION_DATA>')
                                            xml_lines.append(f'            </PRIOR_SALES_EXTENSION_SECTION>')
                                            xml_lines.append(f'          </PRIOR_SALES_EXTENSION>')
                                            xml_lines.append(f'        </PRIOR_SALES>')
                                            xml_lines.append(f'        <COMPARISON_DETAIL_EXTENSION>')
                                            xml_lines.append(f'          <COMPARISON_DETAIL_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                                            xml_lines.append(f'            <COMPARISON_DETAIL_EXTENSION_SECTION_DATA>')
                                            xml_lines.append(f'              <COMPARISON_DETAIL GSEDaysOnMarketDescription="" GSEAgeEstimationIndicator="N" GSEBelowGradeTotalSquareFeetNumber="" />')
                                            xml_lines.append(f'            </COMPARISON_DETAIL_EXTENSION_SECTION_DATA>')
                                            xml_lines.append(f'          </COMPARISON_DETAIL_EXTENSION_SECTION>')
                                            xml_lines.append(f'        </COMPARISON_DETAIL_EXTENSION>')
                                            xml_lines.append(f'      </COMPARABLE_SALE>')
                                        xml_lines.append(f'    </SALES_COMPARISON>')
                                        xml_lines.append(f'    <INCOME_ANALYSIS ValueIndicatedByIncomeApproachAmount="" EstimatedMarketMonthlyRentAmount="" GrossRentMultiplierFactor="" _Comment="" />')
                                        xml_lines.append(f'  </VALUATION_METHODS>')

                                        # VALUATION section
                                        final_val = val_summary.get("final_opinion_value", "") or val_summary.get("indicated_value", "") or val_opinion
                                        eff_date = val_summary.get("effective_date", insp_date) or insp_date
                                        xml_lines.append(f'  <VALUATION PropertyAppraisedValueAmount="{final_val}" AppraisalEffectiveDate="{eff_date}">')
                                        xml_lines.append(f'    <_RECONCILIATION _SummaryComment="{xesc(comments.get("reconciliation", ""))}" _ConditionsComment="{xesc(comments.get("conditions_comment", ""))}" />')
                                        xml_lines.append(f'  </VALUATION>')

                                        xml_lines.append(f'</VALUATION_RESPONSE>')

                                        xml_str = '\n'.join(xml_lines)
                                        st.download_button("Download UAD XML", data=xml_str,
                                            file_name=f"{order_data['order_id']}_UAD.xml",
                                            mime="application/xml")

        else:
            st.info("No orders found. Create an order first.")

# ====================== TAB 5_TOOLS: TOOLS & CALCULATORS ======================
with tab5_tools:
    st.markdown("---")
    st.markdown("#### External Tools")
    ext_col1, ext_col2 = st.columns(2)
    with ext_col1:
        st.markdown('''
        <div style="background: white; border-radius: 12px; padding: 1.5rem; border: 1px solid #e5e5e5; text-align: center;">
            <h4 style="margin: 0 0 0.5rem 0;">📐 CubiCasa</h4>
            <p style="color: #666; font-size: 0.85rem; margin-bottom: 1rem;">AI-powered floor plans from your phone. Scan a property in minutes and get a professional floor plan with accurate measurements.</p>
        </div>
        ''', unsafe_allow_html=True)
        st.link_button("Open CubiCasa App", "https://www.cubi.casa", use_container_width=True)
    with ext_col2:
        st.markdown('''
        <div style="background: white; border-radius: 12px; padding: 1.5rem; border: 1px solid #e5e5e5; text-align: center;">
            <h4 style="margin: 0 0 0.5rem 0;">📈 STR Report Generator</h4>
            <p style="color: #666; font-size: 0.85rem; margin-bottom: 1rem;">Generate AirDNA-powered short-term rental income analysis reports for appraisal work.</p>
        </div>
        ''', unsafe_allow_html=True)
        st.link_button("Open STR Generator", "https://avm-str-generator.onrender.com", use_container_width=True)
    st.markdown("---")

    st.markdown("### Appraiser Toolkit")

    tool = st.selectbox("Select Tool", [
        "GLA Calculator", "Adjustment Calculator", "GRM Calculator",
        "Cost Approach Calculator", "Net/Gross Adjustment Analyzer"
    ], key="tool_select")

    st.divider()

    if tool == "GLA Calculator":
        st.markdown("**Gross Living Area Calculator**")
        st.caption("Enter dimensions for each floor level")
        total_gla = 0
        for i in range(1, 5):
            with st.expander(f"Level {i}", expanded=(i == 1)):
                gc1, gc2, gc3 = st.columns(3)
                with gc1:
                    length = st.number_input(f"Length (ft)", value=0.0, step=1.0, key=f"gla_l{i}")
                with gc2:
                    width = st.number_input(f"Width (ft)", value=0.0, step=1.0, key=f"gla_w{i}")
                with gc3:
                    area = length * width
                    st.metric(f"Area", f"{area:,.0f} sqft")
                total_gla += area
        st.success(f"**Total GLA: {total_gla:,.0f} square feet**")

    elif tool == "Adjustment Calculator":
        st.markdown("**Comparable Adjustment Calculator**")
        preset = st.selectbox("Preset Rates", [
            "Custom", "GLA ($50/sqft)", "GLA ($65/sqft)", "GLA ($75/sqft)",
            "Bedroom ($7,500)", "Bedroom ($10,000)", "Bathroom ($10,000)",
            "Bathroom ($15,000)", "Garage ($15,000)", "Garage ($20,000)",
            "Fireplace ($4,000)", "Pool ($15,000)", "Age ($1,000/year)"
        ])
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            subj_val = st.number_input("Subject Value", value=0.0, step=1.0, key="adj_subj")
        with ac2:
            comp_val = st.number_input("Comp Value", value=0.0, step=1.0, key="adj_comp")
        with ac3:
            rate_defaults = {"Custom": 0, "GLA ($50/sqft)": 50, "GLA ($65/sqft)": 65, "GLA ($75/sqft)": 75,
                "Bedroom ($7,500)": 7500, "Bedroom ($10,000)": 10000, "Bathroom ($10,000)": 10000,
                "Bathroom ($15,000)": 15000, "Garage ($15,000)": 15000, "Garage ($20,000)": 20000,
                "Fireplace ($4,000)": 4000, "Pool ($15,000)": 15000, "Age ($1,000/year)": 1000}
            rate = st.number_input("Rate per unit ($)", value=float(rate_defaults.get(preset, 0)), step=1.0, key="adj_rate")
        diff = subj_val - comp_val
        adjustment = diff * rate if "GLA" in preset or "Age" in preset else diff * rate if rate != 0 else 0
        if "GLA" in preset or "Age" in preset:
            adjustment = diff * rate
        else:
            adjustment = diff * rate if diff != 0 and rate != 0 else (subj_val - comp_val) * (1 if rate == 0 else rate)
        if preset != "Custom" and "GLA" not in preset and "Age" not in preset:
            direction = 1 if subj_val > comp_val else (-1 if subj_val < comp_val else 0)
            adjustment = rate * direction
        else:
            adjustment = diff * rate
        st.metric("Adjustment Amount", f"${adjustment:,.0f}")
        if adjustment > 0:
            st.info("Positive adjustment — comp is inferior to subject")
        elif adjustment < 0:
            st.info("Negative adjustment — comp is superior to subject")

    elif tool == "GRM Calculator":
        st.markdown("**Gross Rent Multiplier Calculator**")
        grm_mode = st.radio("Mode", ["Calculate GRM", "Calculate Value from GRM"], horizontal=True, key="grm_mode")
        if grm_mode == "Calculate GRM":
            gc1, gc2 = st.columns(2)
            with gc1:
                sale_price = st.number_input("Sale Price ($)", value=0.0, step=1000.0, key="grm_sp")
            with gc2:
                monthly_rent = st.number_input("Monthly Rent ($)", value=0.0, step=50.0, key="grm_rent")
            if monthly_rent > 0:
                grm = sale_price / monthly_rent
                st.success(f"**GRM: {grm:.1f}**")
                st.caption(f"Annual GRM: {sale_price / (monthly_rent * 12):.2f}")
        else:
            gc1, gc2 = st.columns(2)
            with gc1:
                grm_val = st.number_input("GRM", value=0.0, step=0.5, key="grm_v")
            with gc2:
                rent_val = st.number_input("Monthly Rent ($)", value=0.0, step=50.0, key="grm_r2")
            if grm_val > 0 and rent_val > 0:
                indicated = grm_val * rent_val
                st.success(f"**Indicated Value: ${indicated:,.0f}**")

    elif tool == "Cost Approach Calculator":
        st.markdown("**Cost Approach Calculator**")
        cc1, cc2 = st.columns(2)
        with cc1:
            ca_gla = st.number_input("GLA (sqft)", value=0.0, step=10.0, key="ca_gla")
            ca_cost = st.number_input("Cost per sqft ($)", value=0.0, step=5.0, key="ca_cost")
            ca_site = st.number_input("Site Value ($)", value=0.0, step=1000.0, key="ca_site")
        with cc2:
            ca_eff_age = st.number_input("Effective Age (years)", value=0, step=1, key="ca_age")
            ca_econ_life = st.number_input("Total Economic Life (years)", value=60, step=5, key="ca_life")
            ca_site_imp = st.number_input("Site Improvements ($)", value=0.0, step=500.0, key="ca_si")
        if ca_gla > 0 and ca_cost > 0:
            rcn = ca_gla * ca_cost
            depr_pct = (ca_eff_age / ca_econ_life * 100) if ca_econ_life > 0 else 0
            depr_amt = rcn * (depr_pct / 100)
            depreciated = rcn - depr_amt
            indicated = depreciated + ca_site + ca_site_imp
            st.divider()
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Replacement Cost New", f"${rcn:,.0f}")
            mc2.metric("Depreciation", f"${depr_amt:,.0f} ({depr_pct:.1f}%)")
            mc3.metric("Depreciated Cost", f"${depreciated:,.0f}")
            mc4.metric("Indicated Value", f"${indicated:,.0f}")

    elif tool == "Net/Gross Adjustment Analyzer":
        st.markdown("**Net & Gross Adjustment Analyzer**")
        sale_price = st.number_input("Comp Sale Price ($)", value=0.0, step=1000.0, key="adj_sp")
        st.caption("Enter adjustments (positive = comp inferior, negative = comp superior)")
        adj_labels = ["Location", "Site", "View", "Design", "Quality", "Age", "Condition", "GLA", "Basement", "Garage", "Other"]
        adjs = []
        acols = st.columns(4)
        for i, lbl in enumerate(adj_labels):
            with acols[i % 4]:
                val = st.number_input(lbl, value=0.0, step=500.0, key=f"ana_{lbl}")
                adjs.append(val)
        if sale_price > 0:
            net = sum(adjs)
            gross = sum(abs(a) for a in adjs)
            net_pct = abs(net) / sale_price * 100
            gross_pct = gross / sale_price * 100
            adj_price = sale_price + net
            st.divider()
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Net Adjustment", f"${net:,.0f}")
            rc2.metric("Net %", f"{net_pct:.1f}%")
            rc3.metric("Gross %", f"{gross_pct:.1f}%")
            rc4.metric("Adjusted Price", f"${adj_price:,.0f}")
            if net_pct > 15:
                st.warning("Net adjustments exceed 15% UAD threshold")
            if gross_pct > 25:
                st.warning("Gross adjustments exceed 25% UAD threshold")
            if net_pct <= 15 and gross_pct <= 25:
                st.success("Adjustments within UAD guidelines")

# ====================== TAB 6_STR: STR REPORTS ======================
with tab6_str:
    if not has_feature("str_reports"):
        st.warning("🔒 STR Reports require Enterprise plan")
        st.info("Upgrade to Enterprise to unlock short-term rental analysis")
    else:
        st.markdown("### Short-Term Rental (STR) Analysis")
        st.markdown("Generate AirDNA-powered income analysis reports for STR properties")

        with st.form("str_form"):
            st.markdown("#### Property Details")
            str_address = st.text_input("Property Address", placeholder="123 Beach St")
            str_bedrooms = st.number_input("Bedrooms", min_value=1, value=3)
            str_bathrooms = st.number_input("Bathrooms", min_value=1, value=2)

            st.markdown("#### Market Data")
            str_market = st.selectbox("Market/City",
                ["Miami, FL", "Las Vegas, NV", "New York, NY", "Los Angeles, CA", "Denver, CO"])
            str_occupancy = st.slider("Estimated Occupancy Rate (%)", 0, 100, 70)
            str_avg_rate = st.number_input("Average Nightly Rate ($)", min_value=0, value=250)

            str_submit = st.form_submit_button("📈 Generate STR Report")
            if str_submit:
                st.info("STR Report generation would use AirDNA API integration. Demo mode shows sample output.")

                annual_revenue = 365 * str_occupancy/100 * str_avg_rate
                expense_pct = 0.35  # 35% operating expense rate
                annual_expense = annual_revenue * expense_pct
                noi = annual_revenue - annual_expense

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Annual Revenue", f"${annual_revenue:,.0f}")
                col2.metric("Operating Expense", f"${annual_expense:,.0f}")
                col3.metric("NOI", f"${noi:,.0f}")
                col4.metric("Cap Rate (est)", f"{(noi/1000000)*100:.2f}%")

# ====================== TAB 7: AI ADVISOR ======================
with tab7_advisor:
    st.subheader("Appraisal AI Advisor")
    st.caption("Ask questions about Fannie Mae, Freddie Mac, FHA guidelines, USPAP, revision requests, form completion, and more.")

    advisor_settings = get_settings()
    advisor_api_key = advisor_settings.get("openai_api_key", "")

    if not advisor_api_key:
        st.warning("Set your OpenAI API key in the **Settings** tab to use the AI Advisor.")
    else:
        # Quick topic buttons
        st.markdown("**Quick Topics:**")
        qtcol1, qtcol2, qtcol3, qtcol4 = st.columns(4)
        with qtcol1:
            if st.button("📋 USPAP Rules", key="qt_uspap", use_container_width=True):
                st.session_state.advisor_messages.append({"role": "user", "content": "Summarize the key USPAP requirements that residential appraisers need to follow for every assignment."})
                st.rerun()
        with qtcol2:
            if st.button("🏠 Fannie Mae", key="qt_fnma", use_container_width=True):
                st.session_state.advisor_messages.append({"role": "user", "content": "What are the current Fannie Mae appraisal requirements for a standard 1004 form? Cover the key things appraisers need to know."})
                st.rerun()
        with qtcol3:
            if st.button("📝 Revision Help", key="qt_revision", use_container_width=True):
                st.session_state.advisor_messages.append({"role": "user", "content": "I received a revision request from an underwriter. What are the most common revision requests and how should I handle them professionally?"})
                st.rerun()
        with qtcol4:
            if st.button("🔄 FHA Guidelines", key="qt_fha", use_container_width=True):
                st.session_state.advisor_messages.append({"role": "user", "content": "What are the key FHA appraisal requirements from the HUD Handbook 4000.1 that differ from conventional appraisals?"})
                st.rerun()

        st.markdown("---")

        # Display chat history
        for msg in st.session_state.advisor_messages:
            if msg["role"] == "user":
                st.chat_message("user").markdown(msg["content"])
            else:
                st.chat_message("assistant").markdown(msg["content"])

        # Chat input
        user_question = st.chat_input("Ask about guidelines, revision requests, form help, adjustments...")

        # Helper function for API call
        def call_advisor_api(system_prompt, api_key):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                messages = [{"role": "system", "content": system_prompt}]
                for m in st.session_state.advisor_messages[-10:]:
                    messages.append({"role": m["role"], "content": m["content"]})
                with st.spinner("Thinking..."):
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        max_tokens=2000,
                        temperature=0.3
                    )
                    answer = response.choices[0].message.content
                    st.session_state.advisor_messages.append({"role": "assistant", "content": answer})
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

        # Check if last message is from user without a response
        needs_api_call = False
        if st.session_state.advisor_messages and st.session_state.advisor_messages[-1]["role"] == "user":
            # Check if there's no assistant response after the last user message
            needs_api_call = True

        if user_question or needs_api_call:
            if user_question:
                st.session_state.advisor_messages.append({"role": "user", "content": user_question})

            system_prompt = """You are an expert residential real estate appraisal advisor with deep knowledge of:

1. FANNIE MAE (FNMA) Selling Guide - Sections B4-1 through B4-2 covering all appraisal requirements:
   - Property eligibility, condition ratings (C1-C6), quality ratings (Q1-Q6)
   - Comparable selection criteria, adjustment guidelines, UAD formatting
   - Market conditions, neighborhood analysis, condo/2-4 unit requirements
   - Desktop and hybrid appraisal requirements

2. FREDDIE MAC Single-Family Seller/Servicer Guide - Chapters 44-46:
   - Appraisal requirements, property eligibility, ACE criteria

3. FHA/HUD Handbook 4000.1:
   - Minimum Property Requirements (MPR) and Minimum Property Standards (MPS)
   - Health and safety requirements, repair requirements, escrow holdbacks

4. USPAP (Uniform Standards of Professional Appraisal Practice):
   - Standards Rule 1 and 2, scope of work, competency, ethics, reporting

5. Common underwriter revision requests and professional response strategies

6. UAD (Uniform Appraisal Dataset) formatting for all fields

7. Appraisal form completion: 1004, 1004C, 1073, 2055, 1025

When answering:
- Cite the relevant guideline section when possible (e.g. "Per FNMA B4-1.3-06...")
- Give practical, actionable advice appraisers can use immediately
- For revision requests, provide sample response language they can adapt
- Use plain language - be direct and helpful
- If uncertain about a specific detail, say so
- Focus on current 2025-2026 requirements including UAD 3.6 updates"""

            call_advisor_api(system_prompt, advisor_api_key)

        # Clear chat button
        if st.session_state.advisor_messages:
            if st.button("Clear Chat", key="clear_advisor"):
                st.session_state.advisor_messages = []
                st.rerun()

# ====================== TAB 7_QC: QC REVIEW ======================
with tab7_qc:
    st.markdown("### QC Review & Revision Tracking")
    st.caption("Manage revision requests, quality control items, and reviewer notes")

    conn = get_db()
    orders = conn.execute("SELECT order_id, subject_address FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()

    if orders:
        selected_order_id = st.selectbox("Select Order for Review", [o["order_id"] for o in orders], key="qc_order_select")

        if selected_order_id:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Add Revision Request")
                with st.form("revision_form"):
                    item_type = st.selectbox("Item Type", ["Missing Data", "Unsupported Adjustment", "Photo Issue", "Compliance", "Other"])
                    description = st.text_area("Description", placeholder="Describe the revision needed...")
                    rev_submit = st.form_submit_button("Add Revision Item")

                    if rev_submit and description:
                        conn = get_db()
                        conn.execute(
                            "INSERT INTO review_items (order_id, item_type, description, status, created_at) VALUES (?, ?, ?, ?, ?)",
                            (selected_order_id, item_type, description, "open", datetime.now().isoformat())
                        )
                        conn.commit()
                        conn.close()
                        st.success("Revision item added!")
                        st.rerun()

            with col2:
                st.markdown("#### QC Checklist")
                checklist_items = [
                    "Photos complete",
                    "All sections written",
                    "Comps documented",
                    "Adjustments supported",
                    "USPAP scope of work included"
                ]

                for item in checklist_items:
                    st.checkbox(item)

            st.divider()

            # Display existing review items
            st.markdown("#### Revision Items")
            conn = get_db()
            review_items = conn.execute(
                "SELECT id, item_type, description, status FROM review_items WHERE order_id = ? ORDER BY created_at DESC",
                (selected_order_id,)
            ).fetchall()
            conn.close()

            if review_items:
                for item in review_items:
                    with st.expander(f"**{item['item_type']}** - {item['description'][:50]}... [{item['status'].upper()}]"):
                        st.markdown(f"**Type:** {item['item_type']}")
                        st.markdown(f"**Description:** {item['description']}")
                        st.markdown(f"**Status:** {item['status']}")

                        if item['status'] == 'open':
                            with st.form(f"response_form_{item['id']}"):
                                response = st.text_area("Response/Resolution:", key=f"response_{item['id']}")
                                status = st.selectbox("Update Status:", ["open", "resolved", "pending"], key=f"status_{item['id']}")
                                resp_submit = st.form_submit_button("Save Response")

                                if resp_submit and response:
                                    conn = get_db()
                                    conn.execute(
                                        "UPDATE review_items SET status = ?, response = ?, resolved_at = ? WHERE id = ?",
                                        (status, response, datetime.now().isoformat() if status == 'resolved' else None, item['id'])
                                    )
                                    conn.commit()
                                    conn.close()
                                    st.success("Response saved!")
                                    st.rerun()
            else:
                st.info("No revision items yet.")
    else:
        st.info("No orders available for review.")

# ====================== TAB 4: ACTIVITY LOG ======================
with tab4:
    st.markdown("### Activity Log")

    conn = get_db()
    activity = pd.read_sql_query("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 50", conn)
    conn.close()

    if not activity.empty:
        activity_display = activity[["order_id", "action", "details", "timestamp"]].copy()
        activity_display["timestamp"] = pd.to_datetime(activity_display["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(activity_display, use_container_width=True, hide_index=True)
    else:
        st.info("No activity logged yet.")

# ====================== TAB 5: SETTINGS ======================
with tab5:
    st.markdown("### Settings & Configuration")

    tab_settings_general, tab_settings_api = st.tabs(["General", "API Keys"])

    with tab_settings_general:
        st.markdown("#### Account Settings")
        st.markdown(f"**Current User:** {st.session_state.user_name}")
        st.markdown(f"**Plan:** {st.session_state.user_tier.title()}")

        st.markdown("#### Company Information")
        with st.form("settings_form"):
            company_name = st.text_input("Company Name", value="A-Tech Appraisal Co.")
            company_address = st.text_input("Company Address", value="Warwick, RI")
            company_phone = st.text_input("Company Phone")

            settings_submit = st.form_submit_button("Save Settings")
            if settings_submit:
                save_settings({
                    "company_name": company_name,
                    "company_address": company_address,
                    "company_phone": company_phone
                })
                st.success("Settings saved!")

    with tab_settings_api:
        st.markdown("#### API Configuration")

        with st.form("api_settings_form"):
            current_settings = get_settings()

            openai_key = st.text_input(
                "OpenAI API Key",
                value=current_settings.get("openai_api_key", ""),
                type="password",
                placeholder="sk-..."
            )

            gmail_user = st.text_input(
                "Gmail Address",
                value=current_settings.get("gmail_user", ""),
                placeholder="your-email@gmail.com"
            )

            gmail_pwd = st.text_input(
                "Gmail App Password",
                value=current_settings.get("gmail_app_password", ""),
                type="password",
                placeholder="Your 16-char app password"
            )

            api_submit = st.form_submit_button("Save API Keys")
            if api_submit:
                save_settings({
                    "openai_api_key": openai_key,
                    "gmail_user": gmail_user,
                    "gmail_app_password": gmail_pwd
                })
                st.success("API keys saved. For production, configure keys in Streamlit secrets management instead of the database.")

        st.info("**Streamlit Secrets Management (Recommended for Production):**\nFor enhanced security in production deployments, add your API keys to `.streamlit/secrets.toml` instead of using the database. The app checks Streamlit secrets first before falling back to this database for backwards compatibility.")

# Footer
st.markdown("---")
st.markdown("""
<p style="text-align: center; color: #86868b; font-size: 0.85rem; margin-top: 2rem;">
Powered by A-Tech Appraisal Co., LLC • Warwick, RI<br>
AppraisalOS is the complete platform for modern appraisers
</p>
""", unsafe_allow_html=True)
