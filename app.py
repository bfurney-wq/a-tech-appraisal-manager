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

# ====================== CONFIG ======================
st.set_page_config(page_title="A-Tech Appraisal Manager", layout="wide")

# ====================== SESSION STATE INIT ======================
if "show_form" not in st.session_state:
    st.session_state.show_form = False
if "edit_order_id" not in st.session_state:
    st.session_state.edit_order_id = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Dashboard"

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
- Flood Zone: {p.get('flood_zone', 'Unknown')}, Flood Map #: {p.get('flood_map_number', 'Unknown')}
- Taxes: ${p.get('tax_amount', 'Unknown')} ({p.get('tax_year', 'Unknown')})
- Assessor Parcel #: {p.get('assessor_parcel', 'Unknown')}
- Legal Description: {p.get('legal_description', 'Unknown')}"""

        prompt = f"""You are a licensed residential real estate appraiser with 20+ years of experience
in {order_data.get('state', 'RI')}, writing a USPAP-compliant appraisal narrative for a
{order_data['appraisal_type']} / {order_data.get('form_type', 'URAR')} report.

You MUST use your knowledge of the actual area to write realistic, detailed content. Use real street
names that exist in the area. Reference actual landmarks, schools, shopping areas, and roads. Write
as if you personally inspected this property and researched the local MLS.

Property Details:
- Address: {order_data['subject_address']}, {order_data.get('city', '')}, {order_data.get('state', 'RI')} {order_data.get('zip_code', '')}
- Property Type: {order_data['property_type']}
{prop_info}
- Appraiser Field Notes: {order_data.get('field_notes', 'None provided')}
- Preliminary Value Opinion: {order_data.get('value_opinion', 'TBD')}

Write ALL of the following sections in full detail. Each section should be multiple paragraphs.
Do NOT abbreviate or cut short. Write as a thorough appraiser would:

1. SUBJECT SECTION (3+ paragraphs)
   - Full property description with all physical characteristics
   - Legal description, census tract, map reference
   - Current owner, sale history (prior 3 years), current listing status
   - HOA fees if applicable, special assessments

2. NEIGHBORHOOD ANALYSIS (3+ paragraphs)
   - Specific boundaries using real road names
   - Built-up percentage, growth rate, property values trend
   - Demand/supply, marketing time, present land use percentages
   - Nearby amenities (schools by name, parks, shopping, employment centers)
   - Any positive or negative factors (highway noise, views, water access)

3. SITE DESCRIPTION (2+ paragraphs)
   - Lot dimensions, area, shape, topography, drainage
   - Utilities (public water, public sewer, gas, electric)
   - Street type, curb/gutter, sidewalk, alley
   - FEMA flood zone, flood map panel, flood insurance requirement
   - Easements, encroachments, environmental conditions
   - Zoning classification and compliance

4. IMPROVEMENT DESCRIPTION (3+ paragraphs)
   - Foundation type, exterior walls, roof surface and condition
   - Room-by-room breakdown (kitchen, living room, dining, bedrooms, baths)
   - Kitchen details (counters, appliances, cabinets, flooring)
   - Bathroom details (fixtures, tile, condition)
   - Basement description (finished/unfinished, ceiling height, egress, sump pump)
   - Mechanical systems (HVAC age, water heater, electrical panel)
   - Interior finishes (flooring types, paint, trim)
   - Exterior features (deck, patio, porch, pool, fencing, landscaping)
   - Garage/carport details
   - Overall condition and quality ratings with justification

5. SALES COMPARISON APPROACH (4+ paragraphs)
   - Search parameters used (radius, date range, property type)
   - 3 comparable sales with FULL details: address, sale price, sale date, GLA, lot size,
     rooms, beds, baths, year built, condition, quality, garage, basement
   - Line-by-line adjustment explanation for each comp
   - Adjustment rates used and market support for those rates
   - Net and gross adjustment percentages
   - Indicated value range and reconciled value from this approach

6. COST APPROACH (2+ paragraphs)
   - Site value estimate with support
   - Cost new estimate (cost per sq ft, source: Marshall & Swift or similar)
   - Physical depreciation (effective age / total economic life)
   - Functional and external depreciation if any
   - Indicated value by cost approach

7. RECONCILIATION (2+ paragraphs)
   - Weight given to each approach and why
   - Final opinion of value with effective date
   - Exposure time, marketing time estimates
   - Confidence level in the value conclusion

8. ADDENDUM / SCOPE OF WORK (2+ paragraphs)
   - Scope of work performed (inspection type, data sources, analysis methods)
   - Intended use and intended users
   - Definition of market value used
   - Assumptions and limiting conditions
   - Certification statement reference
   - Prior services disclosure

Use UAD abbreviations where standard (C1-C6, Q1-Q6, N;Res;, etc.).
Write in professional appraiser language. Be thorough - a reviewer should find no blanks or vague statements."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a licensed certified residential real estate appraiser with 20+ years of experience appraising properties in {order_data.get('city', 'Rhode Island')}, {order_data.get('state', 'RI')}. You have deep knowledge of the local real estate market, neighborhoods, street names, schools, and recent sales. Write thorough, professional, USPAP-compliant appraisal narratives. Use your knowledge of the actual geographic area to include realistic details. Every section must be substantive - never use placeholder text or vague one-liners."},
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
in {city}, {state}. Generate COMPLETE structured appraisal data as JSON for a URAR form.
This data will be imported into TOTAL appraisal software via UAD XML.

USE YOUR KNOWLEDGE OF THE ACTUAL AREA. Use real street names that exist in {city}, {state}.
Use realistic sale prices for the area. Reference actual neighborhoods, school districts, and landmarks.

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
- Flood Zone: {p.get('flood_zone', '')}, Map #: {p.get('flood_map_number', '')}
- Tax: ${p.get('tax_amount', '')} ({p.get('tax_year', '')}), Parcel: {p.get('assessor_parcel', '')}
- Legal Desc: {p.get('legal_description', '')}
- Value Opinion: {order_data.get('value_opinion', '')}
- Field Notes: {order_data.get('field_notes', '')}

CRITICAL RULES:
1. Use REAL street names from {city}, {state} for comparable sales
2. Sale prices must be realistic for this specific zip code and neighborhood
3. Sale dates must be within the last 12 months
4. Every adjustment must have a dollar amount that makes sense (e.g. $50/sqft for GLA, $5000-15000 for garage)
5. Net adjustments should typically be under 15% of sale price, gross under 25%
6. All comments must be 3-5 sentences minimum - NO one-liners
7. The addendum must be a FULL scope of work (8+ sentences)
8. All monetary values as strings without $ signs or commas

