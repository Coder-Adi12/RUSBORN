import json
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.auth import require_dashboard_session
from services.audience_service import (
    get_audience,
    parse_csv_preview,
    process_audience_import,
    remove_audience_member,
)
from services.campaign_service import (
    add_contacts,
    create_campaign,
    delete_campaign,
    get_campaign,
    get_campaign_activity,
    get_campaign_progress,
    list_campaigns,
    pause_campaign,
    start_campaign,
    stop_campaign,
    update_campaign,
    validate_campaign,
)

router = APIRouter(
    prefix="/api/v1/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(require_dashboard_session)],
)

class CampaignCreateRequest(BaseModel):
    name: str
    objective: str
    voice_agent_instructions: str
    timezone: str
    max_concurrent_calls: int = 1
    max_attempts_per_customer: int = 1
    retry_delay_minutes: int = 30

class CampaignUpdateRequest(BaseModel):
    name: str | None = None
    objective: str | None = None
    voice_agent_instructions: str | None = None
    timezone: str | None = None
    max_concurrent_calls: int | None = None
    max_attempts_per_customer: int | None = None
    retry_delay_minutes: int | None = None

class AddContactsRequest(BaseModel):
    customer_ids: List[str]

@router.get("")
def api_list_campaigns():
    return list_campaigns()

@router.post("")
def api_create_campaign(req: CampaignCreateRequest):
    campaign = create_campaign(req.model_dump())
    if not campaign:
        raise HTTPException(status_code=500, detail="Failed to create campaign")
    return campaign

@router.get("/{campaign_id}")
def api_get_campaign(campaign_id: str):
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.put("/{campaign_id}")
def api_update_campaign(campaign_id: str, req: CampaignUpdateRequest):
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    campaign = update_campaign(campaign_id, update_data)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found or failed to update")
    return campaign

@router.delete("/{campaign_id}")
def api_delete_campaign(campaign_id: str):
    if not delete_campaign(campaign_id):
        raise HTTPException(status_code=500, detail="Failed to delete campaign")
    return {"status": "ok"}

@router.post("/{campaign_id}/validate")
def api_validate_campaign(campaign_id: str):
    result = validate_campaign(campaign_id)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.post("/{campaign_id}/start")
def api_start_campaign(campaign_id: str):
    if not start_campaign(campaign_id):
        raise HTTPException(status_code=400, detail="Could not start campaign. Check status.")
    return {"status": "RUNNING"}

@router.post("/{campaign_id}/pause")
def api_pause_campaign(campaign_id: str):
    if not pause_campaign(campaign_id):
        raise HTTPException(status_code=400, detail="Could not pause campaign.")
    return {"status": "PAUSED"}

@router.post("/{campaign_id}/stop")
def api_stop_campaign(campaign_id: str):
    if not stop_campaign(campaign_id):
        raise HTTPException(status_code=400, detail="Could not stop campaign.")
    return {"status": "STOPPED"}

@router.post("/{campaign_id}/contacts")
def api_add_contacts(campaign_id: str, req: AddContactsRequest):
    if not add_contacts(campaign_id, req.customer_ids):
        raise HTTPException(status_code=500, detail="Failed to add contacts")
    return {"status": "ok"}

@router.get("/{campaign_id}/progress")
def api_campaign_progress(campaign_id: str):
    return get_campaign_progress(campaign_id)

@router.get("/{campaign_id}/activity")
def api_campaign_activity(campaign_id: str):
    return get_campaign_activity(campaign_id)

@router.post("/{campaign_id}/audience/upload")
async def api_audience_upload(campaign_id: str, file: UploadFile = File(...)):
    content = await file.read()
    return parse_csv_preview(content)

@router.post("/{campaign_id}/audience/import")
async def api_audience_import(campaign_id: str, file: UploadFile = File(...), mapping: str = Form(...)):
    content = await file.read()
    mapping_dict = json.loads(mapping)
    return process_audience_import(campaign_id, content, mapping_dict)

@router.get("/{campaign_id}/audience")
def api_get_audience(campaign_id: str):
    return get_audience(campaign_id)

@router.delete("/{campaign_id}/audience/{contact_id}")
def api_delete_audience_member(campaign_id: str, contact_id: str):
    if not remove_audience_member(contact_id):
        raise HTTPException(status_code=500, detail="Failed to remove audience member")
    return {"status": "ok"}

