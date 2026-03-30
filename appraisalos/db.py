
from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import COMPANY_SETTINGS_DEFAULTS, DB_PATH, STORAGE_DIR
from .security import hash_password, new_salt, verify_password


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'appraiser',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                organization_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (organization_id, key),
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT UNIQUE NOT NULL,
                client_name TEXT,
                client_email TEXT,
                client_phone TEXT,
                borrower_name TEXT,
                lender_name TEXT,
                loan_number TEXT,
                subject_address TEXT NOT NULL,
                city TEXT,
                state TEXT DEFAULT 'RI',
                zip_code TEXT,
                property_type TEXT,
                appraisal_type TEXT DEFAULT '1004',
                form_type TEXT DEFAULT 'URAR',
                assigned_appraiser TEXT,
                fee REAL DEFAULT 0,
                due_date TEXT,
                inspection_date TEXT,
                status TEXT DEFAULT 'Pending',
                value_opinion TEXT,
                field_notes TEXT,
                extracted_data_json TEXT DEFAULT '{}',
                property_details_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                mime_type TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS report_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                section_name TEXT NOT NULL,
                ai_draft TEXT,
                human_edited TEXT,
                evidence_json TEXT DEFAULT '[]',
                review_status TEXT DEFAULT 'draft',
                reviewer_notes TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(order_id, section_name),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS review_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                reviewer_name TEXT,
                item_type TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                response TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS qc_checklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                item_key TEXT NOT NULL,
                is_complete INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(order_id, item_key),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS ai_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                run_type TEXT NOT NULL,
                section_name TEXT,
                prompt_summary TEXT,
                input_json TEXT,
                output_text TEXT,
                model TEXT,
                usage_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_by TEXT,
                reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id TEXT,
                action TEXT NOT NULL,
                details TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            );
            """
        )
        conn.commit()
    seed_demo_if_needed()


def seed_demo_if_needed() -> None:
    now = datetime.utcnow().isoformat()
    with closing(connect()) as conn:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count:
            return

        conn.execute(
            "INSERT INTO organizations (name, created_at) VALUES (?, ?)",
            ("Demo Appraisal Co.", now),
        )
        org_id = conn.execute("SELECT id FROM organizations ORDER BY id DESC LIMIT 1").fetchone()[0]

        salt = new_salt()
        conn.execute(
            """
            INSERT INTO users (email, name, password_hash, salt, organization_id, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo@appraisalos.local",
                "Demo Admin",
                hash_password("demo123", salt),
                salt,
                org_id,
                "admin",
                now,
            ),
        )

        for key, value in COMPANY_SETTINGS_DEFAULTS.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (organization_id, key, value) VALUES (?, ?, ?)",
                (org_id, key, str(value)),
            )

        sample_order_id = "ORD-DEMO-1001"
        property_details = {
            "year_built": "1998",
            "stories": "2",
            "design_style": "Colonial",
            "exterior_desc": "Vinyl siding",
            "foundation_type": "Full Basement",
            "basement_sqft": "950",
            "basement_finished_pct": "20",
            "total_rooms": "8",
            "bedrooms": "4",
            "bathrooms": "2.5",
            "gla_sqft": "2240",
            "heating_type": "FWA / Gas",
            "cooling_type": "Central AC",
            "condition_rating": "C3",
            "quality_rating": "Q4",
            "lot_dimensions": "100 x 150",
            "lot_area": "15000",
            "zoning": "A-7",
            "garage_type": "2-Car Attached",
            "county": "Kent",
            "neighborhood_name": "Buttonwoods",
            "assessor_parcel": "000-0000",
            "tax_year": "2025",
            "tax_amount": "6900",
            "flood_zone": "X",
            "flood_map_id": "44003C0126J",
            "legal_desc": "Lot 42, Plat 18",
            "utilities": "Public water, public sewer, electric, gas",
        }
        conn.execute(
            """
            INSERT INTO orders (
                organization_id, order_id, client_name, client_email, client_phone, borrower_name,
                lender_name, loan_number, subject_address, city, state, zip_code,
                property_type, appraisal_type, form_type, assigned_appraiser, fee,
                due_date, inspection_date, status, value_opinion, field_notes,
                extracted_data_json, property_details_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                org_id,
                sample_order_id,
                "Demo Client",
                "client@example.com",
                "(401) 555-1000",
                "Jordan Borrower",
                "Demo Lender",
                "LN-1001",
                "123 Main St",
                "Warwick",
                "RI",
                "02886",
                "Single Family",
                "1004",
                "URAR",
                "Demo Admin",
                650.0,
                now[:10],
                now[:10],
                "Review",
                "575000",
                "Occupied single-family home. Typical suburban setting. Kitchen updated in recent years; basement partly finished.",
                json.dumps({"source": "seed"}),
                json.dumps(property_details),
                now,
                now,
            ),
        )

        add_activity(
            conn,
            org_id=org_id,
            order_id=sample_order_id,
            action="Seeded demo order",
            details="Created starter data so the app has something to review.",
            created_by="system",
        )

        conn.commit()


def add_activity(
    conn: sqlite3.Connection,
    org_id: int,
    action: str,
    details: str = "",
    created_by: str = "",
    order_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO activity_log (organization_id, order_id, action, details, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (org_id, order_id, action, details, created_by, datetime.utcnow().isoformat()),
    )


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),)).fetchone()
    return _row_to_dict(row)


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = get_user_by_email(email)
    if not user or not user.get("is_active"):
        return None
    if not verify_password(password, user["salt"], user["password_hash"]):
        return None
    with closing(connect()) as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user["id"]),
        )
        conn.commit()
    return get_user_by_email(email)


def create_user(
    organization_id: int,
    name: str,
    email: str,
    password: str,
    role: str = "appraiser",
) -> tuple[bool, str]:
    email = email.strip().lower()
    if not email or not password or not name.strip():
        return False, "Name, email, and password are required."
    if get_user_by_email(email):
        return False, "That email is already in use."
    salt = new_salt()
    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT INTO users (email, name, password_hash, salt, organization_id, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                name.strip(),
                hash_password(password, salt),
                salt,
                organization_id,
                role,
                datetime.utcnow().isoformat(),
            ),
        )
        add_activity(conn, organization_id, "Created user", details=email, created_by="system")
        conn.commit()
    return True, "User created."


def list_users(organization_id: int) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, email, name, role, is_active, created_at, last_login
            FROM users
            WHERE organization_id = ?
            ORDER BY name
            """,
            (organization_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_settings(organization_id: int) -> dict[str, str]:
    values = dict(COMPANY_SETTINGS_DEFAULTS)
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE organization_id = ?",
            (organization_id,),
        ).fetchall()
    for row in rows:
        values[row["key"]] = row["value"]
    return values


def save_settings(organization_id: int, values: dict[str, Any]) -> None:
    with closing(connect()) as conn:
        for key, value in values.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (organization_id, key, value) VALUES (?, ?, ?)",
                (organization_id, key, str(value)),
            )
        add_activity(conn, organization_id, "Updated settings", created_by="user")
        conn.commit()