Return ONLY valid JSON (no markdown, no code fences) with this EXACT structure:
{{
  "comps": [
    {{
      "address": "use a real street name from {city}",
      "city": "{city}",
      "state": "{state}",
      "zip": "{zipcode}",
      "sale_price": "350000",
      "sale_date": "01/2026",
      "financing_type": "FHA",
      "financing_adj": "0",
      "concessions": "0",
      "concessions_adj": "0",
      "gla": "1800",
      "total_rooms": "7",
      "bedrooms": "3",
      "bathrooms": "2",
      "year_built": "1985",
      "lot_size": "10000",
      "design_style": "Colonial",
      "exterior_walls": "Vinyl Siding",
      "roof_surface": "Asphalt Shingle",
      "condition": "C3",
      "quality": "Q3",
      "view": "N;Res;",
      "foundation": "Full Basement",
      "basement_total_sqft": "900",
      "basement_finished_sqft": "400",
      "heating_cooling": "FWA/Central",
      "garage_parking": "2gbi",
      "porch_patio_deck": "Deck, Patio",
      "fireplace": "1fp1wbfp",
      "pool": "None",
      "fence": "Wood Privacy",
      "functional_utility": "Average",
      "energy_efficiency": "Typical",
      "location_adj": "0",
      "lease_fee_adj": "0",
      "site_adj": "0",
      "view_adj": "0",
      "design_adj": "0",
      "quality_adj": "0",
      "age_adj": "0",
      "condition_adj": "0",
      "gla_adj": "-5000",
      "room_adj": "0",
      "basement_adj": "0",
      "functional_adj": "0",
      "heating_adj": "0",
      "energy_adj": "0",
      "garage_adj": "0",
      "porch_adj": "0",
      "fireplace_adj": "0",
      "pool_adj": "0",
      "fence_adj": "0",
      "net_adj": "-5000",
      "gross_adj": "5000",
      "net_adj_pct": "1.4",
      "gross_adj_pct": "1.4",
      "adj_sale_price": "345000",
      "data_source": "RIMLS#12345678;DOM 30",
      "verification_source": "Public Records/MLS",
      "proximity": "0.3 miles",
      "prior_sale_date": "N/A",
      "prior_sale_price": "N/A"
    }}
  ],
  "neighborhood": {{
    "name": "use actual neighborhood name for this area",
    "boundaries": "North: real road, South: real road, East: real road, West: real road",
    "description": "3+ sentences describing the actual neighborhood character, housing stock, and appeal",
    "built_up": "Over 75%",
    "growth_rate": "Stable",
    "property_values": "Increasing",
    "demand_supply": "Shortage",
    "marketing_time": "Under 3 Months",
    "market_conditions": "3+ sentences about the current local real estate market conditions and trends",
    "price_low": "250000",
    "price_high": "500000",
    "price_predominant": "375000",
    "age_low": "10",
    "age_high": "80",
    "age_predominant": "40",
    "land_use_sf_pct": "85",
    "land_use_24_pct": "5",
    "land_use_apt_pct": "5",
    "land_use_comm_pct": "3",
    "land_use_other_pct": "2",
    "neighborhood_factors": "2+ sentences about any positive or negative neighborhood factors"
  }},
  "site": {{
    "dimensions": "{p.get('lot_dimensions', '')}",
    "area": "{p.get('lot_area', '')}",
    "shape": "Rectangular",
    "view": "N;Res;",
    "topography": "Level",
    "drainage": "Adequate",
    "utilities_electric": "Public",
    "utilities_gas": "Public",
    "utilities_water": "Public",
    "utilities_sewer": "Public",
    "street": "Asphalt",
    "curb_gutter": "Yes",
    "sidewalk": "Yes",
    "street_lights": "Yes",
    "alley": "None",
    "fema_flood_zone": "{p.get('flood_zone', 'X')}",
    "fema_map_number": "{p.get('flood_map_number', '')}",
    "fema_map_date": "",
    "flood_insurance_required": "No",
    "easements": "Typical utility easements noted",
    "encroachments": "None observed",
    "special_assessments": "None",
    "environmental_conditions": "None observed",
    "zoning_class": "{p.get('zoning', '')}",
    "zoning_description": "Single Family Residential",
    "zoning_compliance": "Legal conforming",
    "highest_best_use": "Present use as improved - single family residential"
  }},
  "subject_improvements": {{
    "general_description": "3+ sentences describing the overall structure and its characteristics",
    "foundation_walls": "{p.get('foundation_type', '')}",
    "exterior_walls": "{p.get('exterior_desc', '')}",
    "roof_surface": "Asphalt Shingle",
    "roof_condition": "Average - no visible defects",
    "gutters_downspouts": "Aluminum",
    "window_type": "Double Hung/Insulated",
    "storm_screens": "Yes",
    "insulation": "Adequate",
    "flooring": "Hardwood, Carpet, Tile",
    "walls_trim": "Drywall, Painted, Wood Trim",
    "bath_floor": "Ceramic Tile",
    "bath_wainscot": "Ceramic Tile",
    "kitchen_counters": "Granite",
    "kitchen_cabinets": "Wood",
    "kitchen_appliances": "Refrigerator, Range/Oven, Dishwasher, Microwave",
    "attic": "Scuttle",
    "amenities": "Fireplace, Deck, Patio",
    "car_storage": "{p.get('garage_type', '')}",
    "physical_depreciation": "Normal for age",
    "functional_depreciation": "None noted",
    "external_depreciation": "None noted",
    "effective_age": "",
    "remaining_economic_life": "50",
    "overall_condition_comment": "3+ sentences about the overall condition of improvements"
  }},
  "comments": {{
    "additional_features": "3-5 sentences describing additional features, upgrades, renovations, and amenities. Mention specific items like updated kitchen, new roof, deck/patio size, landscaping quality, storage, and any other value-adding features.",
    "condition_comment": "3-5 sentences about the overall condition. Reference specific systems (roof age, HVAC age, water heater), recent updates, deferred maintenance if any, and effective age vs actual age.",
    "quality_comment": "3-5 sentences about construction quality. Mention materials used, workmanship, quality tier (Q1-Q6 with description), how it compares to neighborhood standards.",
    "adverse_conditions": "2-3 sentences about any adverse environmental conditions, external factors, or special assessments observed. If none, explain what was checked and that none were found.",
    "conforms_to_neighborhood": "2-3 sentences about how the subject conforms or does not conform to the neighborhood in terms of size, style, condition, and price range. Note any over-improvements or under-improvements.",
    "reconciliation": "4-6 sentences. State the indicated value from each approach (Sales Comparison, Cost, Income if applicable). Explain the weight given to each approach and why. State the final opinion of market value and the effective date. Mention the exposure time and marketing time estimates.",
    "conditions_comment": "3-4 sentences about any conditions of the appraisal. Is it subject to completion of repairs? Subject to inspection? As-is? Hypothetical conditions? Extraordinary assumptions?",
    "sales_comparison_comment": "4-6 sentences. Describe the comparable selection process, search parameters used, why these comps were chosen, the adjustment methodology, and the reliability of the indicated value from this approach. Mention the MLS searched, date range, and any limiting factors in comp availability.",
    "cost_comment": "3-4 sentences about the cost approach. Source of cost data (Marshall & Swift, local builders, etc.), how site value was estimated, depreciation methodology, and reliability of this approach for this property type and age.",
    "addendum": "ADDENDUM / SCOPE OF WORK: 8-12 sentences minimum. Include: (1) Scope of work performed - type of inspection (interior/exterior), data sources consulted (MLS, public records, assessor), analysis performed. (2) Intended use: mortgage lending. Intended user: lender/client. (3) Market value definition per USPAP/OCC/FIRREA. (4) Three-year sale/listing history of the subject. (5) Three-year sale/listing history of each comparable. (6) Market trend analysis with data support (median prices, days on market, inventory levels). (7) Any extraordinary assumptions or hypothetical conditions. (8) Appraiser competency statement. (9) Prior services statement."
  }},
  "cost_approach": {{
    "site_value": "",
    "site_value_source": "Comparable land sales and assessor allocation",
    "dwelling_sqft": "{p.get('gla_sqft', '')}",
    "dwelling_cost_per_sqft": "",
    "dwelling_cost_source": "Marshall & Swift Residential Cost Handbook",
    "dwelling_cost": "",
    "garage_sqft": "",
    "garage_cost_per_sqft": "",
    "garage_cost": "",
    "other_improvements": "",
    "other_improvements_cost": "0",
    "total_new_cost": "",
    "physical_depreciation_pct": "",
    "physical_depreciation_amt": "",
    "functional_depreciation_amt": "0",
    "functional_depreciation_desc": "None observed",
    "external_depreciation_amt": "0",
    "external_depreciation_desc": "None observed",
    "total_depreciation": "",
    "depreciated_cost": "",
    "site_improvements": "",
    "site_improvements_desc": "Driveway, walkways, landscaping, fencing",
    "indicated_value": "",
    "effective_age": "",
    "remaining_economic_life": "50",
    "total_economic_life": ""
  }},
  "prior_sales": {{
    "subject_prior_sale_date": "N/A or date",
    "subject_prior_sale_price": "N/A or price",
    "subject_current_listing": "N/A or listing price",
    "subject_current_listing_dom": "N/A or days"
  }},
  "valuation_summary": {{
    "sales_comparison_value": "",
    "cost_approach_value": "",
    "income_approach_value": "N/A",
    "final_opinion_value": "",
    "effective_date": "",
    "exposure_time": "30-90 days",
    "marketing_time": "30-90 days"
  }}
}}

IMPORTANT: Generate 3 realistic comparable sales from {city}, {state} {zipcode}.
Use REAL street names from this area. Make adjustments that are mathematically correct
(net_adj = sum of all individual adjustments, adj_sale_price = sale_price + net_adj).
Net adjustment percentage = abs(net_adj) / sale_price * 100.
Gross adjustment percentage = sum of abs values of all adjustments / sale_price * 100.
All comps should bracket the subject value opinion. Fill in EVERY field. No blanks."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a licensed certified residential real estate appraiser with 20+ years experience in {city}, {state}. You have deep knowledge of local street names, neighborhoods, recent sales, and market conditions. Return ONLY valid JSON - no markdown formatting, no code fences, no commentary. Every field must be filled in with realistic, specific data appropriate for this market area."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8000,
            temperature=0.2
        )
        result_text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        if result_text.startswith("json"):
            result_text = result_text[4:]
        report_data = json.loads(result_text.strip())
        return report_data, None
    except ImportError:
        return None, "OpenAI package not installed."
    except json.JSONDecodeError as e:
        return None, f"AI returned invalid JSON: {str(e)}"
    except Exception as e:
        return None, str(e)

# ====================== SETTINGS HELPERS ======================
def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def save_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ====================== HEADER ======================
st.title("A-Tech Appraisal Manager")
st.caption("A-Tech Appraisal Co., LLC - Warwick, RI")

# ====================== NAVIGATION ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "New Order", "AI Reports", "Activity Log", "Settings"])

