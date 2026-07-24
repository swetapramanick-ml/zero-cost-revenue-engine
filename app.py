import os
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

import db
from extractor import extract_domain_metadata
from personalizer import generate_personalized_content
from dispatcher import send_email

# Initialize DB on start
db.init_db()

app = FastAPI(title="Zero-Cost Revenue Engine", description="Sales Outreach Automation Pipeline")

# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# HTML Template Path
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
index_html_path = os.path.join(templates_dir, "index.html")

# --- Pydantic Models for API Requests ---
class IngestRequest(BaseModel):
    company_name: str
    domain: str

class UpdateRequest(BaseModel):
    recipient_email: str
    personalized_subject: str
    personalized_body: str

# --- Pipeline Background Workers ---
def run_pipeline_for_lead(lead_id: int):
    """
    Automated background worker running:
    [1. Data Extraction] --> [2. State DB] --> [3. AI Personalizer] --> State DB (Pending Review)
    """
    lead = db.get_lead(lead_id)
    if not lead:
        return
        
    # Phase 1: Data Extraction & Enrichment
    try:
        # Update state database
        db.update_lead_status(lead_id, "Enriched")
        
        # Programmatic scraper
        metadata = extract_domain_metadata(lead["domain"])
        
        # Save enriched data & fallback email
        db.update_lead_enrichment(
            lead_id=lead_id,
            extracted_metadata=metadata,
            recipient_email=metadata.get("primary_email"),
            status="Enriched"
        )
    except Exception as e:
        db.update_lead_status(lead_id, "Failed", error_message=f"Enrichment Error: {str(e)}")
        return

    # Refetch lead after enrichment
    lead = db.get_lead(lead_id)
    try:
        # Load extracted metadata
        metadata = json.loads(lead["extracted_metadata"])
    except Exception:
        db.update_lead_status(lead_id, "Failed", error_message="Enrichment Error: Failed to parse metadata JSON.")
        return

    # Phase 2: AI Personalization
    try:
        # Check for key configuration
        api_key = db.get_setting("GEMINI_API_KEY")
        if not api_key:
            db.update_lead_status(lead_id, "Failed", error_message="AI Error: GEMINI_API_KEY is not configured in settings.")
            return

        db.update_lead_status(lead_id, "Pending_Review")
        
        # Connect to free Gemini API model (1.5 Flash or 2.5 Flash)
        ai_data = generate_personalized_content(lead["company_name"], lead["domain"], metadata)
        
        # Save AI copy and transition state to Pending Review
        db.update_lead_ai_output(
            lead_id=lead_id,
            pain_points=ai_data["pain_points"],
            subject=ai_data["personalized_subject"],
            body=ai_data["personalized_body"],
            status="Pending_Review"
        )
    except Exception as e:
        db.update_lead_status(lead_id, "Failed", error_message=f"AI Personalization Error: {str(e)}")

# --- Endpoints ---

@app.get("/")
def get_dashboard():
    """Serves the main dashboard application."""
    if not os.path.exists(index_html_path):
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(index_html_path)

@app.get("/api/leads")
def get_leads(status: Optional[str] = None):
    """Retrieves all leads, optionally filtered by status."""
    if status and status != "all":
        return db.get_leads_by_status(status)
    return db.get_all_leads()

@app.get("/api/leads/{lead_id}")
def get_lead_details(lead_id: int):
    """Retrieves specific details of a single lead."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.get("/api/stats")
def get_pipeline_stats():
    """Retrieves lead pipeline overview stats."""
    return db.get_stats()

@app.post("/api/leads/ingest")
def ingest_lead(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to ingest a new lead.
    Starts background pipeline tasks automatically.
    """
    domain = request.domain.strip().lower()
    
    # Check for duplicate
    conn = db.get_db_connection()
    row = conn.execute("SELECT id FROM leads WHERE domain = ?", (domain,)).fetchone()
    conn.close()
    
    if row:
        raise HTTPException(status_code=400, detail=f"Lead with domain '{domain}' already exists in pipeline.")

    success = db.add_lead(request.company_name, domain)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write lead to database.")

    # Retrieve inserted row
    conn = db.get_db_connection()
    new_row = conn.execute("SELECT * FROM leads WHERE domain = ?", (domain,)).fetchone()
    conn.close()
    
    lead_id = new_row["id"]
    
    # Queue background processing tasks immediately
    background_tasks.add_task(run_pipeline_for_lead, lead_id)
    
    return dict(new_row)