def create_order(
    organization_id: int,
    order_data: dict[str, Any],
    property_details: dict[str, Any],
    extracted_data: dict[str, Any] | None = None,
    created_by: str = "",
) -> str:
    order_id = order_data["order_id"]
    now = datetime.utcnow().isoformat()
    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT INTO orders (
                organization_id, order_id, client_name, client_email, client_phone, borrower_name,
                lender_name, loan_number, subject_address, city, state, zip_code,
                property_type, appraisal_type, form_type, assigned_appraiser, fee, due_date,
                inspection_date, status, value_opinion, field_notes, extracted_data_json,
                property_details_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                order_id,
                order_data.get("client_name", ""),
                order_data.get("client_email", ""),
                order_data.get("client_phone", ""),
                order_data.get("borrower_name", ""),
                order_data.get("lender_name", ""),
                order_data.get("loan_number", ""),
                order_data.get("subject_address", ""),
                order_data.get("city", ""),
                order_data.get("state", "RI"),
                order_data.get("zip_code", ""),
                order_data.get("property_type", ""),
                order_data.get("appraisal_type", "1004"),
                order_data.get("form_type", "URAR"),
                order_data.get("assigned_appraiser", ""),
                float(order_data.get("fee") or 0),
                order_data.get("due_date"),
                order_data.get("inspection_date"),
                order_data.get("status", "Pending"),
                order_data.get("value_opinion", ""),
                order_data.get("field_notes", ""),
                json.dumps(extracted_data or {}, ensure_ascii=False),
                json.dumps(property_details or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO status_history (organization_id, order_id, old_status, new_status, changed_by, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (organization_id, order_id, None, order_data.get("status", "Pending"), created_by, "Order created", now),
        )
        add_activity(conn, organization_id, "Created order", details=order_data.get("subject_address", ""), created_by=created_by, order_id=order_id)
        conn.commit()
    return order_id


def list_orders(organization_id: int) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE organization_id = ? ORDER BY created_at DESC",
            (organization_id,),
        ).fetchall()
    return [_deserialize_order(_row_to_dict(row)) for row in rows]


def get_order(organization_id: int, order_id: str) -> dict[str, Any] | None:
    with closing(connect()) as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE organization_id = ? AND order_id = ?",
            (organization_id, order_id),
        ).fetchone()
    return _deserialize_order(_row_to_dict(row))


