
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build_workfile_bundle(
    order: dict[str, Any],
    sections: list[dict[str, Any]],
    files: list[dict[str, Any]],
    review_items: list[dict[str, Any]],
    checklist: dict[str, bool],
    activity: list[dict[str, Any]],
    status_history: list[dict[str, Any]],
) -> bytes:
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        order_snapshot = {
            "order": order,
            "sections": sections,
            "review_items": review_items,
            "qc_checklist": checklist,
            "activity": activity,
            "status_history": status_history,
        }
        zf.writestr("casefile/order_snapshot.json", json.dumps(order_snapshot, indent=2, ensure_ascii=False))

        markdown_parts: list[str] = [
            f"# Workfile Bundle for {order.get('order_id', '')}",
            "",
            f"**Property:** {order.get('subject_address', '')}, {order.get('city', '')}, {order.get('state', '')} {order.get('zip_code', '')}",
            f"**Client:** {order.get('client_name', '')}",
            f"**Status:** {order.get('status', '')}",
            "",
        ]
        for section in sorted(sections, key=lambda item: item.get("section_name", "")):
            body = (section.get("human_edited") or section.get("ai_draft") or "").strip()
            if body:
                markdown_parts.append(f"## {section.get('section_name', '')}")
                markdown_parts.append("")
                markdown_parts.append(body)
                markdown_parts.append("")
        zf.writestr("casefile/report_sections.md", "\n".join(markdown_parts).encode("utf-8"))

        if review_items:
            zf.writestr("casefile/review_items.csv", _csv_bytes(review_items))
        if activity:
            zf.writestr("casefile/activity_log.csv", _csv_bytes(activity))
        if status_history:
            zf.writestr("casefile/status_history.csv", _csv_bytes(status_history))

        checklist_rows = [{"item_key": key, "is_complete": value} for key, value in checklist.items()]
        if checklist_rows:
            zf.writestr("casefile/qc_checklist.csv", _csv_bytes(checklist_rows))

        readme_text = (
            "This bundle is a workfile export.\n\n"
            "Included:\n"
            "- order_snapshot.json\n"
            "- report_sections.md\n"
            "- review_items.csv\n"
            "- activity_log.csv\n"
            "- status_history.csv\n"
            "- qc_checklist.csv\n"
            "- files/ (copied attachments and photos when available)\n\n"
            "This is not a validated UAD 3.6 submission package.\n"
            "Use a verified appraisal software vendor for final UAD delivery."
        )
        zf.writestr("casefile/README.txt", readme_text.encode("utf-8"))

        for file_info in files:
            path = Path(file_info.get("stored_path", ""))
            if path.exists() and path.is_file():
                arcname = f"casefile/files/{path.name}"
                zf.write(path, arcname=arcname)

    bundle.seek(0)
    return bundle.getvalue()