# ====================== TAB 1: DASHBOARD ======================
with tab1:
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    conn.close()

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    pending = len(df[df["status"] == "Pending"]) if not df.empty else 0
    in_progress = len(df[df["status"] == "In Progress"]) if not df.empty else 0
    completed = len(df[df["status"] == "Completed"]) if not df.empty else 0

    col1.metric("Total Orders", total)
    col2.metric("Pending", pending)
    col3.metric("In Progress", in_progress)
    col4.metric("Completed", completed)

    st.divider()

    # Filter controls
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        status_filter = st.selectbox("Filter by Status", ["All", "Pending", "In Progress", "Completed", "On Hold", "Cancelled"])
    with fcol2:
        appraiser_filter = st.selectbox("Filter by Appraiser", ["All"] + (df["assigned_appraiser"].dropna().unique().tolist() if not df.empty else []))
    with fcol3:
        search = st.text_input("Search (address, client, order ID)")

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
        status_icons = {"Pending": "ð´", "In Progress": "ð¡", "Completed": "ð¢", "On Hold": "ð ", "Cancelled": "â«"}
        filtered["Status Display"] = filtered["status"].apply(lambda s: f"{status_icons.get(s, 'âª')} {s}")

        display_cols = ["order_id", "client_name", "subject_address", "assigned_appraiser",
                       "Status Display", "due_date", "fee", "created_at"]
        available_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(filtered[available_cols], use_container_width=True, hide_index=True)

        # Order detail expander
        st.subheader("Order Details")
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
                    with st.expander("Field Notes"):
                        st.write(order["field_notes"])

                if order["ai_narrative"]:
                    with st.expander("AI Narrative"):
                        st.write(order["ai_narrative"])

                # Photo gallery
                if order["photos"]:
                    with st.expander("Photos"):
                        photo_paths = [p.strip() for p in order["photos"].split(",") if p.strip()]
                        photo_cols = st.columns(min(4, len(photo_paths)))
                        for i, path in enumerate(photo_paths):
                            if os.path.exists(path):
                                with photo_cols[i % 4]:
                                    st.image(path, use_container_width=True)

                # Quick status update
                st.divider()
                qcol1, qcol2 = st.columns([3, 1])
                with qcol1:
                    new_status = st.selectbox("Quick Status Update",
                        ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"],
                        index=["Pending", "In Progress", "Completed", "On Hold", "Cancelled"].index(order["status"]),
                        key="quick_status"
                    )
                with qcol2:
                    if st.button("Update Status"):
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
                            <p>A-Tech Appraisal Co., LLC<br>Warwick, RI</p>
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
        st.info("No orders found. Create your first order in the 'New Order' tab.")

