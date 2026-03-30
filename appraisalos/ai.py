
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import fitz  # type: ignore

from .config import DEFAULT_AI_MODEL, SECTION_GUIDANCE


def _get_streamlit_secret(key: str) -> str:
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if key in st.secrets:
                return str(st.secrets[key])
            lower = key.lower()
            if lower in st.secrets:
                return str(st.secrets[lower])
            if "api_keys" in st.secrets and isinstance(st.secrets["api_keys"], dict):
                api_keys = st.secrets["api_keys"]
                if key in api_keys:
                    return str(api_keys[key])
                if lower in api_keys:
                    return str(api_keys[lower])
    except Exception:
        pass
    return ""


def get_secret(key: str) -> str:
    return os.environ.get(key, "").strip() or _get_streamlit_secret(key)


def get_default_model() -> str:
    return os.environ.get("APPRAISALOS_AI_MODEL", DEFAULT_AI_MODEL).strip() or DEFAULT_AI_MODEL


def _make_client(api_key: str | None = None):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI SDK is not installed. Add 'openai' to your environment.") from exc
    return OpenAI(api_key=api_key or get_secret("OPENAI_API_KEY"))


def _dump_usage(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        try:
            return usage.model_dump()
        except Exception:
            return {"raw": str(usage)}
    if isinstance(usage, dict):
        return usage
    return {"raw": str(usage)}


def build_order_facts(order: dict[str, Any]) -> dict[str, Any]:
    property_details = dict(order.get("property_details") or {})
    facts = {
        "order_id": order.get("order_id"),
        "subject_address": order.get("subject_address"),
        "city": order.get("city"),
        "state": order.get("state"),
        "zip_code": order.get("zip_code"),
        "property_type": order.get("property_type"),
        "appraisal_type": order.get("appraisal_type"),
        "form_type": order.get("form_type"),
        "client_name": order.get("client_name"),
        "borrower_name": order.get("borrower_name"),
        "lender_name": order.get("lender_name"),
        "loan_number": order.get("loan_number"),
        "assigned_appraiser": order.get("assigned_appraiser"),
        "value_opinion": order.get("value_opinion"),
        "field_notes": order.get("field_notes"),
        "inspection_date": order.get("inspection_date"),
        "due_date": order.get("due_date"),
        "extracted_data": order.get("extracted_data") or {},
        "property_details": property_details,
    }
    return facts


def build_evidence(order: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for key in (
        "subject_address",
        "city",
        "state",
        "zip_code",
        "property_type",
        "appraisal_type",
        "form_type",
        "value_opinion",
        "field_notes",
        "inspection_date",
    ):
        value = order.get(key)
        if value:
            evidence.append({"source": "order", "field": key, "value": str(value)})
    for key, value in (order.get("property_details") or {}).items():
        if value not in ("", None, [], {}):
            evidence.append({"source": "property_details", "field": key, "value": str(value)})
    return evidence


_SECTION_SYSTEM = """You are a residential appraisal writing assistant.
Rules:
1. Write only from the supplied facts.
2. Never invent owners, sale history, schools, landmarks, streets, comparable sales, zoning details, or measurements.
3. If a fact is missing, write [NOT PROVIDED — appraiser to complete].
4. Keep the tone professional and plain.
5. Where the section depends on comp data, cost data, or reconciliation judgment, create a framework with placeholders instead of making facts up.
6. Do not mention these rules in the output.
"""


def generate_section(
    order: dict[str, Any],
    section_name: str,
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    model = model or get_default_model()
    client = _make_client(api_key)
    facts = build_order_facts(order)
    evidence = build_evidence(order)
    input_payload = {
        "task": "draft_appraisal_section",
        "section_name": section_name,
        "section_guidance": SECTION_GUIDANCE.get(section_name, ""),
        "facts": facts,
    }
    response = client.responses.create(
        model=model,
        instructions=_SECTION_SYSTEM,
        input=json.dumps(input_payload, indent=2),
    )
    return response.output_text.strip(), _dump_usage(response), evidence


def assemble_addendum(sections: dict[str, dict[str, Any]]) -> str:
    parts: list[str] = []
    for section_name in sorted(sections.keys()):
        item = sections[section_name]
        text = (item.get("human_edited") or item.get("ai_draft") or "").strip()
        if text:
            parts.append(f"## {section_name}\n\n{text}")
    return "\n\n".join(parts).strip()


_REVISION_SYSTEM = """You draft concise appraisal revision responses.
Rules:
1. Use only the supplied order facts and review items.
2. Never claim that a correction was made unless the facts show it.
3. Where evidence is missing, state [APPRAISER TO VERIFY].
4. Keep the tone professional, calm, and direct.
"""


def generate_revision_response(
    order: dict[str, Any],
    review_items: list[dict[str, Any]],
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, dict[str, Any]]:
    model = model or get_default_model()
    client = _make_client(api_key)
    payload = {
        "task": "draft_revision_response",
        "facts": build_order_facts(order),
        "open_review_items": review_items,
    }
    response = client.responses.create(
        model=model,
        instructions=_REVISION_SYSTEM,
        input=json.dumps(payload, indent=2),
    )
    return response.output_text.strip(), _dump_usage(response)


def _extract_json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Model output did not contain a JSON object.")
    return json.loads(text[start : end + 1])


def _pdf_to_images(file_bytes: bytes, max_pages: int = 5) -> list[dict[str, str]]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images: list[dict[str, str]] = []
    try:
        for page_num in range(min(doc.page_count, max_pages)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=180)
            img_bytes = pix.tobytes("png")
            images.append(
                {
                    "mime": "image/png",
                    "data": base64.b64encode(img_bytes).decode("utf-8"),
                }
            )
    finally:
        doc.close()
    return images


def extract_document(
    uploaded_file: Any,
    doc_type: str = "engagement",
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    model = model or get_default_model()
    client = _make_client(api_key)
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    suffix = Path(uploaded_file.name).suffix.lower()
    content_items: list[dict[str, Any]] = []
    if suffix == ".pdf":
        for image in _pdf_to_images(file_bytes):
            content_items.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{image['mime']};base64,{image['data']}",
                    "detail": "high",
                }
            )
    else:
        mime_type = getattr(uploaded_file, "type", "") or "image/png"
        content_items.append(
            {
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode('utf-8')}",
                "detail": "high",
            }
        )

    if doc_type == "purchase":
        schema_hint = {
            "buyer_name": "",
            "seller_name": "",
            "purchase_price": "",
            "sale_date": "",
            "property_address": "",
            "city": "",
            "state": "",
            "zip_code": "",
            "property_type": "",
            "closing_date": "",
            "loan_amount": "",
            "lender_name": "",
        }
        task = "Extract factual fields from this purchase and sale agreement. Return JSON only."
    else:
        schema_hint = {
            "client_name": "",
            "client_email": "",
            "client_phone": "",
            "lender_name": "",
            "loan_number": "",
            "borrower_name": "",
            "subject_address": "",
            "city": "",
            "state": "",
            "zip_code": "",
            "property_type": "",
            "appraisal_type": "",
            "fee": "",
            "due_date": "",
        }
        task = "Extract factual fields from this engagement letter or order form. Return JSON only."

    prompt = (
        f"{task}\n"
        "Rules:\n"
        "- Include only fields you can actually see.\n"
        "- Leave missing fields out or set them to an empty string.\n"
        "- Do not guess.\n"
        f"- Use this JSON shape: {json.dumps(schema_hint)}"
    )

    content_items.insert(0, {"type": "input_text", "text": prompt})
    response = client.responses.create(
        model=model,
        instructions="You extract structured appraisal intake data from documents. Return JSON only.",
        input=[{"role": "user", "content": content_items}],
    )
    data = _extract_json_from_text(response.output_text)
    return data, _dump_usage(response)


_ADVISOR_SYSTEM = """You are a knowledgeable residential real estate appraisal advisor.
You help appraisers with questions about USPAP, Fannie Mae guidelines, FHA/HUD requirements,
appraisal methodology, market analysis, adjustments, and general appraisal practice.
Rules:
1. Give practical, actionable answers.
2. Cite specific guideline sections when you can (e.g., USPAP Standards Rule 1-1, Fannie Mae B4-1.3-06).
3. If you are unsure or the answer depends on jurisdiction, say so clearly.
4. Keep answers concise and professional.
"""


def advisor_chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, dict[str, Any]]:
    model = model or get_default_model()
    client = _make_client(api_key)
    response = client.responses.create(
        model=model,
        instructions=_ADVISOR_SYSTEM,
        input=messages,
    )
    return response.output_text.strip(), _dump_usage(response)
