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
            photos TEXT
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
    conn.commit()
    conn.close()

init_db()

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

        prompt = f"""You are an expert residential real estate appraiser writing a USPAP-compliant
appraisal narrative for a {order_data['appraisal_type']} / {order_data.get('form_type', 'URAR')} report.

Property Details:
- Address: {order_data['subject_address']}, {order_data.get('city', '')}, {order_data.get('state', 'RI')} {order_data.get('zip_code', '')}
- Property Type: {order_data['property_type']}
- Appraiser Field Notes: {order_data.get('field_notes', 'None provided')}
- Preliminary Value Opinion: {order_data.get('value_opinion', 'TBD')}

Write the following sections in professional UAD-compliant language:
1. Subject Section - Property description, site, improvements
2. Neighborhood Analysis - Market conditions, trends, boundaries
3. Site Description - Lot size, shape, utilities, zoning
4. Improvement Description - Structure, condition, rooms, features
5. Sales Comparison Approach - Framework for comp analysis
6. Reconciliation - Final value conclusion

Keep it factual, concise, and ready to paste into a TOTAL form. Use UAD abbreviations where appropriate
(C3, C4, Q3, etc. for condition/quality ratings). Do NOT fabricate specific comp data -
leave placeholders like [COMP 1 ADDRESS] for the appraiser to fill in."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a licensed real estate appraiser assistant. Write professional, USPAP-compliant appraisal narratives."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.3
        )
        return response.choices[0].message.content, None
    except ImportError:
        return None, "OpenAI package not installed. Run: pip install openai"
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
st.caption("A-Tech Appraisal Co., LLC â¢ Warwick, RI")

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

            conn = get_db()
            conn.execute('''
                INSERT OR REPLACE INTO orders
                (order_id, client_name, client_email, client_phone, lender_name, loan_number,
                 subject_address, city, state, zip_code, property_type, appraisal_type, form_type,
                 assigned_appraiser, fee, due_date, inspection_date, status, field_notes,
                 value_opinion, created_at, updated_at, photos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, client_name, client_email, client_phone, lender_name, loan_number,
                  subject_address, city, state, zip_code, property_type, appraisal_type, form_type,
                  assigned_appraiser, fee,
                  due_date.isoformat() if due_date else None,
                  inspection_date.isoformat() if inspection_date else None,
                  status, field_notes, value_opinion,
                  prefill.get("created_at", datetime.now().isoformat()),
                  datetime.now().isoformat(), all_photos))
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

        if st.button("Generate AI Narrative", type="primary", disabled=not api_key):
            with st.spinner("GPT is writing your appraisal narrative..."):
                narrative, error = generate_narrative(order_data, api_key)
                if narrative:
                    st.session_state["generated_narrative"] = narrative
                    st.session_state["narrative_order_id"] = order_id_selected
                    st.success("Narrative generated!")
                else:
                    st.error(f"Error: {error}")

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
                mismo_ns = "http://www.mismo.org/residential/2009/schemas"
                gse_ns = "http://www.mismo.org/residential/2009/schemas/gse"
                xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"

                ET.register_namespace('', mismo_ns)
                ET.register_namespace('gse', gse_ns)
                ET.register_namespace('xsi', xsi_ns)

                root = ET.Element(f"{{{mismo_ns}}}VALUATION_RESPONSE")
                root.set("MISMOVersionID", "2.6")

                # SUBJECT section
                subject = ET.SubElement(root, f"{{{mismo_ns}}}SUBJECT")
                subject_detail = ET.SubElement(subject, f"{{{mismo_ns}}}SUBJECT_DETAIL")
                subject_detail.set("_StreetAddress", order_data.get("subject_address", ""))
                subject_detail.set("_City", order_data.get("city", ""))
                subject_detail.set("_State", order_data.get("state", "RI"))
                subject_detail.set("_PostalCode", order_data.get("zip_code", ""))
                subject_detail.set("_County", "")

                # PROPERTY section
                prop = ET.SubElement(root, f"{{{mismo_ns}}}PROPERTY")
                prop_detail = ET.SubElement(prop, f"{{{mismo_ns}}}PROPERTY_DETAIL")
                ptype = order_data.get("property_type", "Single Family")
                ptype_map = {"Single Family": "SFR", "Condo": "Condominium", "Multi-Family": "2-4 Family", "Townhouse": "Townhouse", "Co-op": "Cooperative"}
                prop_detail.set("PropertyTypeDescription", ptype_map.get(ptype, ptype))

                site = ET.SubElement(prop, f"{{{mismo_ns}}}SITE")
                site_detail = ET.SubElement(site, f"{{{mismo_ns}}}_SITE_DETAIL")

                struct = ET.SubElement(prop, f"{{{mismo_ns}}}STRUCTURE")
                struct_detail = ET.SubElement(struct, f"{{{mismo_ns}}}STRUCTURE_DETAIL")

                # SALES_COMPARISON / VALUATION
                valuation = ET.SubElement(root, f"{{{mismo_ns}}}VALUATION")
                valuation_detail = ET.SubElement(valuation, f"{{{mismo_ns}}}VALUATION_DETAIL")
                val_opinion = order_data.get("value_opinion", "")
                if val_opinion:
                    valuation_detail.set("AppraisedValueAmount", str(val_opinion))

                # APPRAISER section
                appraiser = ET.SubElement(root, f"{{{mismo_ns}}}APPRAISER")
                appraiser_detail = ET.SubElement(appraiser, f"{{{mismo_ns}}}APPRAISER_DETAIL")
                appraiser_detail.set("_Name", order_data.get("assigned_appraiser", ""))
                appraiser_detail.set("_CompanyName", "A-Tech Appraisal Co., LLC")

                # LENDER / CLIENT section
                lender = ET.SubElement(root, f"{{{mismo_ns}}}LENDER")
                lender_detail = ET.SubElement(lender, f"{{{mismo_ns}}}LENDER_DETAIL")
                lender_detail.set("_Name", order_data.get("lender_name", ""))

                client = ET.SubElement(root, f"{{{mismo_ns}}}CLIENT")
                client_detail = ET.SubElement(client, f"{{{mismo_ns}}}CLIENT_DETAIL")
                client_detail.set("_Name", order_data.get("client_name", ""))

                # LOAN section
                loan = ET.SubElement(root, f"{{{mismo_ns}}}LOAN")
                loan_detail = ET.SubElement(loan, f"{{{mismo_ns}}}LOAN_DETAIL")
                loan_detail.set("_LoanNumber", order_data.get("loan_number", ""))

                # FORM section
                form = ET.SubElement(root, f"{{{mismo_ns}}}FORM")
                form_detail = ET.SubElement(form, f"{{{mismo_ns}}}FORM_DETAIL")
                form_type = order_data.get("form_type", "URAR")
                atype = order_data.get("appraisal_type", "1004")
                form_detail.set("_Type", form_type)
                form_detail.set("FormVersionIdentifier", atype)

                # NARRATIVE / ADDENDUM section
                if order_data.get("ai_narrative"):
                    addendum = ET.SubElement(root, f"{{{mismo_ns}}}ADDENDUM")
                    addendum_detail = ET.SubElement(addendum, f"{{{mismo_ns}}}ADDENDUM_DETAIL")
                    addendum_detail.set("_Type", "Narrative")
                    narrative_text = ET.SubElement(addendum_detail, f"{{{mismo_ns}}}NARRATIVE")
                    narrative_text.text = order_data["ai_narrative"]

                xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
                st.download_button("Download MISMO XML", data=xml_str,
                                  file_name=f"{order_data['order_id']}_MISMO.xml",
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

# ====================== TAB 4: ACTIVITY LOG ======================
with tab4:
    st.subheader("Activity Log")

    conn = get_db()
    log_df = pd.read_sql_query(
        "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 100", conn
    )
    conn.close()

    if not log_df.empty:
        st.dataframe(log_df[["order_id", "action", "details", "timestamp"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("No activity recorded yet.")

# ====================== TAB 5: SETTINGS ======================
with tab5:
    st.subheader("Settings")

    settings = get_settings()

    st.markdown("**Email Configuration (Gmail)**")
    st.caption("Use a Gmail App Password â not your regular password. Google Account > Security > App Passwords.")

    gmail_user = st.text_input("Gmail Address", value=settings.get("gmail_user", ""), key="gmail_user_input")
    gmail_pass = st.text_input("Gmail App Password", value=settings.get("gmail_app_password", ""),
                               type="password", key="gmail_pass_input")

    st.markdown("**OpenAI API Key**")
    st.caption("Get your key at platform.openai.com/api-keys")
    openai_key = st.text_input("API Key", value=settings.get("openai_api_key", ""),
                                type="password", key="openai_key_input")

    st.markdown("**Company Info**")
    company_name = st.text_input("Company Name", value=settings.get("company_name", "A-Tech Appraisal Co., LLC"))
    company_phone = st.text_input("Company Phone", value=settings.get("company_phone", ""))

    if st.button("Save Settings", type="primary"):
        save_setting("gmail_user", gmail_user)
        save_setting("gmail_app_password", gmail_pass)
        save_setting("openai_api_key", openai_key)
        save_setting("company_name", company_name)
        save_setting("company_phone", company_phone)
        st.success("Settings saved!")
