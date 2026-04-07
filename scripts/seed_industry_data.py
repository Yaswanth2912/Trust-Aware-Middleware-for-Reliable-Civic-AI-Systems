import os
import sys
import sqlite3
import random
import json
from datetime import datetime, timedelta

# Configuration
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

def init_db():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traffic_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sensor_id TEXT,
            region TEXT,
            event_type TEXT,
            raw_value REAL,
            prediction TEXT,
            confidence REAL,
            reliability_score REAL,
            needs_human_review BOOLEAN,
            review_reason TEXT,
            risk_signals TEXT, -- JSON string
            intervention_status TEXT DEFAULT 'pending' -- 'pending', 'resolved', 'dismissed'
        )
    """)
    conn.commit()
    conn.close()

def seed_industry_data(count=250):
    sensors = [
        "SEN_INT_001", "SEN_INT_002", "SEN_INT_003", "SEN_RAD_404", 
        "SEN_CAM_501", "SEN_CAM_502", "SEN_IOT_101", "SEN_IOT_102"
    ]
    regions = {
        "SEN_INT": "Downtown Core",
        "SEN_RAD": "Highway Exit 14",
        "SEN_CAM": "Residential North",
        "SEN_IOT": "Industrial Zone"
    }
    
    predictions = ["Normal Flow", "Heavy Congestion", "Minor Incident", "Sensor Drift Detected", "Road Blockage"]
    reasons = [
        "Low Confidence: Sensor Calibration Drift",
        "Low Margin: Ambiguous Prediction",
        "High Risk Signal: Historical Variance",
        "Low Reliability Score",
        "Manual HIL Override Triggered"
    ]
    
    conn = _get_db()
    print(f"Generating {count} industry-level civic records...")
    
    for i in range(count):
        # Generate timestamps spread over the last 3 days
        minutes_back = random.randint(0, 72 * 60)
        ts = datetime.now() - timedelta(minutes=minutes_back)
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        
        sensor_id = random.choice(sensors)
        prefix = sensor_id[:7]
        region = regions.get(prefix, "Unknown")
        event_type = "radar" if "RAD" in sensor_id else ("camera" if "CAM" in sensor_id else "optical")
        
        # Rush hour logic for realistic values
        hour = ts.hour
        is_rush = 7 <= hour <= 9 or 16 <= hour <= 19
        raw_value = random.uniform(0.6, 0.98) if is_rush else random.uniform(0.1, 0.6)
        
        confidence = 0.7 + (random.random() * 0.3)
        reliability = 0.6 + (random.random() * 0.4)
        
        needs_review = reliability < 0.8 or confidence < 0.8
        status = "pending" if needs_review else "resolved"
        if i % 5 == 0: status = "pending" # Force some pending items
        
        risk_signals = {
            "sensor_noise": random.uniform(0.01, 0.4),
            "historical_variance": random.uniform(0.01, 0.4),
            "ood_score": random.uniform(0, 0.2)
        }
        
        conn.execute("""
            INSERT INTO traffic_events (
                timestamp, sensor_id, region, event_type, raw_value, 
                prediction, confidence, reliability_score, 
                needs_human_review, review_reason, risk_signals, intervention_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts_str, sensor_id, region, event_type, raw_value, 
            random.choice(predictions), confidence, reliability, 
            int(needs_review), random.choice(reasons) if needs_review else "",
            json.dumps(risk_signals), status
        ))
        
    conn.commit()
    conn.close()
    print("Synthetic industry data generation complete.")

if __name__ == "__main__":
    init_db()
    seed_industry_data()