def _deserialize_order(order: dict[str, Any] | None) -> dict[str, Any] | None:
    if not order:
        return None
    for key in ("property_details_json", "extracted_data_json"):
        value = order.get(key) or "{}"
        try:
            order[key] = json.loads(value)
        except Exception:
            order[key] = {}
    order["property_details"] = order.pop("property_details_json", {})
    order["extracted_data"] = order.pop("extracted_data_json", {})
    return order


def update_order(
    organization_id: int,
    order_id: str,
    updated_fields: dict[str, Any],
    property_details: dict[str, Any] | None = None,
    changed_by: str = "",
) -> None:
    if not updated_fields and property_details is None:
        return
    allowed = {
        "client_name", "client_email", "client_phone", "borrower_name", "lender_name",
        "loan_number", "subject_address", "city", "state", "zip_code", "property_type",
        "appraisal_type", "form_type", "assigned_appraiser", "fee", "due_date",
        "inspection_date", "status", "value_opinion", "field_notes",
    }
    set_clauses: list[str] = []
    values: list[Any] = []
    for key, value in updated_fields.items():
        if key in allowed:
            set_clauses.append(f"{key} = ?")
            values.append(value)
    if property_details is not None:
        set_clauses.append("property_details_json = ?")
        values.append(json.dumps(property_details, ensure_ascii=False))
    set_clauses.append("updated_at = ?")
    values.append(datetime.utcnow().isoformat())
    values.extend([organization_id, order_id])
    with closing(connect()) as conn:
        conn.execute(
            f"UPDATE orders SET {', '.join(set_clauses)} WHERE organization_id = ? AND order_id = ?",
            values,
        )
        add_activity(conn, organization_id, "Updated order", details=order_id, created_by=changed_by, order_id=order_id)
        conn.commit()


