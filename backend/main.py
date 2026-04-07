import os
import sqlite3
import random
import time
import json
import uuid
from datetime import datetime
from apps.civic_middleware.backend.agent.agent import run_trust_agent_streaming

# App Configuration
APP_NAME = "civic_middleware"
DB_DIR = f"apps/{APP_NAME}/backend/data/db"
DB_PATH = os.path.join(DB_DIR, "traffic_data.db")

def _get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# RPC Functions - Middleware API
def chat_streaming(**args):
    """
    Agentic Middleware Endpoint. 
    Processes unstructured civic reports and returns structured trust assessments.
    """
    message = args.get("message", "")
    print(f"[BACKEND_START] chat_streaming message={message[:100]}")

    # 1. Yield initial status
    yield {"type": "status", "content": "Initializing trust agent...", "progress": 10}

    # 2. Process via Trust Agent
    final_content = ""
    for event in run_trust_agent_streaming(message=message):
        if event.get("type") == "message_complete":
            final_content = event.get("content", "")
            
            # Persist successful middleware decisions to the Audit Log
            try:
                data = json.loads(final_content)
                _persist_middleware_event(data)
            except Exception as e:
                print(f"[BACKEND_ERROR] Failed to persist event: {e}")
                
        yield event

    # 3. Final cleanup and done
    yield {"type": "done"}
    print("[BACKEND_SUCCESS] chat_streaming complete")

def _persist_middleware_event(data):
    """Internal helper to log validated trust events."""
    conn = _get_db()
    conn.execute("""
        INSERT INTO traffic_events (
            sensor_id, region, event_type, raw_value, prediction, 
            confidence, reliability_score, needs_human_review, 
            review_reason, risk_signals
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("sensor_id", "AGENT_VIRTUAL"),
        data.get("region", "Unspecified"),
        "agentic_middleware",
        0.0,
        data.get("prediction", "Unknown"),
        data.get("confidence", 0.0),
        data.get("reliability_score", 0.0),
        int(data.get("needs_human_review", False)),
        data.get("reason", "No reason provided"),
        json.dumps(data.get("risk_signals", {}))
    ))
    conn.commit()
    conn.close()

def get_dashboard_stats():
    """Returns aggregated stats for the dashboard overview."""
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM traffic_events").fetchone()[0]
    reviewed = conn.execute("SELECT COUNT(*) FROM traffic_events WHERE needs_human_review = 1").fetchone()[0]
    avg_reliability = conn.execute("SELECT AVG(reliability_score) FROM traffic_events").fetchone()[0] or 0.0
    
    interventions = conn.execute("""
        SELECT COUNT(*) FROM traffic_events 
        WHERE needs_human_review = 1 AND intervention_status != 'pending'
    """).fetchone()[0]
    
    conn.close()
    return {
        "total_events": total,
        "human_review_count": reviewed,
        "avg_reliability": round(avg_reliability, 3),
        "intervention_rate": round(interventions / max(1, reviewed), 2),
        "unresolved_interventions": reviewed - interventions
    }

def get_recent_events(limit: int = 50):
    """Retrieves the most recent traffic events and their trust analysis."""
    conn = _get_db()
    rows = conn.execute("""
        SELECT * FROM traffic_events 
        ORDER BY timestamp DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    
    res = []
    for r in rows:
        d = dict(r)
        d["risk_signals"] = json.loads(d["risk_signals"])
        res.append(d)
    return res

def get_analytics_data():
    """Returns trend and distribution data for industry charts."""
    conn = _get_db()
    trend = conn.execute("""
        SELECT strftime('%H:00', timestamp) as hour, AVG(reliability_score) as avg_reliability, AVG(confidence) as avg_confidence
        FROM traffic_events 
        GROUP BY hour 
        ORDER BY timestamp ASC 
        LIMIT 24
    """).fetchall()
    
    distribution = conn.execute("""
        SELECT 
            CASE 
                WHEN reliability_score < 0.3 then 'Critical'
                WHEN reliability_score < 0.6 then 'Low'
                WHEN reliability_score < 0.8 then 'Moderate'
                ELSE 'High'
            END as bracket,
            COUNT(*) as count
        FROM traffic_events
        GROUP BY bracket
    """).fetchall()

    conn.close()
    return {
        "reliability_trend": [dict(r) for r in trend],
        "reliability_distribution": [dict(r) for r in distribution]
    }

def resolve_intervention(event_id: int, status: str = 'resolved'):
    """Updates the intervention status of an event."""
    conn = _get_db()
    conn.execute("UPDATE traffic_events SET intervention_status = ? WHERE id = ?", (status, event_id))
    conn.commit()
    conn.close()
    return {"success": True, "id": event_id, "status": status}