# ====================== TAB 2: NEW / EDIT ORDER ======================
with tab2:
    st.subheader("Create / Edit Order")

    conn = get_db()
    existing_orders = pd.read_sql_query("SELECT order_id FROM orders ORDER BY created_at DESC", conn)
    conn.close()

    edit_mode = st.radio("Mode", ["New Order", "Edit Existing"], horizontal=True)

    prefill = {}
    if edit_mode == "Edit Existing" and not existing_orders.empty:
        edit_id = st.selectbox("Select order to edit", existing_orders["order_id"].tolist())
        conn = get_db()
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (edit_id,)).fetchone()
        conn.close()
        if row:
            prefill = dict(row)

    with st.form("order_form", clear_on_submit=True):
        st.markdown("**Order Info**")
        ocol1, ocol2 = st.columns(2)
        with ocol1:
            next_num = len(existing_orders) + 1
            order_id = st.text_input("Order ID", value=prefill.get("order_id", f"AT-{datetime.now().strftime('%Y%m%d')}-{next_num:03d}"))
            client_name = st.text_input("Client Name", value=prefill.get("client_name", ""))
            client_email = st.text_input("Client Email", value=prefill.get("client_email", ""))
            client_phone = st.text_input("Client Phone", value=prefill.get("client_phone", ""))
        with ocol2:
            lender_name = st.text_input("Lender Name", value=prefill.get("lender_name", ""))
            loan_number = st.text_input("Loan Number", value=prefill.get("loan_number", ""))
            fee = st.number_input("Fee ($)", value=float(prefill.get("fee", 0) or 0), step=25.0)
            due_date = st.date_input("Due Date", value=None)

        st.markdown("**Property Info**")
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            subject_address = st.text_input("Street Address", value=prefill.get("subject_address", ""))
            city = st.text_input("City", value=prefill.get("city", "Warwick"))
            state = st.text_input("State", value=prefill.get("state", "RI"))
            zip_code = st.text_input("Zip", value=prefill.get("zip_code", ""))
        with pcol2:
            property_type = st.selectbox("Property Type",
                ["Single Family", "Condo", "2-4 Unit", "Multi-Family", "Land", "Other"],
                index=["Single Family", "Condo", "2-4 Unit", "Multi-Family", "Land", "Other"].index(prefill.get("property_type", "Single Family")) if prefill.get("property_type") in ["Single Family", "Condo", "2-4 Unit", "Multi-Family", "Land", "Other"] else 0
            )
            appraisal_type = st.selectbox("Appraisal Type", ["1004", "1004C", "1073", "2055", "1025", "Desktop"],
                index=["1004", "1004C", "1073", "2055", "1025", "Desktop"].index(prefill.get("appraisal_type", "1004")) if prefill.get("appraisal_type") in ["1004", "1004C", "1073", "2055", "1025", "Desktop"] else 0
            )
            form_type = st.selectbox("Form Type", ["URAR", "Condo", "Small Income", "Land", "Exterior Only", "Desktop"],
                index=["URAR", "Condo", "Small Income", "Land", "Exterior Only", "Desktop"].index(prefill.get("form_type", "URAR")) if prefill.get("form_type") in ["URAR", "Condo", "Small Income", "Land", "Exterior Only", "Desktop"] else 0
            )
            assigned_appraiser = st.selectbox("Assigned Appraiser", ["Bill Furney", "Team Member 1", "Team Member 2"])
            inspection_date = st.date_input("Inspection Date", value=None)

        # Property Details (for URAR/XML export)
        st.markdown("**Property Details (for URAR)**")
        prefill_pd = {}
        if prefill.get("property_details"):
            try:
                prefill_pd = json.loads(prefill["property_details"])
            except:
                prefill_pd = {}

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

        st.markdown("**Status & Notes**")
        status = st.selectbox("Status", ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"],
            index=["Pending", "In Progress", "Completed", "On Hold", "Cancelled"].index(prefill.get("status", "Pending")) if prefill.get("status") in ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"] else 0
        )
        field_notes = st.text_area("Field Notes", value=prefill.get("field_notes", ""), height=150,
            placeholder="Measurements, observations, comp notes, condition details...")
        value_opinion = st.text_input("Preliminary Value Opinion", value=prefill.get("value_opinion", ""))

        # Photo upload
        uploaded_files = st.file_uploader("Upload Photos", accept_multiple_files=True, type=["jpg", "png", "jpeg"])

        submitted = st.form_submit_button("Save Order", type="primary")

        if submitted:
            # Handle photos
            photos_saved = []
            if uploaded_files:
                os.makedirs("photos", exist_ok=True)
                for file in uploaded_files:
                    path = f"photos/{order_id}_{file.name}"
                    with open(path, "wb") as f:
                        f.write(file.getbuffer())
                    photos_saved.append(path)

            # Keep existing photos if editing
            existing_photos = prefill.get("photos", "") or ""
            if existing_photos and photos_saved:
                all_photos = existing_photos + "," + ",".join(photos_saved)
            elif photos_saved:
                all_photos = ",".join(photos_saved)
            else:
                all_photos = existing_photos

            # Build property_details JSON
            prop_details = json.dumps({
                "year_built": pd_year_built, "stories": pd_stories, "design_style": pd_design_style,
                "exterior_desc": pd_exterior, "foundation_type": pd_foundation,
                "basement_sqft": pd_basement_sqft, "basement_finished_pct": pd_basement_fin,
                "total_rooms": pd_total_rooms, "bedrooms": pd_bedrooms, "bathrooms": pd_bathrooms,
                "gla_sqft": pd_gla, "heating_type": pd_heating, "cooling_type": pd_cooling,
                "condition_rating": pd_condition, "quality_rating": pd_quality,
                "lot_dimensions": pd_lot_dims, "lot_area": pd_lot_area, "zoning": pd_zoning,
                "garage_type": pd_garage, "county": pd_county, "neighborhood_name": pd_neighborhood,
                "assessor_parcel": pd_assessor, "tax_year": pd_tax_year, "tax_amount": pd_tax_amount,
                "flood_zone": pd_flood_zone, "flood_map_id": pd_flood_map, "legal_desc": pd_legal
            })

            conn = get_db()
            conn.execute('''
                INSERT OR REPLACE INTO orders
                (order_id, client_name, client_email, client_phone, lender_name, loan_number,
                 subject_address, city, state, zip_code, property_type, appraisal_type, form_type,
                 assigned_appraiser, fee, due_date, inspection_date, status, field_notes,
                 value_opinion, created_at, updated_at, photos, property_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, client_name, client_email, client_phone, lender_name, loan_number,
                  subject_address, city, state, zip_code, property_type, appraisal_type, form_type,
                  assigned_appraiser, fee,
                  due_date.isoformat() if due_date else None,
                  inspection_date.isoformat() if inspection_date else None,
                  status, field_notes, value_opinion,
                  prefill.get("created_at", datetime.now().isoformat()),
                  datetime.now().isoformat(), all_photos, prop_details))
            conn.commit()
            conn.close()

            action = "Order Updated" if edit_mode == "Edit Existing" else "Order Created"
            log_activity(order_id, action, f"Status: {status}")

            st.success(f"Order {order_id} saved!")
            st.rerun()

# ====================== TAB 3: AI REPORTS ======================
with tab3:
    st.subheader("AI Report Writer")

    settings = get_settings()
    api_key = settings.get("openai_api_key", "")

    if not api_key:
        st.warning("OpenAI API key not configured. Go to Settings tab to add it.")

    conn = get_db()
    orders_df = pd.read_sql_query("SELECT order_id, subject_address, status FROM orders ORDER BY created_at DESC", conn)
    conn.close()

    if not orders_df.empty:
        selected_order = st.selectbox("Select Order",
            orders_df.apply(lambda r: f"{r['order_id']} - {r['subject_address']}", axis=1).tolist(),
            key="ai_order_select")

        order_id_selected = selected_order.split(" - ")[0]
        conn = get_db()
        order_data = dict(conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id_selected,)).fetchone())
        conn.close()

        st.write(f"**Property:** {order_data['subject_address']}, {order_data.get('city', '')}, {order_data.get('state', 'RI')}")
        st.write(f"**Type:** {order_data['property_type']} | **Form:** {order_data.get('form_type', 'URAR')}")

        if order_data.get("field_notes"):
            with st.expander("Current Field Notes"):
                st.write(order_data["field_notes"])

        if order_data.get("ai_narrative"):
            st.info("This order already has an AI narrative. Generating a new one will replace it.")

        gcol1, gcol2 = st.columns(2)
        with gcol1:
            if st.button("Generate AI Narrative", type="primary", disabled=not api_key):
                with st.spinner("GPT is writing your appraisal narrative..."):
                    narrative, error = generate_narrative(order_data, api_key)
                    if narrative:
                        st.session_state["generated_narrative"] = narrative
                        st.session_state["narrative_order_id"] = order_id_selected
                        st.success("Narrative generated!")
                    else:
                        st.error(f"Error: {error}")
        with gcol2:
            if st.button("Generate Full Report Data (Comps + Adjustments)", disabled=not api_key):
                with st.spinner("GPT is generating comps, adjustments, and comments..."):
                    report_data, error = generate_report_data(order_data, api_key)
                    if report_data:
                        # Store as JSON in a settings key tied to order
                        save_setting(f"report_data_{order_id_selected}", json.dumps(report_data))
                        log_activity(order_id_selected, "AI Report Data Generated", "Comps, adjustments, comments")
                        st.success("Full report data generated! Comps, adjustments, and comments are ready for XML export.")
                        st.json(report_data)
                    else:
                        st.error(f"Error: {error}")

        # Show existing report data if available
        existing_rd = settings.get(f"report_data_{order_id_selected}", "")
        if existing_rd:
            with st.expander("Stored Report Data (Comps & Adjustments)"):
                try:
                    st.json(json.loads(existing_rd))
                except:
                    st.write(existing_rd)

        # Show and edit generated narrative
        if st.session_state.get("narrative_order_id") == order_id_selected and st.session_state.get("generated_narrative"):
            edited = st.text_area("Generated Narrative (edit before saving)",
                                 st.session_state["generated_narrative"], height=400)

            if st.button("Save Narrative to Order"):
                conn = get_db()
                conn.execute("UPDATE orders SET ai_narrative = ?, updated_at = ? WHERE order_id = ?",
                           (edited, datetime.now().isoformat(), order_id_selected))
                conn.commit()
                conn.close()
                log_activity(order_id_selected, "AI Narrative Saved")
                st.success("Narrative saved to order!")
                del st.session_state["generated_narrative"]
                st.rerun()

        # Export section
        st.divider()
        st.subheader("Export")

        ecol1, ecol2 = st.columns(2)
        with ecol1:
            if st.button("Export XML for TOTAL"):
                # Build UAD XML matching exact TOTAL/a la mode format (MISMO 2.6GSE, no namespaces)
                addr = order_data.get("subject_address", "")
                city = order_data.get("city", "")
                state = order_data.get("state", "RI")
                zipcode = order_data.get("zip_code", "")
                county = order_data.get("county", "")
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

                # Determine AppraisalPurposeType
                appraisal_type = order_data.get("appraisal_type", "Refinance")
                purpose_map = {"Refinance": "Refinance", "Purchase": "Purchase", "Refi": "Refinance", "Refinancing": "Refinance"}
                appraisal_purpose = purpose_map.get(appraisal_type, "Refinance")

                # XML escaping function
                def xesc(s):
                    """Escape XML special characters in string values"""
                    if not s:
                        return ""
                    s = str(s)
                    s = s.replace("&", "&amp;")
                    s = s.replace("<", "&lt;")
                    s = s.replace(">", "&gt;")
                    s = s.replace('"', "&quot;")
                    s = s.replace("'", "&apos;")
                    return s

                # Extract property details from JSON
                p = {}
                pd_str = order_data.get("property_details", "") or "{}"
                try:
                    p = json.loads(pd_str) if isinstance(pd_str, str) else (pd_str if pd_str else {})
                except:
                    p = {}

                yr = str(p.get("year_built", ""))
                stories = str(p.get("stories", ""))
                design = str(p.get("design_style", ""))
                found_type = str(p.get("foundation_type", "Full Basement"))
                bsmt_sqft = str(p.get("basement_sqft", ""))
                bsmt_fin = str(p.get("basement_finished_pct", ""))
                tot_rooms = str(p.get("total_rooms", ""))
                beds = str(p.get("bedrooms", ""))
                baths = str(p.get("bathrooms", ""))
                gla = str(p.get("gla_sqft", ""))
                heat = str(p.get("heating_type", ""))
                cool = str(p.get("cooling_type", ""))
                cond = str(p.get("condition_rating", ""))
                qual = str(p.get("quality_rating", ""))
                lot_dims = str(p.get("lot_dimensions", ""))
                lot_area = str(p.get("lot_area", ""))
                zoning = str(p.get("zoning", ""))
                garage = str(p.get("garage_type", ""))
                assessor = str(p.get("assessor_parcel", ""))
                tax_yr = str(p.get("tax_year", ""))
                tax_amt = str(p.get("tax_amount", ""))
                flood_z = str(p.get("flood_zone", ""))
                flood_map = str(p.get("flood_map_id", ""))
                legal = str(p.get("legal_desc", ""))
                occupancy = str(p.get("occupancy_type", "Owner"))
                rights_type = str(p.get("rights_type", "FeeSimple"))
                lat = str(p.get("latitude", ""))
                lon = str(p.get("longitude", ""))

                # Garage parsing
                garage_spaces = ""
                garage_xml_type = ""
                if garage:
                    if "1" in garage:
                        garage_spaces = "1"
                    elif "2" in garage:
                        garage_spaces = "2"
                    elif "3" in garage:
                        garage_spaces = "3"
                    if "Attached" in garage:
                        garage_xml_type = "Attached"
                    elif "Detached" in garage:
                        garage_xml_type = "Detached"
                    elif "Carport" in garage:
                        garage_xml_type = "Carport"

                # Foundation mapping
                found_map = {"Full Basement": "Basement", "Partial Basement": "Basement", "Crawl Space": "CrawlSpace", "Crawlspace": "CrawlSpace", "Slab": "Slab", "Other": "Other"}
                found_xml = found_map.get(found_type.strip(), "Basement")
                found_cond = "Full" if "Full" in found_type else ("Partial" if "Partial" in found_type else "")

                # Load AI-generated report data if available
                rd = {}
                rd_str = order_data.get("ai_report_data", "") or ""
                if rd_str:
                    try:
                        rd = json.loads(rd_str) if isinstance(rd_str, str) else (rd_str if rd_str else {})
                    except:
                        rd = {}

                comps = rd.get("comparables", []) or []
                nb = rd.get("neighborhood", {}) or {}
                comments = rd.get("comments", {}) or {}
                cost = rd.get("cost_approach", {}) or {}
                site_data = rd.get("site_data", {}) or {}
                subj_imp = rd.get("subject_improvements", {}) or {}
                prior_sales = rd.get("prior_sales", {}) or {}
                val_summary = rd.get("valuation_summary", {}) or {}

                addendum_text = comments.get("addendum", "")
                narrative_text = order_data.get("ai_narrative", "")

                # Minimal valid PDF base64 string (empty PDF)
                minimal_pdf_base64 = "JVBERi0xLjENCiXi48/TDQoxIDAgb2JqDQo8PC9UeXBlL0NhdGFsb2cvUGFnZXM/LS9Db3VudCAwPj4NCmVuZG9iag0Kend0cmFpbGVyPDwvU2l6ZSAxL1Jvb3QgMSAwIFI+Pg0Kc3RhcnR4cmVmDQowDQolJUVPRg0K"

                xml_lines = []
                xml_lines.append('<?xml version="1.0" encoding="utf-8"?>')
                xml_lines.append(f'<VALUATION_RESPONSE MISMOVersionID="2.6GSE">')

                # REPORT section
                xml_lines.append(f'  <REPORT USPAPReportDescription="{xesc(addr)}" AppraiserFileIdentifier="{xesc(order_data.get("order_id", ""))}" AppraiserAdditionalFileIdentifierName="Other File Number" AppraiserAdditionalFileIdentifier="" AppraisalSoftwareProductName="a la mode - TOTAL" AppraisalSoftwareProductVersionIdentifier="6.321" AppraiserReportSignedDate="" SupervisorReportSignedDate="" AppraisalFormType="{form_type}" _TitleDescription="{title_desc}" AppraisalFormVersionIdentifier="2005" AppraisalPurposeType="{appraisal_purpose}" OtherLoanPurposeDescription="" AppraisalPurposeTypeOtherDescription="">')

                # FORM element (primary appraisal form)
                xml_lines.append(f'    <FORM AppraisalReportContentSequenceIdentifier="1" AppraisalReportContentType="AppraisalForm" AppraisalReportContentName="URAR [UAD Version]" AppraisalReportContentIdentifier="UAD Version 9/2011" AppraisalReportContentIsPrimaryFormIndicator="Y" />')

                # EMBEDDED_FILE with minimal valid base64 PDF
                xml_lines.append(f'    <EMBEDDED_FILE _Name="AppraisalReport" _EncodingType="Base64" MIMEType="application/pdf" _Type="PDF">')
                xml_lines.append(f'      <DOCUMENT>{minimal_pdf_base64}</DOCUMENT>')
                xml_lines.append(f'    </EMBEDDED_FILE>')

                # Add addendum form if narrative/addendum text available
                combined_addendum = ""
                if addendum_text:
                    combined_addendum += addendum_text
                if narrative_text:
                    if combined_addendum:
                        combined_addendum += "\n\n"
                    combined_addendum += narrative_text
                if combined_addendum:
                    xml_lines.append(f'    <FORM AppraisalReportContentSequenceIdentifier="2" AppraisalReportContentType="Addendum" AppraisalReportContentName="Supplemental Addendum" AppraisalReportContentIdentifier="" AppraisalReportContentIsPrimaryFormIndicator="N" />')

                # PARTIES section
                xml_lines.append(f'    <PARTIES>')
                xml_lines.append(f'      <APPRAISER _Name="{xesc(appraiser_name)}" _CompanyName="" _StreetAddress="" _City="" _State="" _PostalCode="">')
                xml_lines.append(f'        <CONTACT_DETAIL>')
                xml_lines.append(f'          <CONTACT_POINT _Type="Phone" _Value="" />')
                xml_lines.append(f'          <CONTACT_POINT _Type="Email" _Value="" />')
                xml_lines.append(f'        </CONTACT_DETAIL>')
                xml_lines.append(f'        <APPRAISER_LICENSE _Type="" _Identifier="" _ExpirationDate="" _State="" />')
                xml_lines.append(f'        <INSPECTION AppraisalInspectionPropertyType="Subject" InspectionDate="{xesc(insp_date)}" />')
                xml_lines.append(f'      </APPRAISER>')
                xml_lines.append(f'      <SUPERVISOR _Name="" _CompanyName="" _StreetAddress="" _City="" _State="" _PostalCode="">')
                xml_lines.append(f'        <CONTACT_DETAIL>')
                xml_lines.append(f'          <CONTACT_POINT _Type="Phone" _Value="" />')
                xml_lines.append(f'          <CONTACT_POINT _Type="Email" _Value="" />')
                xml_lines.append(f'        </CONTACT_DETAIL>')
                xml_lines.append(f'        <APPRAISER_LICENSE _ExpirationDate="" _State="" />')
                xml_lines.append(f'        <INSPECTION AppraisalInspectionPropertyType="Comparable" />')
                xml_lines.append(f'      </SUPERVISOR>')
                xml_lines.append(f'      <REVIEW_APPRAISER />')
                xml_lines.append(f'      <REAL_ESTATE_AGENT>')
                xml_lines.append(f'        <CONTACT_DETAIL />')
                xml_lines.append(f'      </REAL_ESTATE_AGENT>')
                xml_lines.append(f'      <LENDER _UnparsedName="{xesc(lender_name)}" AppraisalFormsUnparsedAddress="" _StreetAddress="">')
                xml_lines.append(f'        <CONTACT_DETAIL _Name="">')
                xml_lines.append(f'          <CONTACT_POINT _Type="Email" _Value="" />')
                xml_lines.append(f'        </CONTACT_DETAIL>')
                xml_lines.append(f'      </LENDER>')
                xml_lines.append(f'      <BORROWER _UnparsedName="{xesc(borrower_name)}">')
                xml_lines.append(f'        <BORROWER_EXTENSION>')
                xml_lines.append(f'          <BORROWER_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'            <BORROWER_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'              <BORROWER_NAME GSEBorrowerName="{xesc(borrower_name)}" />')
                xml_lines.append(f'            </BORROWER_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'          </BORROWER_EXTENSION_SECTION>')
                xml_lines.append(f'        </BORROWER_EXTENSION>')
                xml_lines.append(f'      </BORROWER>')
                xml_lines.append(f'      <MANAGEMENT_COMPANY_EXTENSION>')
                xml_lines.append(f'        <MANAGEMENT_COMPANY_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <MANAGEMENT_COMPANY_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <MANAGEMENT_COMPANY GSEManagementCompanyName="" />')
                xml_lines.append(f'          </MANAGEMENT_COMPANY_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </MANAGEMENT_COMPANY_EXTENSION_SECTION>')
                xml_lines.append(f'      </MANAGEMENT_COMPANY_EXTENSION>')
                xml_lines.append(f'    </PARTIES>')

                # PROPERTY section
                xml_lines.append(f'  <PROPERTY _StreetAddress="{xesc(addr)}" _City="{xesc(city)}" _State="{state}" _PostalCode="{zipcode}" _County="{xesc(county)}" _CurrentOccupancyType="{occupancy}" _RightsType="{rights_type}" _RightsTypeOtherDescription="">')

                # Property Identification
                xml_lines.append(f'    <_IDENTIFICATION AssessorsParcelIdentifier="{xesc(assessor)}" MapReferenceIdentifier="" CensusTractIdentifier="">')
                xml_lines.append(f'      <PROPERTY_IDENTIFICATION_EXTENSION>')
                xml_lines.append(f'        <PROPERTY_IDENTIFICATION_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <PROPERTY_IDENTIFICATION_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <PARCEL_IDENTIFIER GSEAssessorsParcelIdentifier="{xesc(assessor)}" />')
                xml_lines.append(f'          </PROPERTY_IDENTIFICATION_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </PROPERTY_IDENTIFICATION_EXTENSION_SECTION>')
                xml_lines.append(f'      </PROPERTY_IDENTIFICATION_EXTENSION>')
                xml_lines.append(f'    </_IDENTIFICATION>')

                # Legal Description
                xml_lines.append(f'    <_LEGAL_DESCRIPTION _Type="Other" _TypeOtherDescription="" _TextDescription="{xesc(legal)}" />')

                # STRUCTURE
                xml_lines.append(f'    <STRUCTURE LivingUnitCount="1" _AccessoryUnitExistsIndicator="N" StoriesCount="{stories}" AttachmentType="Detached" BuildingStatusType="Existing" _DesignDescription="{xesc(design)}" PropertyStructureBuiltYear="{yr}" TotalRoomCount="{tot_rooms}" TotalBedroomCount="{beds}" TotalBathroomCount="{baths}" GrossLivingAreaSquareFeetCount="{gla}">')

                # Exterior Features
                xml_lines.append(f'      <EXTERIOR_FEATURE _Type="Foundation" _Description="" _ExistsIndicator="Y" />')
                xml_lines.append(f'      <EXTERIOR_FEATURE _Type="Walls" _Description="" _ExistsIndicator="Y" />')
                xml_lines.append(f'      <EXTERIOR_FEATURE _Type="RoofSurface" _Description="" _ExistsIndicator="Y" />')

                # Foundation
                xml_lines.append(f'      <FOUNDATION _Type="{found_xml}" _ConditionDescription="{found_cond}" _ExistsIndicator="{"Y" if found_type.lower() != "slab" else "N"}">')
                xml_lines.append(f'        <_CONDITION _Type="Infestation" _Comment="" />')
                xml_lines.append(f'      </FOUNDATION>')
                xml_lines.append(f'      <BASEMENT SquareFeetCount="{bsmt_sqft}" _FinishedPercent="{bsmt_fin}" />')

                # Interior Features
                xml_lines.append(f'      <INTERIOR_FEATURE _Type="Floors" _ConditionDescription="{xesc(subj_imp.get("flooring", ""))}" />')
                xml_lines.append(f'      <INTERIOR_FEATURE _Type="Walls" _ConditionDescription="{xesc(subj_imp.get("walls_trim", ""))}" />')
                xml_lines.append(f'      <INTERIOR_FEATURE _Type="TrimAndFinish" _ConditionDescription="{xesc(subj_imp.get("walls_trim", ""))}" />')
                xml_lines.append(f'      <INTERIOR_FEATURE _Type="BathroomFloors" _ConditionDescription="{xesc(subj_imp.get("bath_floor", ""))}" />')
                xml_lines.append(f'      <INTERIOR_FEATURE _Type="BathroomWainscot" _ConditionDescription="{xesc(subj_imp.get("bath_wainscot", ""))}" />')

                # Heating/Cooling
                xml_lines.append(f'      <HEATING _FuelDescription="{xesc(heat)}" />')
                xml_lines.append(f'      <COOLING _OtherIndicator="Y" _UnitDescription="{xesc(cool)}" />')

                # Kitchen Equipment
                xml_lines.append(f'      <KITCHEN_EQUIPMENT _Type="Refrigerator" _ExistsIndicator="Y" />')
                xml_lines.append(f'      <KITCHEN_EQUIPMENT _Type="RangeOven" _ExistsIndicator="Y" />')
                xml_lines.append(f'      <KITCHEN_EQUIPMENT _Type="Dishwasher" _ExistsIndicator="N" />')
                xml_lines.append(f'      <KITCHEN_EQUIPMENT _Type="WasherDryer" _ExistsIndicator="N" />')
                xml_lines.append(f'      <KITCHEN_EQUIPMENT _Type="Other" _TypeOtherDescription="" />')

                # Attic
                xml_lines.append(f'      <ATTIC>')
                xml_lines.append(f'        <ATTIC_FEATURE _Type="DropStair" _ExistsIndicator="N" />')
                xml_lines.append(f'      </ATTIC>')

                # Amenities
                amenities_str = subj_imp.get("amenities", "")
                has_fp = "Y" if "fireplace" in amenities_str.lower() or "fp" in amenities_str.lower() else "N"
                has_pool = "Y" if "pool" in amenities_str.lower() else "N"

                xml_lines.append(f'      <AMENITY _Type="WoodStove" _Count="" />')
                xml_lines.append(f'      <AMENITY _Type="Fireplace" _ExistsIndicator="{has_fp}" _Count="" />')
                xml_lines.append(f'      <AMENITY _Type="Fence" _DetailedDescription="" />')
                xml_lines.append(f'      <AMENITY _Type="Patio" _ExistsIndicator="N" _DetailedDescription="" />')
                xml_lines.append(f'      <AMENITY _Type="Porch" _ExistsIndicator="N" _DetailedDescription="" />')
                xml_lines.append(f'      <AMENITY _Type="Pool" _ExistsIndicator="{has_pool}" _DetailedDescription="" />')
                xml_lines.append(f'      <AMENITY _Type="Other" _ExistsIndicator="N" _TypeOtherDescription="" />')

                # Car Storage
                xml_lines.append(f'      <CAR_STORAGE>')
                xml_lines.append(f'        <CAR_STORAGE_LOCATION _Type="Driveway" _ExistsIndicator="Y" ParkingSpacesCount="" />')
                xml_lines.append(f'        <CAR_STORAGE_LOCATION _Type="Garage" ParkingSpacesCount="{garage_spaces}" _AttachmentType="{garage_xml_type}" />')
                xml_lines.append(f'        <CAR_STORAGE_LOCATION _Type="Carport" ParkingSpacesCount="" />')
                xml_lines.append(f'      </CAR_STORAGE>')

                # Structure Analysis
                eff_age = subj_imp.get("effective_age", cost.get("effective_age", ""))
                rem_life = subj_imp.get("remaining_economic_life", cost.get("remaining_economic_life", ""))

                xml_lines.append(f'      <STRUCTURE_ANALYSIS EffectiveAgeYearsCount="{eff_age}">')
                xml_lines.append(f'        <STRUCTURE_ANALYSIS_RATING />')
                xml_lines.append(f'        <STRUCTURE_ANALYSIS_EXTENSION>')
                xml_lines.append(f'          <STRUCTURE_ANALYSIS_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'            <STRUCTURE_ANALYSIS_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'              <EFFECTIVE_AGE GSEEffectiveAgeDescription="{xesc(eff_age)}" />')
                xml_lines.append(f'            </STRUCTURE_ANALYSIS_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'          </STRUCTURE_ANALYSIS_EXTENSION_SECTION>')
                xml_lines.append(f'        </STRUCTURE_ANALYSIS_EXTENSION>')
                xml_lines.append(f'      </STRUCTURE_ANALYSIS>')

                # Condition Details
                xml_lines.append(f'      <CONDITION_DETAIL_EXTENSION>')
                xml_lines.append(f'        <CONDITION_DETAIL_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <CONDITION_DETAIL_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <CONDITION_DETAIL _SequenceIdentifier="1" GSEImprovementAreaType="Kitchen" GSEImprovementDescriptionType="Updated" GSEEstimateYearOfImprovementType="Unknown" />')
                xml_lines.append(f'          </CONDITION_DETAIL_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </CONDITION_DETAIL_EXTENSION_SECTION>')
                xml_lines.append(f'      </CONDITION_DETAIL_EXTENSION>')

                # Overall Condition Rating
                xml_lines.append(f'      <OVERALL_CONDITION_RATING_EXTENSION>')
                xml_lines.append(f'        <OVERALL_CONDITION_RATING_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <OVERALL_CONDITION_RATING_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <OVERALL_CONDITION_RATING GSEUpdateLastFifteenYearIndicator="N" />')
                xml_lines.append(f'          </OVERALL_CONDITION_RATING_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </OVERALL_CONDITION_RATING_EXTENSION_SECTION>')
                xml_lines.append(f'      </OVERALL_CONDITION_RATING_EXTENSION>')

                # Structure Extension
                xml_lines.append(f'      <STRUCTURE_EXTENSION>')
                xml_lines.append(f'        <STRUCTURE_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <STRUCTURE_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <STRUCTURE_INFORMATION GSEYearBuiltEstimationIndicator="N" GSEStoriesCount="{stories}" />')
                xml_lines.append(f'          </STRUCTURE_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </STRUCTURE_EXTENSION_SECTION>')
                xml_lines.append(f'      </STRUCTURE_EXTENSION>')
                xml_lines.append(f'    </STRUCTURE>')

                # Off-Site Improvements
                xml_lines.append(f'    <_OFF_SITE_IMPROVEMENT _Type="Street" _Description="" _OwnershipType="Public" _ExistsIndicator="N" />')
                xml_lines.append(f'    <_OFF_SITE_IMPROVEMENT _Type="Street" _Description="" _OwnershipType="Private" _ExistsIndicator="Y" />')

                # SITE section
                xml_lines.append(f'    <SITE _DimensionsDescription="{xesc(lot_dims)}" _AreaDescription="{xesc(lot_area)}" _ZoningClassificationIdentifier="" _ZoningClassificationDescription="{xesc(zoning)}" _ZoningComplianceType="Legal" _ZoningComplianceDescription="" HighestBestUseIndicator="Y" HighestBestUseDescription="">')
                xml_lines.append(f'      <SITE_FEATURE _Type="Shape" _Comment="" />')
                xml_lines.append(f'      <SITE_FEATURE _Type="View" _Comment="" />')
                xml_lines.append(f'      <SITE_FEATURE _Type="Driveway" _Comment="" />')

                # Flood Zone
                xml_lines.append(f'      <FLOOD_ZONE SpecialFloodHazardAreaIndicator="N" NFIPFloodZoneIdentifier="{xesc(flood_z)}" NFIPMapIdentifier="{xesc(flood_map)}" NFIPMapPanelDate="">')
                xml_lines.append(f'        <FLOOD_ZONE_EXTENSION>')
                xml_lines.append(f'          <FLOOD_ZONE_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'            <FLOOD_ZONE_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'              <FLOOD_ZONE_INFORMATION GSEFEMASpecialFloodHazardAreaIndicator="N" GSENFIPFloodZoneIdentifier="{xesc(flood_z)}" GSEFEMAFloodMapIdentifier="{xesc(flood_map)}" />')
                xml_lines.append(f'            </FLOOD_ZONE_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'          </FLOOD_ZONE_EXTENSION_SECTION>')
                xml_lines.append(f'        </FLOOD_ZONE_EXTENSION>')
                xml_lines.append(f'      </FLOOD_ZONE>')

                # Site Utilities
                xml_lines.append(f'      <SITE_UTILITY _Type="Electricity" _PublicIndicator="Y" _NonPublicIndicator="N" _NonPublicDescription="" />')
                xml_lines.append(f'      <SITE_UTILITY _Type="Gas" _PublicIndicator="N" _NonPublicIndicator="Y" _NonPublicDescription="" />')
                xml_lines.append(f'      <SITE_UTILITY _Type="Water" _PublicIndicator="Y" _NonPublicIndicator="N" _NonPublicDescription="" />')
                xml_lines.append(f'      <SITE_UTILITY _Type="SanitarySewer" _PublicIndicator="N" _NonPublicIndicator="Y" _NonPublicDescription="Septic" />')
                xml_lines.append(f'    </SITE>')

                # PROJECT section
                xml_lines.append(f'    <PROJECT _Name="" _ConversionDate="" _ContainsMultipleDwellingUnitsDataSourceDescription="" _CommonElementsStatusDescription="" _CommonElementsLeaseTermsDescription="" _CommonElementsDescription="">')
                xml_lines.append(f'      <DEVELOPMENT_STAGE _TotalPhasesCount="" CompletedUnitsCount="" PlannedUnitsCount="" UnitsSoldCount="" UnitsRentedCount="" UnitsForSaleCount="" DataSourceDescription="" />')
                xml_lines.append(f'      <_PER_UNIT_FEE _Amount="" />')
                xml_lines.append(f'    </PROJECT>')

                # NEIGHBORHOOD section
                nb_name = nb.get("name", "")
                nb_desc = nb.get("description", "")
                xml_lines.append(f'    <NEIGHBORHOOD _Name="{xesc(nb_name)}" PropertyNeighborhoodLocationType="" _BuiltupRangeType="" _GrowthPaceType="" _PropertyValueTrendType="" _DemandSupplyType="" _TypicalMarketingTimeDurationType="" _BoundaryAndCharacteristicsDescription="" _Description="{xesc(nb_desc)}" _MarketConditionsDescription="">')
                xml_lines.append(f'      <_HOUSING _Type="SingleFamily" _LowPriceAmount="" _HighPriceAmount="" _PredominantPriceAmount="" _OldestYearsCount="" _NewestYearsCount="" _PredominantAgeYearsCount="" />')
                xml_lines.append(f'      <_PRESENT_LAND_USE _Type="SingleFamily" _Percent="" />')
                xml_lines.append(f'      <_PRESENT_LAND_USE _Type="TwoToFourFamily" _Percent="" />')
                xml_lines.append(f'      <_PRESENT_LAND_USE _Type="Apartment" _Percent="" />')
                xml_lines.append(f'      <_PRESENT_LAND_USE _Type="Commercial" _Percent="" />')
                xml_lines.append(f'      <_PRESENT_LAND_USE _Type="Other" _TypeOtherDescription="" _Percent="" />')
                xml_lines.append(f'      <NEIGHBORHOOD_EXTENSION>')
                xml_lines.append(f'        <NEIGHBORHOOD_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <NEIGHBORHOOD_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <NEIGHBORHOOD_BOUNDARIES GSENeighborhoodBoundariesDescription="" />')
                xml_lines.append(f'          </NEIGHBORHOOD_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </NEIGHBORHOOD_EXTENSION_SECTION>')
                xml_lines.append(f'      </NEIGHBORHOOD_EXTENSION>')
                xml_lines.append(f'    </NEIGHBORHOOD>')

                # TAX section
                xml_lines.append(f'    <_TAX _YearIdentifier="{xesc(tax_yr)}" _TotalTaxAmount="{xesc(tax_amt)}" _TotalSpecialTaxAmount="">')
                xml_lines.append(f'      <PROPERTY_TAX_EXTENSION>')
                xml_lines.append(f'        <PROPERTY_TAX_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <PROPERTY_TAX_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <PROPERTY_TAX_AMOUNT GSEPropertyTaxTotalTaxAmount="{xesc(tax_amt)}" />')
                xml_lines.append(f'          </PROPERTY_TAX_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </PROPERTY_TAX_EXTENSION_SECTION>')
                xml_lines.append(f'      </PROPERTY_TAX_EXTENSION>')
                xml_lines.append(f'    </_TAX>')

                # Additional property analysis
                xml_lines.append(f'    <LISTING_HISTORY ListedWithinPreviousYearIndicator="N" ListedWithinPreviousYearDescription="" />')
                xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="AdditionalFeatures" _Comment="" />')
                xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="QualityAndAppearance" _Comment="" />')
                xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="PhysicalDeficiency" _ExistsIndicator="N" _Comment="" />')
                xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="ConformsToNeighborhood" _ExistsIndicator="Y" _Comment="" />')
                xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="UtilitiesAndOffSiteImprovementsConformToNeighborhood" _ExistsIndicator="Y" _Comment="" />')
                xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="AdverseSiteConditions" _ExistsIndicator="N" _Comment="" />')
                xml_lines.append(f'    <PROPERTY_ANALYSIS _Type="PropertyCondition" _Comment="" />')

                # Owner
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

                # Sales Contract
                xml_lines.append(f'    <SALES_CONTRACT _ReviewComment="" _Amount="" _Date="" DataSourceDescription="" SalesConcessionAmount="" SalesConcessionDescription="">')
                xml_lines.append(f'      <SALES_CONCESSION_EXTENSION>')
                xml_lines.append(f'        <SALES_CONCESSION_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <SALES_CONCESSION_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <SALES_CONCESSION GSEUndefinedConcessionAmountIndicator="N" />')
                xml_lines.append(f'          </SALES_CONCESSION_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </SALES_CONCESSION_EXTENSION_SECTION>')
                xml_lines.append(f'      </SALES_CONCESSION_EXTENSION>')
                xml_lines.append(f'    </SALES_CONTRACT>')

                # Property Extension
                xml_lines.append(f'    <PROPERTY_EXTENSION>')
                xml_lines.append(f'      <PROPERTY_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'        <PROPERTY_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'          <PROPERTY_TYPE GSE_PUDIndicator="N" />')
                xml_lines.append(f'        </PROPERTY_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'      </PROPERTY_EXTENSION_SECTION>')
                xml_lines.append(f'    </PROPERTY_EXTENSION>')
                xml_lines.append(f'  </PROPERTY>')

                # VALUATION_METHODS section
                methods_comment = comments.get("methods", "Extent of the Appraisal Process: Standard appraisal methods applied.")
                xml_lines.append(f'  <VALUATION_METHODS _AdditionalDescription="{xesc(methods_comment)}">')

                # COST_ANALYSIS
                cost_site_val = cost.get("site_value", "")
                cost_improvement = cost.get("cost_new_improvements", "")
                cost_depr = cost.get("depreciated_cost", "")
                cost_total = cost.get("total_value", "")

                xml_lines.append(f'    <COST_ANALYSIS SiteEstimatedValueComment="" DataSourceDescription="" CostServiceQualityRatingDescription="" DataSourceEffectiveDate="" _Comment="" EstimatedRemainingEconomicLifeYearsCount="{rem_life}" SiteEstimatedValueAmount="{cost_site_val}" NewImprovementTotalCostAmount="{cost_improvement}" NewImprovementDepreciatedCostAmount="{cost_depr}" SiteOtherImprovementsAsIsAmount="" ValueIndicatedByCostApproachAmount="{cost_total}">')
                xml_lines.append(f'      <NEW_IMPROVEMENT _Type="Dwelling" SquareFeetCount="{gla}" PricePerSquareFootAmount="" _CostAmount="{cost_improvement}" _SequenceIdentifier="1" />')
                xml_lines.append(f'      <NEW_IMPROVEMENT _Type="Other" _TypeOtherDescription="" SquareFeetCount="" PricePerSquareFootAmount="" _CostAmount="" _SequenceIdentifier="2" />')
                xml_lines.append(f'      <DEPRECIATION _PhysicalPercent="" _PhysicalAmount="" _FunctionalPercent="" _FunctionalAmount="" _ExteriorPercent="" _ExteriorAmount="" _TotalAmount="" />')
                xml_lines.append(f'      <COST_ANALYSIS_EXTENSION>')
                xml_lines.append(f'        <COST_ANALYSIS_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                xml_lines.append(f'          <COST_ANALYSIS_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'            <COST_APPROACH_DATA_SOURCE GSECostDataSourceEffectiveDateDescription="" />')
                xml_lines.append(f'          </COST_ANALYSIS_EXTENSION_SECTION_DATA>')
                xml_lines.append(f'        </COST_ANALYSIS_EXTENSION_SECTION>')
                xml_lines.append(f'      </COST_ANALYSIS_EXTENSION>')
                xml_lines.append(f'    </COST_ANALYSIS>')

                # SALES_COMPARISON
                sales_comp_val = val_summary.get("sales_comparison_value", val_summary.get("market_value", ""))
                xml_lines.append(f'    <SALES_COMPARISON _CurrentSalesAgreementAnalysisComment="" _Comment="" ValueIndicatedBySalesComparisonApproachAmount="{sales_comp_val}">')
                xml_lines.append(f'      <RESEARCH ComparableListingsResearchedCount="" ComparableListingsPriceRangeLowAmount="" ComparableListingsPriceRangeHighAmount="" ComparableSalesResearchedCount="" ComparableSalesPriceRangeLowAmount="" ComparableSalesPriceRangeHighAmount="" SalesHistoryNotResearchedComment="">')
                xml_lines.append(f'        <SUBJECT DataSourceDescription="" />')
                xml_lines.append(f'        <COMPARABLE DataSourceDescription="" />')
                xml_lines.append(f'      </RESEARCH>')

                # Add subject property as comparable with sequence 0 (empty PropertySalesAmount)
                xml_lines.append(f'      <COMPARABLE_SALE PropertySequenceIdentifier="0" PropertySalesAmount="" SalesPricePerGrossLivingAreaAmount="">')
                xml_lines.append(f'        <LOCATION LatitudeNumber="{lat}" LongitudeNumber="{lon}" PropertyStreetAddress="{xesc(addr)}" PropertyStreetAddress2="{xesc(city)}, {state} {zipcode}" />')
                xml_lines.append(f'        <ROOM_ADJUSTMENT TotalRoomCount="{tot_rooms}" TotalBedroomCount="{beds}" TotalBathroomCount="{baths}" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Location" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PropertyRights" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="SiteArea" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="View" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="DesignStyle" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Quality" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Age" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Condition" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="GrossLivingArea" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementArea" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementFinish" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="FunctionalUtility" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="HeatingCooling" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="EnergyEfficient" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="CarStorage" _Description="" />')
                xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PorchDeck" _Description="" />')
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

                # Add comparable sales (sequences 1, 2, 3)
                if comps:
                    for idx, comp in enumerate(comps[:3], start=1):
                        comp_price = comp.get("sale_price", "")
                        comp_price_sqft = comp.get("price_per_sqft", "")
                        xml_lines.append(f'      <COMPARABLE_SALE PropertySequenceIdentifier="{idx}" PropertySalesAmount="{comp_price}" SalesPricePerGrossLivingAreaAmount="{comp_price_sqft}" DataSourceDescription="{xesc(comp.get("data_source", ""))}" DataSourceVerificationDescription="{xesc(comp.get("verification_source", ""))}" SalesPriceTotalAdjustmentPositiveIndicator="" SalePriceTotalAdjustmentAmount="" AdjustedSalesPriceAmount="" SalesPriceTotalAdjustmentGrossPercent="" SalesPriceTotalAdjustmentNetPercent="">')
                        xml_lines.append(f'        <LOCATION LatitudeNumber="{comp.get("latitude", "")}" LongitudeNumber="{comp.get("longitude", "")}" PropertyStreetAddress="{xesc(comp.get("address", ""))}" PropertyStreetAddress2="{xesc(comp.get("city", ""))}, {comp.get("state", "")} {comp.get("zip", "")}" ProximityToSubjectDescription="" />')
                        xml_lines.append(f'        <ROOM_ADJUSTMENT TotalRoomCount="{comp.get("total_rooms", "")}" TotalBedroomCount="{comp.get("bedrooms", "")}" TotalBathroomCount="{comp.get("bathrooms", "")}" RoomAdjustmentAmount="" />')

                        # Adjustments for comparable
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Location" _Description="{xesc(comp.get("location", ""))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PropertyRights" _Description="{xesc(comp.get("property_rights", "Fee Simple"))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="SiteArea" _Description="{xesc(comp.get("site_area", ""))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="View" _Description="{xesc(comp.get("view", ""))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="DesignStyle" _Description="{xesc(comp.get("design_style", ""))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Quality" _Description="{xesc(comp.get("quality", ""))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Age" _Description="{xesc(comp.get("age", ""))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Condition" _Description="{xesc(comp.get("condition", ""))}" _Amount="" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="GrossLivingArea" _Description="{xesc(comp.get("gla", ""))}" _Amount="{comp.get("gla_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementArea" _Description="{xesc(comp.get("basement_area", ""))}" _Amount="{comp.get("basement_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="BasementFinish" _Description="{xesc(comp.get("basement_finish", ""))}" _Amount="{comp.get("basement_finish_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="FunctionalUtility" _Description="{xesc(comp.get("functional_utility", ""))}" _Amount="{comp.get("functional_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="HeatingCooling" _Description="{xesc(comp.get("heating_cooling", ""))}" _Amount="{comp.get("heating_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="EnergyEfficient" _Description="{xesc(comp.get("energy_efficiency", ""))}" _Amount="{comp.get("energy_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="CarStorage" _Description="{xesc(comp.get("garage_parking", ""))}" _Amount="{comp.get("garage_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="PorchDeck" _Description="{xesc(comp.get("porch_patio_deck", ""))}" _Amount="{comp.get("porch_adj", "")}" />')
                        xml_lines.append(f'        <SALE_PRICE_ADJUSTMENT _Type="Other" _TypeOtherDescription="Fireplace" _Description="{xesc(comp.get("fireplace", ""))}" _Amount="{comp.get("fireplace_adj", "")}" />')

                        # Prior sales
                        c_prior_date = comp.get("prior_sale_date", "")
                        c_prior_price = comp.get("prior_sale_price", "")
                        xml_lines.append(f'        <PRIOR_SALES PropertySalesDate="{xesc(c_prior_date)}" PropertySalesAmount="{xesc(c_prior_price)}" DataSourceDescription="{xesc(comp.get("data_source", ""))}" DataSourceEffectiveDate="">')
                        xml_lines.append(f'          <PRIOR_SALES_EXTENSION>')
                        xml_lines.append(f'            <PRIOR_SALES_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                        xml_lines.append(f'              <PRIOR_SALES_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'                <PRIOR_SALE GSEPriorSaleDate="{xesc(c_prior_date)}" GSEPriorSaleComment="" />')
                        xml_lines.append(f'              </PRIOR_SALES_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'            </PRIOR_SALES_EXTENSION_SECTION>')
                        xml_lines.append(f'          </PRIOR_SALES_EXTENSION>')
                        xml_lines.append(f'        </PRIOR_SALES>')

                        # Comparison Details
                        xml_lines.append(f'        <COMPARISON_DETAIL_EXTENSION>')
                        xml_lines.append(f'          <COMPARISON_DETAIL_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                        xml_lines.append(f'            <COMPARISON_DETAIL_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'              <COMPARISON_DETAIL GSEDaysOnMarketDescription="{comp.get("days_on_market", "")}" GSEOverallConditionType="" GSEQualityOfConstructionRatingType="" GSEAgeEstimationIndicator="N" GSEBelowGradeTotalSquareFeetNumber="" GSEDataSourceDescription="" GSESaleType="" GSEFinancingType="" GSEFinancingTypeOtherDescription="" GSEConcessionAmount="" GSEListingStatusType="" GSEContractDateUnknownIndicator="N" GSEBelowGradeFinishSquareFeetNumber="" GSEBasementExitType="" />')
                        xml_lines.append(f'            </COMPARISON_DETAIL_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'          </COMPARISON_DETAIL_EXTENSION_SECTION>')
                        xml_lines.append(f'        </COMPARISON_DETAIL_EXTENSION>')

                        # View and Location Rating Extensions (only on actual comps, not subject)
                        xml_lines.append(f'        <COMPARISON_VIEW_OVERALL_RATING_EXTENSION>')
                        xml_lines.append(f'          <COMPARISON_VIEW_OVERALL_RATING_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                        xml_lines.append(f'            <COMPARISON_VIEW_OVERALL_RATING_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'              <COMPARISON_VIEW_OVERALL_RATING GSEViewOverallRatingType="" />')
                        xml_lines.append(f'            </COMPARISON_VIEW_OVERALL_RATING_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'          </COMPARISON_VIEW_OVERALL_RATING_EXTENSION_SECTION>')
                        xml_lines.append(f'        </COMPARISON_VIEW_OVERALL_RATING_EXTENSION>')

                        xml_lines.append(f'        <COMPARISON_LOCATION_OVERALL_RATING_EXTENSION>')
                        xml_lines.append(f'          <COMPARISON_LOCATION_OVERALL_RATING_EXTENSION_SECTION ExtensionSectionOrganizationName="UNIFORM APPRAISAL DATASET">')
                        xml_lines.append(f'            <COMPARISON_LOCATION_OVERALL_RATING_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'              <COMPARISON_LOCATION_OVERALL_RATING GSEOverallLocationRatingType="" />')
                        xml_lines.append(f'            </COMPARISON_LOCATION_OVERALL_RATING_EXTENSION_SECTION_DATA>')
                        xml_lines.append(f'          </COMPARISON_LOCATION_OVERALL_RATING_EXTENSION_SECTION>')
                        xml_lines.append(f'        </COMPARISON_LOCATION_OVERALL_RATING_EXTENSION>')

                        xml_lines.append(f'      </COMPARABLE_SALE>')

                xml_lines.append(f'    </SALES_COMPARISON>')

                # INCOME_ANALYSIS
                xml_lines.append(f'    <INCOME_ANALYSIS ValueIndicatedByIncomeApproachAmount="" EstimatedMarketMonthlyRentAmount="" GrossRentMultiplierFactor="" _Comment="" />')

                xml_lines.append(f'  </VALUATION_METHODS>')

                # VALUATION section (final opinion of value)
                final_val = val_summary.get("final_opinion_value", val_opinion) or val_opinion
                eff_date = val_summary.get("effective_date", insp_date) or insp_date
                reconciliation_comment = comments.get("reconciliation", "")
                conditions_comment = comments.get("conditions_comment", "")

                xml_lines.append(f'  <VALUATION PropertyAppraisedValueAmount="{final_val}" AppraisalEffectiveDate="{xesc(eff_date)}">')
                xml_lines.append(f'    <_RECONCILIATION _SummaryComment="{xesc(reconciliation_comment)}" _ConditionsComment="{xesc(conditions_comment)}">')
                xml_lines.append(f'      <_CONDITION_OF_APPRAISAL _Type="" />')
                xml_lines.append(f'    </_RECONCILIATION>')
                xml_lines.append(f'  </VALUATION>')

                # Close VALUATION_RESPONSE
                xml_lines.append(f'</VALUATION_RESPONSE>')

                xml_str = '\n'.join(xml_lines)
                st.download_button("Download UAD XML", data=xml_str,
                                  file_name=f"{order_data['order_id']}_UAD.xml",
                                  mime="application/xml")

        with ecol2:
            if st.button("Copy Narrative to Clipboard"):
                if order_data.get("ai_narrative"):
                    st.code(order_data["ai_narrative"], language=None)
                    st.info("Select all text above and copy (Ctrl+A, Ctrl+C)")
                else:
                    st.warning("No narrative saved yet. Generate one first.")
    else:
        st.info("No orders found. Create an order first.")