def update_order_status(
    organization_id: int,
    order_id: str,
    new_status: str,
    changed_by: str,
    reason: str = "",
) -> None:
    with closing(connect()) as conn:
        old_row = conn.execute(
            "SELECT status FROM orders WHERE organization_id = ? AND order_id = ?",
            (organization_id, order_id),
        ).fetchone()
        old_status = old_row["status"] if old_row else None
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE organization_id = ? AND order_id = ?",
            (new_status, datetime.utcnow().isoformat(), organization_id, order_id),
        )
        conn.execute(
            """
            INSERT INTO status_history (organization_id, order_id, old_status, new_status, changed_by, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (organization_id, order_id, old_status, new_status, changed_by, reason, datetime.utcnow().isoformat()),
        )
        add_activity(
            conn,
            organization_id,
            "Status changed",
            details=f"{old_status or 'None'} → {new_status}" + (f" | {reason}" if reason else ""),
            created_by=changed_by,
            order_id=order_id,
        )
        conn.commit()


def save_uploaded_file(
    organization_id: int,
    order_id: str,
    uploaded_file: Any,
    kind: str,
) -> str:
    order_dir = STORAGE_DIR / str(organization_id) / order_id
    order_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(uploaded_file.name).name
    target_path = order_dir / filename
    target_path.write_bytes(uploaded_file.getbuffer())
    mime_type = getattr(uploaded_file, "type", "") or ""
    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT INTO files (organization_id, order_id, kind, original_name, stored_path, mime_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                order_id,
                kind,
                filename,
                str(target_path),
                mime_type,
                datetime.utcnow().isoformat(),
            ),
        )
        add_activity(conn, organization_id, "Uploaded file", details=f"{kind}: {filename}", created_by="user", order_id=order_id)
        conn.commit()
    return str(target_path)


def list_files(organization_id: int, order_id: str) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM files
            WHERE organization_id = ? AND order_id = ?
            ORDER BY created_at DESC
            """,
            (organization_id, order_id),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def save_section(
    organization_id: int,
    order_id: str,
    section_name: str,
    ai_draft: str | None = None,
    human_edited: str | None = None,
    evidence: list[dict[str, Any]] | None = None,
    review_status: str | None = None,
    reviewer_notes: str | None = None,
) -> None:
    now = datetime.utcnow().isoformat()
    evidence_json = json.dumps(evidence or [], ensure_ascii=False)
    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT INTO report_sections (
                organization_id, order_id, section_name, ai_draft, human_edited,
                evidence_json, review_status, reviewer_notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_id, section_name) DO UPDATE SET
                ai_draft = COALESCE(excluded.ai_draft, report_sections.ai_draft),
                human_edited = COALESCE(excluded.human_edited, report_sections.human_edited),
                evidence_json = CASE
                    WHEN excluded.evidence_json != '[]' THEN excluded.evidence_json
                    ELSE report_sections.evidence_json
                END,
                review_status = COALESCE(excluded.review_status, report_sections.review_status),
                reviewer_notes = COALESCE(excluded.reviewer_notes, report_sections.reviewer_notes),
                updated_at = excluded.updated_at
            """,
            (
                organization_id,
                order_id,
                section_name,
                ai_draft,
                human_edited,
                evidence_json,
                review_status,
                reviewer_notes,
                now,
            ),
        )
        add_activity(conn, organization_id, "Saved section", details=section_name, created_by="user", order_id=order_id)
        conn.commit()


def get_sections(organization_id: int, order_id: str) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM report_sections
            WHERE organization_id = ? AND order_id = ?
            ORDER BY section_name
            """,
            (organization_id, order_id),
        ).fetchall()
    sections: list[dict[str, Any]] = []
    for row in rows:
        item = _row_to_dict(row)
        try:
            item["evidence"] = json.loads(item.get("evidence_json") or "[]")
        except Exception:
            item["evidence"] = []
        sections.append(item)
    return sections


