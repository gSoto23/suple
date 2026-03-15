from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.models import User
from app.models.marketing import MarketingTemplate, Campaign, CampaignRecipient
from app.schemas import marketing as schemas
from app.api import deps
from app.core.whatsapp import whatsapp_client

router = APIRouter()

# --- Marketing Templates ---

@router.post("/templates/sync")
async def sync_templates(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    try:
        # Fetch from Meta
        meta_templates = await whatsapp_client.get_templates()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Mark all existing as UNAVAILABLE to hide old ones from the UI
    await db.execute(update(MarketingTemplate).values(status="UNAVAILABLE"))
        
    synced_count = 0
    for t in meta_templates:
        name = t.get("name")
        language = t.get("language")
        status_val = str(t.get("status", "")).upper()
        category = t.get("category")
        components = t.get("components", [])
        
        # Check if exists
        result = await db.execute(select(MarketingTemplate).where(MarketingTemplate.name == name, MarketingTemplate.language == language))
        existing = result.scalars().first()
        
        if existing:
            existing.status = status_val
            existing.category = category
            existing.components = components
        else:
            new_template = MarketingTemplate(
                name=name,
                language=language,
                status=status_val,
                category=category,
                components=components
            )
            db.add(new_template)
            
        synced_count += 1
        
    await db.commit()
    return {"message": "Sync completed", "synced_count": synced_count}

@router.get("/templates", response_model=List[schemas.MarketingTemplate])
async def read_templates(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = Query(100, le=100),
    current_user: User = Depends(deps.get_current_user)
):
    query = select(MarketingTemplate).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/templates", response_model=schemas.MarketingTemplate, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_in: schemas.MarketingTemplateCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    db_template = MarketingTemplate(**template_in.model_dump())
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)
    return db_template

@router.get("/templates/{template_id}", response_model=schemas.MarketingTemplate)
async def read_template(
    template_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(MarketingTemplate).where(MarketingTemplate.id == template_id))
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


# --- Campaigns ---

@router.get("/campaigns", response_model=List[schemas.Campaign])
async def read_campaigns(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = Query(100, le=100),
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Campaign).order_by(Campaign.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/campaigns", response_model=schemas.Campaign, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: schemas.CampaignCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # Verify template exists
    template_result = await db.execute(select(MarketingTemplate).where(MarketingTemplate.id == campaign_in.template_id))
    if not template_result.scalars().first():
        raise HTTPException(status_code=404, detail="Marketing template not found")

    db_campaign = Campaign(**campaign_in.model_dump(), created_by_id=current_user.id)
    db.add(db_campaign)
    await db.commit()
    await db.refresh(db_campaign)
    return db_campaign

@router.get("/campaigns/{campaign_id}", response_model=schemas.Campaign)
async def read_campaign(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

# --- Campaign Recipients ---

@router.get("/campaigns/{campaign_id}/recipients", response_model=List[schemas.CampaignRecipient])
async def read_campaign_recipients(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user)
):
    query = select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/campaigns/{campaign_id}/recipients", response_model=List[schemas.CampaignRecipient], status_code=status.HTTP_201_CREATED)
async def add_campaign_recipients(
    campaign_id: int,
    customer_ids: List[int],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # Verify campaign exists
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recipients = []
    for cid in customer_ids:
        # Avoid duplicates
        existing = await db.execute(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.customer_id == cid
            )
        )
        if not existing.scalars().first():
            recipient = CampaignRecipient(campaign_id=campaign_id, customer_id=cid)
            db.add(recipient)
            recipients.append(recipient)
    
    await db.commit()
    
    for r in recipients:
        await db.refresh(r)
        
    return recipients

# --- Campaign Execution ---

@router.post("/campaigns/{campaign_id}/execute")
async def execute_campaign(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # Load campaign and template
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.template))
        .where(Campaign.id == campaign_id)
    )
    campaign = result.scalars().first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if campaign.status in ["running", "completed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign.status}")

    # Load recipients with their customers
    rec_result = await db.execute(
        select(CampaignRecipient)
        .options(selectinload(CampaignRecipient.customer))
        .where(CampaignRecipient.campaign_id == campaign_id, CampaignRecipient.status == "pending")
    )
    recipients = rec_result.scalars().all()

    if not recipients:
        raise HTTPException(status_code=400, detail="No pending recipients found for this campaign")

    # Mark campaign as running
    campaign.status = "running"
    await db.commit()

    success_count = 0
    failure_count = 0

    for recipient in recipients:
        customer = recipient.customer
        if not customer or not customer.phone:
            recipient.status = "failed"
            recipient.error_message = "Customer has no phone number"
            failure_count += 1
            continue

        try:
            # Process Components and inject variables
            final_components = []
            if campaign.template.components:
                # Copy components to avoid modifying the template globally
                import copy
                template_components = copy.deepcopy(campaign.template.components)
                
                # We need to build the structure Meta expects for sending.
                # Meta templates definition components are different from sending components.
                # Sending components look like: [{"type": "body", "parameters": [{"type": "text", "text": "Jorge"}]}]
                
                # Check variables_mapping (e.g {"body_1": "full_name", "body_2": "phone", "header_1": "email"})
                mapping = campaign.variables_mapping or {}
                
                for comp in template_components:
                    comp_type = comp.get("type", "").lower()
                    if comp_type not in ["header", "body"]: continue
                    
                    # If the template component has text with {{#}} it means it needs parameters.
                    # We will simplify by building the 'parameters' array if mapping provides values for this type.
                    # Since we store our custom mapping keyed by e.g "body_1", "body_2"
                    text = comp.get("text", "")
                    import re
                    variables_found = re.findall(r'\{\{(\d+)\}\}', text)
                    if variables_found:
                        parameters = []
                        for var_index in sorted(variables_found, key=int):
                            map_key = f"{comp_type}_{var_index}"
                            customer_attr = mapping.get(map_key)
                            
                            val = ""
                            if customer_attr and hasattr(customer, customer_attr):
                                val = str(getattr(customer, customer_attr) or "")
                            else:
                                val = "Cliente" # fallback
                                
                            parameters.append({"type": "text", "text": val})
                            
                        final_components.append({
                            "type": comp_type,
                            "parameters": parameters
                        })

            # Send message via WhatsApp Client
            meta_response = await whatsapp_client.send_template_message(
                to=customer.phone,
                template_name=campaign.template.name,
                language_code=campaign.template.language,
                components=final_components if final_components else None
            )
            
            # Update recipient status
            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            if meta_response and "messages" in meta_response and len(meta_response["messages"]) > 0:
                recipient.message_id = meta_response["messages"][0]["id"]
            
            success_count += 1
            
        except Exception as e:
            recipient.status = "failed"
            recipient.error_message = str(e)
            failure_count += 1

    # Mark campaign as completed
    campaign.status = "completed"
    await db.commit()

    return {
        "message": "Campaign execution finished",
        "success_count": success_count,
        "failure_count": failure_count,
        "total_processed": len(recipients)
    }
