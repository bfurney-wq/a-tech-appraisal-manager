
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from appraisalos import ai, db
from appraisalos.config import (
    APP_NAME,
    APPRAISAL_TYPES,
    CONDITION_RATINGS,
    DEFAULT_SECTIONS,
    FORM_TYPES,
    FOUNDATION_TYPES,
    GARAGE_TYPES,
    ORDER_STATUSES,
    PROPERTY_TYPES,
    QC_CHECKLIST_ITEMS,
    QUALITY_RATINGS,
)
from appraisalos.export import build_workfile_bundle


st.set_page_config(page_title=APP_NAME, page_icon="🏠", layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer {display:none;}
        .stApp {
            background: #f6f7fb;
        }
        .hero {
            background: linear-gradient(135deg, #111827, #1f2937);
            color: white;
            padding: 1.4rem 1.6rem;
            border-radius: 18px;
            margin-bottom: 1rem;
        }
        .card {
            background: white;
            border: 1px solid rgba(17,24,39,.08);
            border-radius: 16px;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 24px rgba(15,23,42,.04);
        }
        .metric-grid {
            display:grid;
            grid-template-columns:repeat(4, 1fr);
            gap:1rem;
            margin: 0.6rem 0 1rem 0;
        }
        .metric {
            background:white;
            border:1px solid rgba(17,24,39,.08);
            border-radius:16px;
            padding:1rem;
            box-shadow:0 8px 24px rgba(15,23,42,.04);
        }
        .metric .label {
            color:#6b7280;
            font-size:.78rem;
            text-transform:uppercase;
            letter-spacing:.08em;
            font-weight:600;
        }
        .metric .value {
            color:#111827;
            font-size:2rem;
            font-weight:700;
            margin-top:.25rem;
        }
        .tiny-note {
            color:#6b7280;
            font-size:.85rem;
        }
        .section-chip {
            display:inline-block;
            padding:.2rem .55rem;
            border-radius:999px;
            background:#eef2ff;
            color:#3730a3;
            font-size:.78rem;
            margin:.1rem .25rem .1rem 0;
        }
        .tool-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #e5e5e5;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .tool-card h4 { margin: 0 0 0.5rem 0; }
        .tool-card p { color: #666; font-size: 0.85rem; margin-bottom: 1rem; }
        .branded-footer {
            text-align: center;
            color: #9ca3af;
            font-size: 0.82rem;
            padding: 1.5rem 0 0.5rem 0;
        }
        .branded-footer a { color: #6366f1; text-decoration: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    defaults = {
        "auth_user": None,
        "engagement_extract": {},
        "purchase_extract": {},
        "assembled_report_preview": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def current_user() -> dict[str, Any] | None:
    return st.session_state.get("auth_user")


def require_login() -> dict[str, Any]:
    user = current_user()
    if user:
        return user
    render_login()
    st.stop()


def parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(value[:10], fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            pass
    return date.today()


def parse_money(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(raw)
    except Exception:
        return 0.0


def option_index(options: list[str], value: str, fallback: int = 0) -> int:
    try:
        return options.index(value)
    except Exception:
        return fallback


def merged_defaults() -> dict[str, Any]:
    engagement = dict(st.session_state.get("engagement_extract") or {})
    purchase = dict(st.session_state.get("purchase_extract") or {})
    merged = dict(purchase)
    merged.update(engagement)

    normalized = dict(merged)
    if not normalized.get("subject_address") and normalized.get("property_address"):
        normalized["subject_address"] = normalized.get("property_address")
    if not normalized.get("borrower_name") and normalized.get("buyer_name"):
        normalized["borrower_name"] = normalized.get("buyer_name")
    if not normalized.get("client_name") and normalized.get("lender_name"):
        normalized["client_name"] = normalized.get("lender_name")
    return normalized


def clear_extract_state() -> None:
    st.session_state.engagement_extract = {}
    st.session_state.purchase_extract = {}


def render_login() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1 style="margin:0;">AppraisalOS Next</h1>
            <p style="margin:.35rem 0 0 0; color:rgba(255,255,255,.78);">
                Safer intake, facts-only AI drafting, QC tracking, and honest workfile export.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Demo account: demo@appraisalos.local / demo123")

    col1, col2 = st.columns([1.2, 1])
    with col1:
        with st.form("login_form"):
            email = st.text_input("Email", value="demo@appraisalos.local")
            password = st.text_input("Password", type="password", value="demo123")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                user = db.authenticate_user(email, password)
                if user:
                    st.session_state.auth_user = user
                    st.rerun()
                st.error("Login failed.")

    with col2:
        st.markdown(
            """
            <div class="card">
                <h4 style="margin-top:0;">What changed</h4>
                <ul>
                    <li>Local users with hashed passwords instead of plain demo gating</li>
                    <li>Secrets stay in environment / <code>st.secrets</code>, not in SQLite</li>
                    <li>AI sections save to the database and log each run</li>
                    <li>QC checklist persists and revision items are tracked</li>
                    <li>Export is a real workfile bundle instead of a fake XML promise</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def hero(user: dict[str, Any], settings: dict[str, str]) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1 style="margin:0;">{settings.get("company_name", APP_NAME)}</h1>
            <p style="margin:.35rem 0 0 0; color:rgba(255,255,255,.78);">
                Welcome, {user.get("name", "")} • Role: {user.get("role", "").title()}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_orders_df(org_id: int) -> pd.DataFrame:
    rows = db.list_orders(org_id)
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    for column in ("created_at", "updated_at", "due_date", "inspection_date"):
        if column in frame.columns:
            frame[column] = frame[column].fillna("")
    return frame


def render_metrics(df: pd.DataFrame) -> None:
    total = len(df)
    review = int((df["status"] == "Review").sum()) if not df.empty else 0
    completed = int((df["status"] == "Completed").sum()) if not df.empty else 0
    overdue = 0
    if not df.empty and "due_date" in df.columns:
        today = date.today().isoformat()
        overdue = int(((df["due_date"] < today) & (~df["status"].isin(["Completed", "Cancelled"]))).sum())
    revenue = float(df["fee"].fillna(0).sum()) if not df.empty else 0.0

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric"><div class="label">Orders</div><div class="value">{total}</div></div>
            <div class="metric"><div class="label">Needs Review</div><div class="value">{review}</div></div>
            <div class="metric"><div class="label">Completed</div><div class="value">{completed}</div></div>
            <div class="metric"><div class="label">Fees</div><div class="value">${revenue:,.0f}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if overdue:
        st.warning(f"{overdue} order(s) are overdue.")


def render_home(user: dict[str, Any], org_id: int) -> None:
    df = get_orders_df(org_id)
    render_metrics(df)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Due today / next 3 days")
        if not df.empty:
            horizon = {date.today().isoformat()}
            for offset in range(1, 4):
                horizon.add((date.today()).fromordinal(date.today().toordinal() + offset).isoformat())
            due = df[df["due_date"].isin(horizon)][["order_id", "subject_address", "client_name", "due_date", "status"]]
            if not due.empty:
                st.dataframe(due, use_container_width=True, hide_index=True)
            else:
                st.info("Nothing due in the next three days.")
        else:
            st.info("No orders yet.")

    with c2:
        st.markdown("#### Needs review")
        if not df.empty:
            review = df[df["status"].isin(["Review", "Ready for Delivery"])][["order_id", "subject_address", "assigned_appraiser", "status"]]
            if not review.empty:
                st.dataframe(review, use_container_width=True, hide_index=True)
            else:
                st.info("Nothing sitting in review.")
        else:
            st.info("No orders yet.")

    st.markdown("#### Quick notes")
    st.write(
        "This build keeps the public-facing fluff out and focuses on the internal workflow: intake, report sections, QC, and workfile export."
    )


def order_picker(org_id: int, key: str = "order_pick") -> tuple[list[dict[str, Any]], str | None]:
    orders = db.list_orders(org_id)
    if not orders:
        return [], None
    order_ids = [order["order_id"] for order in orders]
    return orders, st.selectbox("Select order", order_ids, key=key)


def render_orders(org_id: int, user: dict[str, Any]) -> None:
    orders = db.list_orders(org_id)
    if not orders:
        st.info("No orders yet. Create one in New Order.")
        return

    df = pd.DataFrame(orders)
    f1, f2 = st.columns([1, 2])
    with f1:
        status_filter = st.selectbox("Status", ["All"] + ORDER_STATUSES, key="order_status_filter")
    with f2:
        search_text = st.text_input("Search address / client / order", key="order_search")

    if status_filter != "All":
        df = df[df["status"] == status_filter]
    if search_text:
        mask = (
            df["subject_address"].str.contains(search_text, case=False, na=False)
            | df["client_name"].str.contains(search_text, case=False, na=False)
            | df["order_id"].str.contains(search_text, case=False, na=False)
        )
        df = df[mask]

    if df.empty:
        st.info("No matching orders.")
        return

    st.dataframe(
        df[["order_id", "subject_address", "client_name", "assigned_appraiser", "status", "due_date", "fee"]],
        use_container_width=True,
        hide_index=True,
    )

    selected_order_id = st.selectbox("Open order", df["order_id"].tolist(), key="order_detail_pick")
    order = db.get_order(org_id, selected_order_id)
    if not order:
        st.warning("Could not load that order.")
        return

    st.markdown("---")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Overview")
        st.write(f"**Property:** {order['subject_address']}, {order['city']}, {order['state']} {order['zip_code']}")
        st.write(f"**Client:** {order.get('client_name', '')}")
        st.write(f"**Borrower:** {order.get('borrower_name', '') or '—'}")
        st.write(f"**Lender:** {order.get('lender_name', '') or '—'}")
        st.write(f"**Loan #:** {order.get('loan_number', '') or '—'}")
        st.write(f"**Assigned appraiser:** {order.get('assigned_appraiser', '') or '—'}")
        st.write(f"**Fee:** ${parse_money(order.get('fee')):,.2f}")
        st.write(f"**Status:** {order.get('status', '')}")
        st.write(f"**Prelim value:** {order.get('value_opinion', '') or '—'}")

    with right:
        st.markdown("#### Property details")
        props = order.get("property_details") or {}
        property_lines = []
        for key in [
            "year_built",
            "gla_sqft",
            "total_rooms",
            "bedrooms",
            "bathrooms",
            "condition_rating",
            "quality_rating",
            "lot_area",
            "zoning",
            "garage_type",
            "flood_zone",
            "flood_map_id",
        ]:
            if props.get(key):
                property_lines.append(f"**{key.replace('_', ' ').title()}:** {props.get(key)}")
        if property_lines:
            st.markdown("\n\n".join(property_lines))
        else:
            st.caption("No property details yet.")

    if order.get("field_notes"):
        with st.expander("Field notes", expanded=False):
            st.write(order["field_notes"])

    files = db.list_files(org_id, selected_order_id)
    if files:
        with st.expander("Photos and documents", expanded=False):
            image_files = [item for item in files if item.get("kind") == "photo" or str(item.get("mime_type", "")).startswith("image/")]
            doc_files = [item for item in files if item not in image_files]
            if image_files:
                cols = st.columns(min(4, len(image_files)))
                for idx, item in enumerate(image_files):
                    path = Path(item["stored_path"])
                    if path.exists():
                        cols[idx % len(cols)].image(str(path), caption=item["original_name"], use_container_width=True)
            if doc_files:
                st.markdown("**Documents**")
                for item in doc_files:
                    st.write(f"• {item['original_name']}")

    sections = db.get_sections(org_id, selected_order_id)
    if sections:
        with st.expander("Saved sections", expanded=False):
            for item in sorted(sections, key=lambda x: x.get("section_name", "")):
                text = (item.get("human_edited") or item.get("ai_draft") or "").strip()
                st.markdown(f"**{item['section_name']}**")
                st.caption(f"Review status: {item.get('review_status', 'draft')}")
                if text:
                    st.write(text[:1200] + ("..." if len(text) > 1200 else ""))
                st.divider()

    h1, h2 = st.columns([1, 2])
    with h1:
        with st.form("status_update_form"):
            new_status = st.selectbox(
                "Update status",
                ORDER_STATUSES,
                index=option_index(ORDER_STATUSES, order.get("status", "Pending")),
            )
            reason = st.text_input("Reason / note", value="")
            status_submit = st.form_submit_button("Save status", use_container_width=True)
            if status_submit:
                db.update_order_status(org_id, selected_order_id, new_status, user.get("name", ""), reason)
                st.success("Status updated.")
                st.rerun()

    with h2:
        workfile_bytes = build_workfile_bundle(
            order=order,
            sections=sections,
            files=files,
            review_items=db.get_review_items(org_id, selected_order_id),
            checklist=db.get_qc_checklist(org_id, selected_order_id),
            activity=db.get_activity(org_id, selected_order_id, limit=250),
            status_history=db.get_status_history(org_id, selected_order_id),
        )
        st.caption("Export a workfile bundle with sections, QC, activity, and local attachments.")
        st.download_button(
            "Download workfile bundle (.zip)",
            data=workfile_bytes,
            file_name=f"{selected_order_id}_workfile_bundle.zip",
            mime="application/zip",
            use_container_width=True,
        )


def run_document_extract(doc_type: str, uploaded_file: Any, org_settings: dict[str, str]) -> None:
    api_key = ai.get_secret("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY is missing. Put it in st.secrets or the environment.")
        return
    model = org_settings.get("ai_model") or ai.get_default_model()
    with st.spinner("Reading document..."):
        try:
            data, usage = ai.extract_document(uploaded_file, doc_type=doc_type, model=model, api_key=api_key)
        except Exception as exc:
            st.error(f"Extraction failed: {exc}")
            return
    if doc_type == "purchase":
        st.session_state.purchase_extract = data
    else:
        st.session_state.engagement_extract = data
    st.success("Document extracted.")
    with st.expander("Extracted data", expanded=False):
        st.json({"data": data, "usage": usage})


def render_new_order(org_id: int, user: dict[str, Any], settings: dict[str, str]) -> None:
    st.markdown("#### Quick import")
    st.caption("These buttons are outside the order form so the page behaves correctly on rerun.")
    e1, e2 = st.columns(2)
    with e1:
        eng_file = st.file_uploader(
            "Engagement letter / order form",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            key="engagement_upload",
        )
        if eng_file and st.button("Extract engagement data", key="extract_engagement_btn", use_container_width=True):
            run_document_extract("engagement", eng_file, settings)

    with e2:
        ps_file = st.file_uploader(
            "Purchase & sale agreement",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            key="purchase_upload",
        )
        if ps_file and st.button("Extract purchase data", key="extract_purchase_btn", use_container_width=True):
            run_document_extract("purchase", ps_file, settings)

    defaults = merged_defaults()
    st.divider()
    with st.form("new_order_form", clear_on_submit=False):
        st.markdown("#### Core order data")
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("Client name *", value=defaults.get("client_name", ""))
            client_email = st.text_input("Client email *", value=defaults.get("client_email", ""))
            client_phone = st.text_input("Client phone", value=defaults.get("client_phone", ""))
            borrower_name = st.text_input("Borrower / buyer", value=defaults.get("borrower_name", ""))
        with c2:
            lender_name = st.text_input("Lender", value=defaults.get("lender_name", ""))
            loan_number = st.text_input("Loan number", value=defaults.get("loan_number", ""))
            assigned_appraiser = st.text_input(
                "Assigned appraiser",
                value=settings.get("default_assignee", "") or user.get("name", ""),
            )
            fee = st.number_input("Fee", min_value=0.0, step=25.0, value=parse_money(defaults.get("fee")))

        st.markdown("#### Subject property")
        p1, p2 = st.columns(2)
        with p1:
            subject_address = st.text_input("Subject address *", value=defaults.get("subject_address", ""))
            city = st.text_input("City *", value=defaults.get("city", ""))
            zip_code = st.text_input("ZIP", value=defaults.get("zip_code", ""))
        with p2:
            state_options = ["RI", "MA", "CT", "NH", "VT", "ME", "NY", "Other"]
            state = st.selectbox("State", state_options, index=option_index(state_options, defaults.get("state", "RI")))
            property_type = st.selectbox(
                "Property type",
                PROPERTY_TYPES,
                index=option_index(PROPERTY_TYPES, defaults.get("property_type", "Single Family")),
            )
            appraisal_type = st.selectbox(
                "Appraisal type",
                APPRAISAL_TYPES,
                index=option_index(APPRAISAL_TYPES, defaults.get("appraisal_type", "1004")),
            )
            form_type = st.selectbox(
                "Form type",
                FORM_TYPES,
                index=option_index(FORM_TYPES, defaults.get("form_type", "URAR")),
            )

        st.markdown("#### Schedule and notes")
        s1, s2, s3 = st.columns(3)
        with s1:
            due_date = st.date_input("Due date", value=parse_date(defaults.get("due_date", date.today())))
        with s2:
            inspection_date = st.date_input("Inspection date", value=parse_date(defaults.get("inspection_date", date.today())))
        with s3:
            value_opinion = st.text_input("Prelim value / contract price", value=defaults.get("purchase_price", defaults.get("value_opinion", "")))

        field_notes = st.text_area(
            "Field notes / scope notes",
            value=defaults.get("field_notes", ""),
            placeholder="Facts only. Inspection notes, client instructions, occupancy, updates, etc.",
            height=120,
        )

        props = defaults
        st.markdown("#### Property details")
        pd1, pd2, pd3 = st.columns(3)
        with pd1:
            year_built = st.text_input("Year built", value=props.get("year_built", ""))
            stories = st.text_input("Stories", value=props.get("stories", ""))
            design_style = st.text_input("Design / style", value=props.get("design_style", ""))
            exterior_desc = st.text_input("Exterior", value=props.get("exterior_desc", ""))
            foundation_type = st.selectbox(
                "Foundation",
                FOUNDATION_TYPES,
                index=option_index(FOUNDATION_TYPES, props.get("foundation_type", "")),
            )
            basement_sqft = st.text_input("Basement sqft", value=props.get("basement_sqft", ""))
            basement_finished_pct = st.text_input("Basement finished %", value=props.get("basement_finished_pct", ""))
        with pd2:
            total_rooms = st.text_input("Total rooms", value=props.get("total_rooms", ""))
            bedrooms = st.text_input("Bedrooms", value=props.get("bedrooms", ""))
            bathrooms = st.text_input("Bathrooms", value=props.get("bathrooms", ""))
            gla_sqft = st.text_input("GLA sqft", value=props.get("gla_sqft", ""))
            heating_type = st.text_input("Heating", value=props.get("heating_type", ""))
            cooling_type = st.text_input("Cooling", value=props.get("cooling_type", ""))
            condition_rating = st.selectbox(
                "Condition",
                CONDITION_RATINGS,
                index=option_index(CONDITION_RATINGS, props.get("condition_rating", "")),
            )
        with pd3:
            quality_rating = st.selectbox(
                "Quality",
                QUALITY_RATINGS,
                index=option_index(QUALITY_RATINGS, props.get("quality_rating", "")),
            )
            lot_dimensions = st.text_input("Lot dimensions", value=props.get("lot_dimensions", ""))
            lot_area = st.text_input("Lot area", value=props.get("lot_area", ""))
            zoning = st.text_input("Zoning", value=props.get("zoning", ""))
            garage_type = st.selectbox(
                "Garage",
                GARAGE_TYPES,
                index=option_index(GARAGE_TYPES, props.get("garage_type", "None")),
            )
            county = st.text_input("County", value=props.get("county", ""))
            neighborhood_name = st.text_input("Neighborhood", value=props.get("neighborhood_name", ""))

        pd4, pd5 = st.columns(2)
        with pd4:
            assessor_parcel = st.text_input("Assessor parcel", value=props.get("assessor_parcel", ""))
            tax_year = st.text_input("Tax year", value=props.get("tax_year", ""))
            tax_amount = st.text_input("Annual taxes", value=props.get("tax_amount", ""))
            utilities = st.text_input("Utilities", value=props.get("utilities", ""))
        with pd5:
            flood_zone = st.text_input("Flood zone", value=props.get("flood_zone", ""))
            flood_map_id = st.text_input("Flood map ID", value=props.get("flood_map_id", ""))
            legal_desc = st.text_input("Legal description", value=props.get("legal_desc", ""))

        st.markdown("#### Attachments")
        uploaded_photos = st.file_uploader("Photos", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        uploaded_docs = st.file_uploader("Supporting docs", type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

        submit = st.form_submit_button("Create order", use_container_width=True)
        if submit:
            if not client_name or not client_email or not subject_address or not city:
                st.error("Client, email, subject address, and city are required.")
            else:
                order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                order_payload = {
                    "order_id": order_id,
                    "client_name": client_name,
                    "client_email": client_email,
                    "client_phone": client_phone,
                    "borrower_name": borrower_name,
                    "lender_name": lender_name,
                    "loan_number": loan_number,
                    "subject_address": subject_address,
                    "city": city,
                    "state": state,
                    "zip_code": zip_code,
                    "property_type": property_type,
                    "appraisal_type": appraisal_type,
                    "form_type": form_type,
                    "assigned_appraiser": assigned_appraiser,
                    "fee": fee,
                    "due_date": due_date.isoformat(),
                    "inspection_date": inspection_date.isoformat(),
                    "status": "Pending",
                    "value_opinion": value_opinion,
                    "field_notes": field_notes,
                }
                property_details = {
                    "year_built": year_built,
                    "stories": stories,
                    "design_style": design_style,
                    "exterior_desc": exterior_desc,
                    "foundation_type": foundation_type,
                    "basement_sqft": basement_sqft,
                    "basement_finished_pct": basement_finished_pct,
                    "total_rooms": total_rooms,
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "gla_sqft": gla_sqft,
                    "heating_type": heating_type,
                    "cooling_type": cooling_type,
                    "condition_rating": condition_rating,
                    "quality_rating": quality_rating,
                    "lot_dimensions": lot_dimensions,
                    "lot_area": lot_area,
                    "zoning": zoning,
                    "garage_type": garage_type,
                    "county": county,
                    "neighborhood_name": neighborhood_name,
                    "assessor_parcel": assessor_parcel,
                    "tax_year": tax_year,
                    "tax_amount": tax_amount,
                    "flood_zone": flood_zone,
                    "flood_map_id": flood_map_id,
                    "legal_desc": legal_desc,
                    "utilities": utilities,
                }
                db.create_order(
                    org_id,
                    order_payload,
                    property_details,
                    extracted_data={
                        "engagement": st.session_state.get("engagement_extract") or {},
                        "purchase": st.session_state.get("purchase_extract") or {},
                    },
                    created_by=user.get("name", ""),
                )

                for photo in uploaded_photos or []:
                    db.save_uploaded_file(org_id, order_id, photo, "photo")
                for doc in uploaded_docs or []:
                    db.save_uploaded_file(org_id, order_id, doc, "document")

                clear_extract_state()
                st.success(f"Created {order_id}")
                st.rerun()


def render_report_writer(org_id: int, settings: dict[str, str]) -> None:
    orders, selected_order_id = order_picker(org_id, key="writer_order_pick")
    if not orders or not selected_order_id:
        st.info("Create an order first.")
        return

    order = db.get_order(org_id, selected_order_id)
    if not order:
        st.warning("Order not found.")
        return

    st.write(f"**Property:** {order['subject_address']}, {order['city']}, {order['state']} {order['zip_code']}")
    st.write(f"**Notes:** {order.get('field_notes', '') or '—'}")
    model = settings.get("ai_model") or ai.get_default_model()
    st.caption(f"AI model setting: {model}")

    api_key = ai.get_secret("OPENAI_API_KEY")
    if not api_key:
        st.warning("OPENAI_API_KEY is missing. Add it to st.secrets or the environment to use AI.")
    else:
        g1, g2 = st.columns([1, 1])
        with g1:
            section_to_generate = st.selectbox("Section to generate", DEFAULT_SECTIONS, key="section_to_generate")
        with g2:
            st.caption("The writer only uses supplied facts. Missing facts stay bracketed.")
            if st.button("Generate section", key="generate_section_button", use_container_width=True):
                with st.spinner(f"Generating {section_to_generate}..."):
                    try:
                        text, usage, evidence = ai.generate_section(order, section_to_generate, model=model, api_key=api_key)
                    except Exception as exc:
                        st.error(f"Generation failed: {exc}")
                    else:
                        db.save_section(
                            org_id,
                            selected_order_id,
                            section_to_generate,
                            ai_draft=text,
                            evidence=evidence,
                            review_status="draft",
                        )
                        db.log_ai_run(
                            org_id,
                            selected_order_id,
                            run_type="section_draft",
                            section_name=section_to_generate,
                            prompt_summary=f"Generate {section_to_generate}",
                            input_payload=ai.build_order_facts(order),
                            output_text=text,
                            model=model,
                            usage=usage,
                        )
                        st.success(f"Saved {section_to_generate}.")
                        st.rerun()

        if st.button("Generate all missing sections", key="generate_all_missing", use_container_width=True):
            sections_now = {item["section_name"]: item for item in db.get_sections(org_id, selected_order_id)}
            generated = 0
            with st.spinner("Generating missing sections..."):
                for section_name in DEFAULT_SECTIONS:
                    existing = sections_now.get(section_name, {})
                    if (existing.get("human_edited") or existing.get("ai_draft")):
                        continue
                    try:
                        text, usage, evidence = ai.generate_section(order, section_name, model=model, api_key=api_key)
                    except Exception as exc:
                        st.error(f"Stopped on {section_name}: {exc}")
                        break
                    db.save_section(org_id, selected_order_id, section_name, ai_draft=text, evidence=evidence, review_status="draft")
                    db.log_ai_run(
                        org_id,
                        selected_order_id,
                        run_type="section_draft",
                        section_name=section_name,
                        prompt_summary=f"Generate {section_name}",
                        input_payload=ai.build_order_facts(order),
                        output_text=text,
                        model=model,
                        usage=usage,
                    )
                    generated += 1
            if generated:
                st.success(f"Generated {generated} section(s).")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Saved sections")
    sections = {item["section_name"]: item for item in db.get_sections(org_id, selected_order_id)}
    if not sections:
        st.info("No sections saved yet.")
    for section_name in DEFAULT_SECTIONS:
        current = sections.get(section_name, {})
        body = current.get("human_edited") or current.get("ai_draft") or ""
        with st.expander(section_name, expanded=False):
            if current.get("evidence"):
                st.markdown("".join([f'<span class="section-chip">{e["field"]}</span>' for e in current["evidence"][:8]]), unsafe_allow_html=True)
            with st.form(f"save_section_{selected_order_id}_{section_name}"):
                edited = st.text_area("Section text", value=body, height=220, key=f"text_{selected_order_id}_{section_name}")
                review_status = st.selectbox(
                    "Review status",
                    ["draft", "reviewed", "final"],
                    index=option_index(["draft", "reviewed", "final"], current.get("review_status", "draft")),
                    key=f"review_status_{selected_order_id}_{section_name}",
                )
                reviewer_notes = st.text_input(
                    "Reviewer notes",
                    value=current.get("reviewer_notes", ""),
                    key=f"reviewer_notes_{selected_order_id}_{section_name}",
                )
                save_section_btn = st.form_submit_button("Save section")
                if save_section_btn:
                    db.save_section(
                        org_id,
                        selected_order_id,
                        section_name,
                        human_edited=edited,
                        review_status=review_status,
                        reviewer_notes=reviewer_notes,
                    )
                    st.success("Section saved.")
                    st.rerun()

    if sections:
        assembled = ai.assemble_addendum(sections)
        st.markdown("---")
        st.markdown("#### Addendum preview")
        st.text_area("Assembled report text", value=assembled, height=280, key="assembled_preview")
        st.download_button(
            "Download assembled markdown",
            data=assembled.encode("utf-8"),
            file_name=f"{selected_order_id}_assembled_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

        with st.expander("AI run log", expanded=False):
            runs = db.get_ai_runs(org_id, selected_order_id)
            if not runs:
                st.caption("No AI runs logged.")
            for item in runs:
                st.markdown(f"**{item['created_at']} — {item.get('run_type')} / {item.get('section_name') or 'n/a'}**")
                st.caption(f"Model: {item.get('model', '')}")
                usage = item.get("usage_json") or {}
                if usage:
                    st.json(usage)
                st.divider()


def render_qc(org_id: int, user: dict[str, Any], settings: dict[str, str]) -> None:
    orders, selected_order_id = order_picker(org_id, key="qc_order_pick")
    if not orders or not selected_order_id:
        st.info("Create an order first.")
        return
    order = db.get_order(org_id, selected_order_id)
    if not order:
        st.warning("Order not found.")
        return

    sections = db.get_sections(org_id, selected_order_id)
    checklist_values = db.get_qc_checklist(org_id, selected_order_id)
    review_items = db.get_review_items(org_id, selected_order_id)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### QC checklist")
        with st.form("qc_checklist_form"):
            updated_items: dict[str, bool] = {}
            for item_key, label in QC_CHECKLIST_ITEMS:
                updated_items[item_key] = st.checkbox(label, value=checklist_values.get(item_key, False))
            checklist_submit = st.form_submit_button("Save checklist")
            if checklist_submit:
                for item_key, is_complete in updated_items.items():
                    db.set_qc_item(org_id, selected_order_id, item_key, is_complete)
                st.success("Checklist saved.")
                st.rerun()

        completed_sections = sum(1 for item in sections if (item.get("human_edited") or item.get("ai_draft")))
        st.caption(f"Saved sections: {completed_sections}/{len(DEFAULT_SECTIONS)}")

    with right:
        st.markdown("#### Add revision / QC item")
        with st.form("review_item_form"):
            item_type = st.selectbox(
                "Type",
                ["Missing Data", "Unsupported Adjustment", "Photo Issue", "Compliance", "Narrative", "Other"],
            )
            description = st.text_area("Description", placeholder="What needs to change?")
            add_item = st.form_submit_button("Add item")
            if add_item and description.strip():
                db.add_review_item(org_id, selected_order_id, user.get("name", ""), item_type, description.strip())
                st.success("Review item added.")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Review items")
    if not review_items:
        st.info("No review items yet.")
    for item in review_items:
        with st.expander(f"{item['item_type']} — {item['status'].upper()}"):
            st.write(item["description"])
            with st.form(f"review_item_update_{item['id']}"):
                response = st.text_area("Response / resolution", value=item.get("response", ""))
                status = st.selectbox(
                    "Status",
                    ["open", "pending", "resolved"],
                    index=option_index(["open", "pending", "resolved"], item.get("status", "open")),
                )
                save_item = st.form_submit_button("Save response")
                if save_item and response.strip():
                    db.update_review_item(org_id, item["id"], status, response.strip())
                    st.success("Review item updated.")
                    st.rerun()

    api_key = ai.get_secret("OPENAI_API_KEY")
    open_items = [item for item in review_items if item.get("status") != "resolved"]
    if api_key and open_items:
        if st.button("Draft revision response", key="draft_revision_response", use_container_width=True):
            with st.spinner("Drafting revision response..."):
                try:
                    text, usage = ai.generate_revision_response(order, open_items, model=settings.get("ai_model") or ai.get_default_model(), api_key=api_key)
                except Exception as exc:
                    st.error(f"Could not draft revision response: {exc}")
                else:
                    db.save_section(org_id, selected_order_id, "Revision Response", ai_draft=text, review_status="draft")
                    db.log_ai_run(
                        org_id,
                        selected_order_id,
                        run_type="revision_response",
                        section_name="Revision Response",
                        prompt_summary="Draft revision response",
                        input_payload={"open_review_items": open_items},
                        output_text=text,
                        model=settings.get("ai_model") or ai.get_default_model(),
                        usage=usage,
                    )
                    st.success("Saved draft under section 'Revision Response'.")
                    st.rerun()

    all_checks = db.get_qc_checklist(org_id, selected_order_id)
    if all(all_checks.get(item_key, False) for item_key, _ in QC_CHECKLIST_ITEMS):
        if st.button("Mark ready for delivery", key="mark_ready", use_container_width=True):
            db.update_order_status(org_id, selected_order_id, "Ready for Delivery", user.get("name", ""), "QC checklist complete")
            st.success("Order marked Ready for Delivery.")
            st.rerun()


def render_activity(org_id: int) -> None:
    orders = db.list_orders(org_id)
    order_options = ["All"] + [item["order_id"] for item in orders]
    selected = st.selectbox("Filter activity by order", order_options, key="activity_order_filter")
    rows = db.get_activity(org_id, None if selected == "All" else selected, limit=200)
    if not rows:
        st.info("No activity yet.")
        return
    frame = pd.DataFrame(rows)
    st.dataframe(frame[["created_at", "order_id", "action", "details", "created_by"]], use_container_width=True, hide_index=True)


def render_tools() -> None:
    calc_tab, ext_tab = st.tabs(["🧮 Calculators", "🔗 External Tools"])

    with calc_tab:
        tool = st.selectbox("Calculator", ["GLA Calculator", "Net / Gross Adjustment Check"], key="tool_choice")

        if tool == "GLA Calculator":
            total = 0.0
            for level in range(1, 5):
                with st.expander(f"Level {level}", expanded=(level == 1)):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        length = st.number_input(f"Length (ft) — L{level}", min_value=0.0, value=0.0, step=1.0)
                    with c2:
                        width = st.number_input(f"Width (ft) — W{level}", min_value=0.0, value=0.0, step=1.0)
                    area = length * width
                    with c3:
                        st.metric("Area", f"{area:,.0f} sqft")
                    total += area
            st.success(f"Total GLA: {total:,.0f} sqft")

        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                sale_price = st.number_input("Sale price", min_value=0.0, value=0.0, step=1000.0)
                total_adjustments = st.number_input("Total adjustments", min_value=0.0, value=0.0, step=1000.0)
            with c2:
                net_adjustments = st.number_input("Net adjustments", value=0.0, step=1000.0)
            gross_pct = (total_adjustments / sale_price * 100) if sale_price else 0.0
            net_pct = (net_adjustments / sale_price * 100) if sale_price else 0.0
            with c3:
                st.metric("Gross %", f"{gross_pct:.1f}%")
                st.metric("Net %", f"{net_pct:.1f}%")

    with ext_tab:
        render_external_tools()


def render_str_reports() -> None:
    st.markdown("#### Short-Term Rental Income Analysis")
    st.write(
        "Generate AirDNA-powered STR income analysis reports for appraisal work. "
        "The generator runs on a separate service and produces branded PDF reports."
    )
    st.link_button(
        "Open STR Report Generator",
        "https://avm-str-generator.onrender.com",
        use_container_width=True,
    )
    st.divider()
    st.markdown("#### How it works")
    st.write(
        "1. Enter the subject property address and AirDNA market data. "
        "2. The tool calculates projected STR income using local comps. "
        "3. Download a branded PDF report suitable for inclusion in appraisal addenda."
    )


def render_ai_advisor(settings: dict[str, str]) -> None:
    api_key = ai.get_secret("OPENAI_API_KEY")
    if not api_key:
        st.warning("OPENAI_API_KEY is missing. Add it to st.secrets or environment to use the advisor.")
        return

    st.markdown("#### Appraisal Advisor")
    st.caption("Ask questions about USPAP, Fannie Mae guidelines, FHA/HUD, methodology, adjustments, or general practice.")

    if "advisor_messages" not in st.session_state:
        st.session_state.advisor_messages = []

    for msg in st.session_state.advisor_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Ask an appraisal question...", key="advisor_input")
    if prompt:
        st.session_state.advisor_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    model = settings.get("ai_model") or ai.get_default_model()
                    reply, _usage = ai.advisor_chat(
                        st.session_state.advisor_messages,
                        model=model,
                        api_key=api_key,
                    )
                except Exception as exc:
                    reply = f"Error: {exc}"
                st.write(reply)
        st.session_state.advisor_messages.append({"role": "assistant", "content": reply})


def render_external_tools() -> None:
    st.markdown("#### External appraisal tools")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="tool-card">'
            "<h4>🏘️ MLS Grid</h4>"
            "<p>Access MLS data, comp searches, and listing history for properties in your market area.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.link_button("Open MLS Grid", "https://www.mlsgrid.com", use_container_width=True)

        st.markdown(
            '<div class="tool-card">'
            "<h4>🗺️ FEMA Flood Maps</h4>"
            "<p>Look up FEMA flood zone designations, map panels, and community information for any property.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.link_button("Open FEMA Flood Map", "https://msc.fema.gov/portal/search", use_container_width=True)

    with c2:
        st.markdown(
            '<div class="tool-card">'
            "<h4>🏛️ County Records</h4>"
            "<p>Search county recorder and assessor databases for deeds, transfers, tax records, and property data.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.link_button("Open County Records", "https://www.netronline.com", use_container_width=True)

        st.markdown(
            '<div class="tool-card">'
            "<h4>📊 Census Data</h4>"
            "<p>Access US Census Bureau demographic, housing, and economic data for neighborhood analysis.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.link_button("Open Census Data", "https://data.census.gov", use_container_width=True)


def render_settings(org_id: int, user: dict[str, Any], settings: dict[str, str]) -> None:
    t1, t2, t3 = st.tabs(["Company", "Users", "Migration"])

    with t1:
        st.markdown("#### Company settings")
        with st.form("company_settings_form"):
            company_name = st.text_input("Company name", value=settings.get("company_name", ""))
            company_address = st.text_input("Company address", value=settings.get("company_address", ""))
            company_phone = st.text_input("Company phone", value=settings.get("company_phone", ""))
            ai_model = st.text_input("AI model", value=settings.get("ai_model", ai.get_default_model()))
            default_assignee = st.text_input("Default assignee", value=settings.get("default_assignee", ""))
            save_company = st.form_submit_button("Save company settings")
            if save_company:
                db.save_settings(
                    org_id,
                    {
                        "company_name": company_name,
                        "company_address": company_address,
                        "company_phone": company_phone,
                        "ai_model": ai_model,
                        "default_assignee": default_assignee,
                    },
                )
                st.success("Settings saved.")
                st.rerun()

        secret_status = "found" if ai.get_secret("OPENAI_API_KEY") else "missing"
        st.info(
            "OPENAI_API_KEY status: "
            f"{secret_status}. Put secrets in `.streamlit/secrets.toml` or environment variables. "
            "This build does not store API keys in SQLite."
        )

    with t2:
        st.markdown("#### Users")
        users = db.list_users(org_id)
        if users:
            st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

        if user.get("role") == "admin":
            with st.form("create_user_form"):
                name = st.text_input("Name")
                email = st.text_input("Email")
                role = st.selectbox("Role", ["appraiser", "reviewer", "admin"])
                password = st.text_input("Temporary password", type="password")
                create_user_submit = st.form_submit_button("Create user")
                if create_user_submit:
                    ok, message = db.create_user(org_id, name, email, password, role=role)
                    if ok:
                        st.success(message)
                        st.rerun()
                    st.error(message)
        else:
            st.caption("Only admins can add users.")

    with t3:
        st.markdown("#### Import legacy data")
        default_path = str(Path.cwd() / "a_tech_appraisals.db")
        with st.form("legacy_import_form"):
            legacy_path = st.text_input("Legacy SQLite path", value=default_path)
            import_submit = st.form_submit_button("Import legacy orders")
            if import_submit:
                count, messages = db.import_legacy_orders(org_id, legacy_path, changed_by=user.get("name", ""))
                if count:
                    st.success(messages[0])
                for message in messages[1:] if messages else []:
                    st.caption(message)
                if not count and messages:
                    st.error(messages[0])


def main() -> None:
    inject_css()
    db.init_db()
    init_session_state()
    user = require_login()
    org_id = int(user["organization_id"])
    settings = db.get_settings(org_id)

    with st.sidebar:
        st.markdown(f"### {APP_NAME}")
        st.caption(user.get("email", ""))
        st.caption(f"Role: {user.get('role', '').title()}")
        st.caption(f"Org: {settings.get('company_name', '—')}")
        if st.button("Logout", use_container_width=True):
            st.session_state.auth_user = None
            st.rerun()

    hero(user, settings)

    (tab_home, tab_orders, tab_new, tab_writer, tab_qc, tab_str,
     tab_advisor, tab_activity, tab_tools, tab_settings) = st.tabs(
        [
            "🏠 Home", "📋 Orders", "📝 New Order", "🤖 Report Writer",
            "🔎 QC Review", "📈 STR Reports", "💡 AI Advisor",
            "🕘 Activity", "🧮 Tools", "⚙️ Settings",
        ]
    )

    with tab_home:
        render_home(user, org_id)
    with tab_orders:
        render_orders(org_id, user)
    with tab_new:
        render_new_order(org_id, user, settings)
    with tab_writer:
        render_report_writer(org_id, settings)
    with tab_qc:
        render_qc(org_id, user, settings)
    with tab_str:
        render_str_reports()
    with tab_advisor:
        render_ai_advisor(settings)
    with tab_activity:
        render_activity(org_id)
    with tab_tools:
        render_tools()
    with tab_settings:
        render_settings(org_id, user, settings)

    st.markdown(
        '<div class="branded-footer">'
        "Powered by <strong>A-Tech Appraisal Co., LLC</strong> &bull; Warwick, RI<br>"
        "AppraisalOS is the complete platform for modern appraisers"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
