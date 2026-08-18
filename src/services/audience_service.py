import csv
import io
import logging
import re
from typing import Any, Dict, List, Optional

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def guess_column_mapping(headers: List[str]) -> Dict[str, str]:
    mapping = {
        "name": "",
        "phone": "",
        "email": "",
        "company": "",
        "description": "",
        "context": ""
    }

    for h in headers:
        hl = h.lower().strip()
        if not mapping["phone"] and re.search(r'\b(phone|mobile|cell|number)\b', hl):
            mapping["phone"] = h
        elif not mapping["name"] and re.search(r'\b(name|first name|full name)\b', hl):
            mapping["name"] = h
        elif not mapping["email"] and "email" in hl:
            mapping["email"] = h
        elif not mapping["company"] and re.search(r'\b(company|org|organization|business)\b', hl):
            mapping["company"] = h
        elif not mapping["description"] and re.search(r'\b(description|desc|title|role)\b', hl):
            mapping["description"] = h
        elif not mapping["context"] and re.search(r'\b(context|notes|reason)\b', hl):
            mapping["context"] = h

    return mapping

def normalize_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    # Strip non-numeric except leading +
    cleaned = re.sub(r'[^\d+]', '', str(phone))
    if not cleaned:
        return None
    # Ensure it starts with +, if not, could assume country code but we just keep digits
    # In a real production system we'd use phonenumbers lib, but this is simple robust fallback
    if not cleaned.startswith('+') and len(cleaned) >= 10:
        cleaned = '+' + cleaned
    return cleaned if len(cleaned) >= 7 else None

def parse_csv_preview(file_bytes: bytes) -> Dict[str, Any]:
    text = file_bytes.decode('utf-8-sig') # Handle BOM
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return {"headers": [], "preview": [], "mapping": {}}

    headers = list(reader.fieldnames)
    mapping = guess_column_mapping(headers)

    preview = []
    for i, row in enumerate(reader):
        if i >= 20:
            break
        preview.append(row)

    return {
        "headers": headers,
        "mapping": mapping,
        "preview": preview,
        "total_rows": len(preview) + sum(1 for _ in reader)
    }

def process_audience_import(campaign_id: str, file_bytes: bytes, mapping: Dict[str, str]) -> Dict[str, Any]:
    text = file_bytes.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))

    client = get_supabase_client()

    # 1. Fetch existing campaign contacts to check duplicates
    existing_contacts = client.table("campaign_contacts").select("customer_id, customers(phone)").eq("campaign_id", campaign_id).execute().data or []
    existing_campaign_phones = set()
    for c in existing_contacts:
        if c.get("customers") and c["customers"].get("phone"):
            existing_campaign_phones.add(c["customers"]["phone"])

    stats = {
        "total": 0,
        "valid": 0,
        "invalid_phone": 0,
        "missing_phone": 0,
        "duplicate": 0,
        "dnc": 0
    }

    for row in reader:
        stats["total"] += 1
        raw_phone = row.get(mapping.get("phone", "")) if mapping.get("phone") else None

        if not raw_phone:
            stats["missing_phone"] += 1
            continue

        phone = normalize_phone(raw_phone)
        if not phone:
            stats["invalid_phone"] += 1
            continue

        if phone in existing_campaign_phones:
            stats["duplicate"] += 1
            continue

        # Extract fields
        name = row.get(mapping.get("name", "")) if mapping.get("name") else None
        email = row.get(mapping.get("email", "")) if mapping.get("email") else None
        company = row.get(mapping.get("company", "")) if mapping.get("company") else None
        description = row.get(mapping.get("description", "")) if mapping.get("description") else None
        context = row.get(mapping.get("context", "")) if mapping.get("context") else None

        # Check if customer exists by phone
        cust_match = client.table("customers").select("*").eq("phone", phone).execute().data

        if cust_match:
            customer = cust_match[0]
            # Update missing info only
            updates = {}
            if name and not customer.get("name"): updates["name"] = name
            if email and not customer.get("email"): updates["email"] = email
            if company and not customer.get("company"): updates["company"] = company
            if updates:
                client.table("customers").update(updates).eq("id", customer["id"]).execute()
        else:
            # Create customer
            new_cust_res = client.table("customers").insert({
                "phone": phone,
                "name": name,
                "email": email,
                "company": company,
                "description": description
            }).execute()
            customer = new_cust_res.data[0] if new_cust_res.data else None

        if not customer:
            stats["invalid_phone"] += 1
            continue

        existing_campaign_phones.add(phone)

        # Check DNC
        if customer.get("do_not_call"):
            stats["dnc"] += 1
            status = "DO_NOT_CALL"
        else:
            stats["valid"] += 1
            status = "PENDING"

        # Create campaign contact
        client.table("campaign_contacts").insert({
            "campaign_id": campaign_id,
            "customer_id": customer["id"],
            "status": status,
            "customer_context": context
        }).execute()

    return stats

def get_audience(campaign_id: str) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table("campaign_contacts").select("id, status, customer_context, customers(name, phone, company, email, do_not_call)").eq("campaign_id", campaign_id).execute()
    return res.data or []

def remove_audience_member(campaign_contact_id: str) -> bool:
    client = get_supabase_client()
    try:
        client.table("campaign_contacts").delete().eq("id", campaign_contact_id).execute()
        return True
    except:
        return False