def log_ai_run(
    organization_id: int,
    order_id: str,
    run_type: str,
    section_name: str | None,
    prompt_summary: str,
    input_payload: dict[str, Any],
    output_text: str,
    model: str,
    usage: dict[str, Any] | None = None,
) -> None:
    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT INTO ai_runs (
                organization_id, order_id, run_type, section_name, prompt_summary,
                input_json, output_text, model, usage_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                order_id,
                run_type,
                section_name,
                prompt_summary,
                json.dumps(input_payload, ensure_ascii=False),
                output_text,
                model,
                json.dumps(usage or {}, ensure_ascii=False),
                datetime.utcnow().isoformat(),
            ),
        )
        add_activity(conn, organization_id, "AI run", details=f"{run_type}: {section_name or 'n/a'}", created_by="AI", order_id=order_id)
        conn.commit()


def get_ai_runs(organization_id: int, order_id: str) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM ai_runs
            WHERE organization_id = ? AND order_id = ?
            ORDER BY created_at DESC
            """,
            (organization_id, order_id),
        ).fetchall()
    items = []
    for row in rows:
        item = _row_to_dict(row)
        for key in ("input_json", "usage_json"):
            try:
                item[key] = json.loads(item.get(key) or "{}")
            except Exception:
                item[key] = {}
        items.append(item)
    return items


def set_qc_item(organization_id: int, order_id: str, item_key: str, is_complete: bool) -> None:
    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT INTO qc_checklist (organization_id, order_id, item_key, is_complete, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(order_id, item_key) DO UPDATE SET
                is_complete = excluded.is_complete,
                updated_at = excluded.updated_at
            """,
            (
                organization_id,
                order_id,
                item_key,
                1 if is_complete else 0,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()


def get_qc_checklist(organization_id: int, order_id: str) -> dict[str, bool]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT item_key, is_complete
            FROM qc_checklist
            WHERE organization_id = ? AND order_id = ?
            """,
            (organization_id, order_id),
        ).fetchall()
    return {row["item_key"]: bool(row["is_complete"]) for row in rows}


def add_review_item(
    organization_id: int,
    order_id: str,
    reviewer_name: str,
    item_type: str,
    description: str,
) -> None:
    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT INTO review_items (
                organization_id, order_id, reviewer_name, item_type, description, status, created_at
            ) VALUES (?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                organization_id,
                order_id,
                reviewer_name,
                item_type,
                description,
                datetime.utcnow().isoformat(),
            ),
        )
        add_activity(conn, organization_id, "Added review item", details=item_type, created_by=reviewer_name, order_id=order_id)
        conn.commit()


def update_review_item(
    organization_id: int,
    item_id: int,
    status: str,
    response: str,
) -> None:
    with closing(connect()) as conn:
        conn.execute(
            """
            UPDATE review_items
            SET status = ?, response = ?, resolved_at = ?
            WHERE organization_id = ? AND id = ?
            """,
            (
                status,
                response,
                datetime.utcnow().isoformat() if status == "resolved" else None,
                organization_id,
                item_id,
            ),
        )
        conn.commit()


def get_review_items(organization_id: int, order_id: str) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM review_items
            WHERE organization_id = ? AND order_id = ?
            ORDER BY created_at DESC
            """,
            (organization_id, order_id),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_activity(organization_id: int, order_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        if order_id:
            rows = conn.execute(
                """
                SELECT * FROM activity_log
                WHERE organization_id = ? AND order_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (organization_id, order_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM activity_log
                WHERE organization_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (organization_id, limit),
            ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_status_history(organization_id: int, order_id: str) -> list[dict[str, Any]]:
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM status_history
            WHERE organization_id = ? AND order_id = ?
            ORDER BY created_at DESC
            """,
            (organization_id, order_id),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def import_legacy_orders(organization_id: int, legacy_db_path: str | Path, changed_by: str) -> tuple[int, list[str]]:
    legacy_db_path = Path(legacy_db_path)
    messages: list[str] = []
    if not legacy_db_path.exists():
        return 0, [f"Legacy database not found: {legacy_db_path}"]

    imported = 0
    legacy = sqlite3.connect(legacy_db_path)
    legacy.row_factory = sqlite3.Row
    try:
        legacy.execute("SELECT 1 FROM orders LIMIT 1")
    except Exception as exc:
        legacy.close()
        return 0, [f"Legacy database does not have an orders table: {exc}"]

    rows = legacy.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    with closing(connect()) as conn:
        for row in rows:
            order_id = row["order_id"]
            exists = conn.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if exists:
                messages.append(f"Skipped existing order {order_id}")
                continue

            property_details = row["property_details"] if "property_details" in row.keys() and row["property_details"] else "{}"
            extracted = "{}"
            conn.execute(
                """
                INSERT INTO orders (
                    organization_id, order_id, client_name, client_email, client_phone, borrower_name,
                    lender_name, loan_number, subject_address, city, state, zip_code,
                    property_type, appraisal_type, form_type, assigned_appraiser, fee,
                    due_date, inspection_date, status, value_opinion, field_notes,
                    extracted_data_json, property_details_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    row["order_id"],
                    row["client_name"] if "client_name" in row.keys() else "",
                    row["client_email"] if "client_email" in row.keys() else "",
                    row["client_phone"] if "client_phone" in row.keys() else "",
                    row["client_name"] if "client_name" in row.keys() else "",
                    row["lender_name"] if "lender_name" in row.keys() else "",
                    row["loan_number"] if "loan_number" in row.keys() else "",
                    row["subject_address"],
                    row["city"] if "city" in row.keys() else "",
                    row["state"] if "state" in row.keys() else "RI",
                    row["zip_code"] if "zip_code" in row.keys() else "",
                    row["property_type"] if "property_type" in row.keys() else "",
                    row["appraisal_type"] if "appraisal_type" in row.keys() else "1004",
                    row["form_type"] if "form_type" in row.keys() else "URAR",
                    row["assigned_appraiser"] if "assigned_appraiser" in row.keys() else "",
                    float(row["fee"] or 0),
                    row["due_date"] if "due_date" in row.keys() else None,
                    row["inspection_date"] if "inspection_date" in row.keys() else None,
                    row["status"] if "status" in row.keys() else "Pending",
                    row["value_opinion"] if "value_opinion" in row.keys() else "",
                    row["field_notes"] if "field_notes" in row.keys() else "",
                    extracted,
                    property_details,
                    row["created_at"] if "created_at" in row.keys() else datetime.utcnow().isoformat(),
                    row["updated_at"] if "updated_at" in row.keys() else datetime.utcnow().isoformat(),
                ),
            )

            photos_value = row["photos"] if "photos" in row.keys() else ""
            for raw_path in [part.strip() for part in str(photos_value or "").split(",") if part.strip()]:
                original_path = Path(raw_path)
                if original_path.exists():
                    target_dir = STORAGE_DIR / str(organization_id) / order_id
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_path = target_dir / original_path.name
                    try:
                        shutil.copy2(original_path, target_path)
                        conn.execute(
                            """
                            INSERT INTO files (organization_id, order_id, kind, original_name, stored_path, mime_type, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                organization_id,
                                order_id,
                                "photo",
                                original_path.name,
                                str(target_path),
                                "",
                                datetime.utcnow().isoformat(),
                            ),
                        )
                    except Exception as exc:
                        messages.append(f"Could not copy {raw_path}: {exc}")

            conn.execute(
                """
                INSERT INTO status_history (organization_id, order_id, old_status, new_status, changed_by, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    order_id,
                    None,
                    row["status"] if "status" in row.keys() else "Pending",
                    changed_by,
                    "Imported from legacy database",
                    datetime.utcnow().isoformat(),
                ),
            )

            add_activity(
                conn,
                organization_id,
                action="Imported legacy order",
                details=str(order_id),
                created_by=changed_by,
                order_id=order_id,
            )
            imported += 1

        conn.commit()

    legacy.close()
    if imported:
        messages.insert(0, f"Imported {imported} order(s) from {legacy_db_path.name}.")
    return imported, messages