@app.post("/api/leads/{lead_id}/update")
def update_lead_draft(lead_id: int, request: UpdateRequest):
    """Updates the recipient, subject, or body of the generated email."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    db.update_lead_email_edits(
        lead_id=lead_id,
        recipient_email=request.recipient_email,
        subject=request.personalized_subject,
        body=request.personalized_body
    )
    return {"message": "Draft changes updated successfully"}

@app.post("/api/leads/{lead_id}/personalize")
def regenerate_lead_personalization(lead_id: int):
    """Manual trigger to re-run Gemini AI personalization using existing metadata."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead["extracted_metadata"]:
        raise HTTPException(status_code=400, detail="Lead is not enriched. Perform extraction first.")

    try:
        metadata = json.loads(lead["extracted_metadata"])
        ai_data = generate_personalized_content(lead["company_name"], lead["domain"], metadata)
        db.update_lead_ai_output(
            lead_id=lead_id,
            pain_points=ai_data["pain_points"],
            subject=ai_data["personalized_subject"],
            body=ai_data["personalized_body"],
            status="Pending_Review"
        )
        return {"message": "AI copy regenerated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/leads/{lead_id}/reject")
def reject_lead(lead_id: int):
    """Marks a lead as Rejected, excluding it from outreach."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.update_lead_status(lead_id, "Rejected")
    return {"message": "Lead rejected successfully"}

@app.post("/api/leads/{lead_id}/approve")
def approve_and_send(lead_id: int):
    """
    Human Gate Approval Endpoint.
    Dispatches the email via SMTP and updates status to Completed.
    """
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    if not lead["recipient_email"] or not lead["personalized_subject"] or not lead["personalized_body"]:
        raise HTTPException(status_code=400, detail="Email copy or recipient is incomplete.")

    try:
        # Wrap SMTP send and status update in a transaction-safe flow
        # In SQL database, we can update status to Completed upon success
        send_email(
            to_email=lead["recipient_email"],
            subject=lead["personalized_subject"],
            body=lead["personalized_body"]
        )
        db.update_lead_status(lead_id, "Completed")
        return {"message": "Email dispatched and lead marked completed"}
    except Exception as e:
        db.update_lead_status(lead_id, "Failed", error_message=f"Dispatch Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Email Dispatch failed: {str(e)}")

# --- System Settings Endpoints ---

@app.get("/api/settings")
def get_system_settings():
    """Retrieves current application configurations."""
    return {
        "GEMINI_API_KEY": db.get_setting("GEMINI_API_KEY"),
        "SMTP_HOST": db.get_setting("SMTP_HOST", "smtp.gmail.com"),
        "SMTP_PORT": db.get_setting("SMTP_PORT", "587"),
        "SMTP_USER": db.get_setting("SMTP_USER", ""),
        "SMTP_FROM_EMAIL": db.get_setting("SMTP_FROM_EMAIL", ""),
        "SMTP_FROM_NAME": db.get_setting("SMTP_FROM_NAME", "Zero-Cost Revenue Engine"),
        "SMTP_PASSWORD": db.get_setting("SMTP_PASSWORD", "")  # We return it masked or plain for local developer use
    }

@app.post("/api/settings")
def update_system_settings(payload: Dict[str, str] = Body(...)):
    """Saves updated settings values to SQLite table."""
    for key, value in payload.items():
        db.save_setting(key, value)
    return {"message": "Settings saved successfully"}

if __name__ == "__main__":
    import uvicorn
    # Start on standard port 8000 or the PORT provided by Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
