import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create leads table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        domain TEXT UNIQUE,
        industry TEXT,
        extracted_metadata TEXT,
        pain_points TEXT,
        recipient_email TEXT,
        personalized_subject TEXT,
        personalized_body TEXT,
        status TEXT NOT NULL DEFAULT 'Discovered',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

def save_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    # First check environment variables
    env_val = os.getenv(key)
    if env_val is not None:
        return env_val
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def add_lead(company_name: str, domain: str, industry: str = None) -> bool:
    """Inserts a new lead in 'Discovered' state. Returns True if inserted, False if duplicate."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO leads (company_name, domain, industry, status) VALUES (?, ?, ?, 'Discovered')",
            (company_name, domain, industry)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Duplicate domain
        return False
    finally:
        conn.close()

def update_lead_status(lead_id: int, status: str, error_message: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leads SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
        (status, error_message, datetime.now().isoformat(), lead_id)
    )
    conn.commit()
    conn.close()

def update_lead_enrichment(lead_id: int, extracted_metadata: dict, recipient_email: str = None, industry: str = None, status: str = 'Enriched'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE leads 
        SET extracted_metadata = ?, recipient_email = COALESCE(?, recipient_email), industry = COALESCE(?, industry), status = ?, updated_at = ?
        WHERE id = ?
        """,
        (json.dumps(extracted_metadata), recipient_email, industry, status, datetime.now().isoformat(), lead_id)
    )
    conn.commit()
    conn.close()

def update_lead_ai_output(lead_id: int, pain_points: list, subject: str, body: str, status: str = 'Pending_Review'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE leads 
        SET pain_points = ?, personalized_subject = ?, personalized_body = ?, status = ?, updated_at = ?
        WHERE id = ?
        """,
        (json.dumps(pain_points), subject, body, status, datetime.now().isoformat(), lead_id)
    )
    conn.commit()
    conn.close()

def update_lead_email_edits(lead_id: int, recipient_email: str, subject: str, body: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE leads 
        SET recipient_email = ?, personalized_subject = ?, personalized_body = ?, updated_at = ?
        WHERE id = ?
        """,
        (recipient_email, subject, body, datetime.now().isoformat(), lead_id)
    )
    conn.commit()
    conn.close()

def get_lead(lead_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_leads_by_status(status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status = ? ORDER BY id DESC", (status,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_leads():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as count FROM leads GROUP BY status")
    rows = cursor.fetchall()
    conn.close()
    
    stats = {
        "Discovered": 0,
        "Enriched": 0,
        "Pending_Review": 0,
        "Completed": 0,
        "Rejected": 0,
        "Failed": 0
    }
    for r in rows:
        if r["status"] in stats:
            stats[r["status"]] = r["count"]
    return stats
