"""
backend/track_db.py
-------------------
Track Master & Infrastructure Database Subsystem for TRACK YUKTI.
West Central Railway (WCR) — Jabalpur Division.

Provides:
- track_master table & data schema
- track_condition table & data schema
- track_defects table & data schema
- track_maintenance_history table & data schema
- track_assets & track_trains relationship tables
- Dynamic calculated fields:
    * track_health_status (GOOD, WARNING, ATTENTION REQUIRED, CRITICAL)
    * overdue_days (dynamic based on current system date)
    * track_criticality (Admin controlled, read-only for departments)
- Strict CSV validation & import pipeline
- Prototype synthetic dataset for WCR Jabalpur Division
"""

import io
import re
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "trackyukti.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATABASE SCHEMA CREATION
# ─────────────────────────────────────────────────────────────────────────────

def init_track_db() -> None:
    """Create all Track Master and related infrastructure tables."""
    conn = get_connection()
    cur = conn.cursor()

    # 1. Track Master Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS track_master (
        track_id TEXT PRIMARY KEY,
        zone TEXT NOT NULL DEFAULT 'WCR',
        division TEXT NOT NULL DEFAULT 'Jabalpur (JBP)',
        section_code TEXT NOT NULL,
        section_name TEXT NOT NULL,
        from_station TEXT NOT NULL,
        to_station TEXT NOT NULL,
        track_type TEXT NOT NULL DEFAULT 'Main Line',
        gauge TEXT NOT NULL DEFAULT 'Broad Gauge (1676mm)',
        electrification TEXT NOT NULL DEFAULT '25kV AC Electric',
        number_of_lines INTEGER NOT NULL DEFAULT 2,
        track_length_km REAL NOT NULL,
        km_from REAL NOT NULL,
        km_to REAL NOT NULL,
        maximum_permissible_speed INTEGER NOT NULL DEFAULT 110,
        traffic_density REAL NOT NULL DEFAULT 100.0,
        line_capacity REAL NOT NULL DEFAULT 95.0,
        track_criticality TEXT NOT NULL DEFAULT 'NORMAL',
        current_condition TEXT NOT NULL DEFAULT 'GOOD',
        last_track_maintenance_date TEXT NOT NULL,
        next_track_maintenance_date TEXT NOT NULL,
        active_block_status TEXT NOT NULL DEFAULT 'NORMAL',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Track Condition Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS track_condition (
        track_id TEXT PRIMARY KEY,
        rail_condition TEXT NOT NULL,
        sleeper_condition TEXT NOT NULL,
        ballast_condition TEXT NOT NULL,
        track_geometry_condition TEXT NOT NULL,
        track_defect_count INTEGER NOT NULL DEFAULT 0,
        severe_defects_count INTEGER NOT NULL DEFAULT 0,
        required_maintenance_resources TEXT NOT NULL,
        remarks TEXT,
        last_inspection_score REAL DEFAULT 80.0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (track_id) REFERENCES track_master(track_id) ON DELETE CASCADE
    );
    """)

    # 3. Track Defects Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS track_defects (
        defect_id TEXT PRIMARY KEY,
        track_id TEXT NOT NULL,
        detected_date TEXT NOT NULL,
        defect_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        km_location TEXT NOT NULL,
        defect_description TEXT NOT NULL,
        repair_status TEXT NOT NULL DEFAULT 'OPEN',
        target_repair_date TEXT NOT NULL,
        resolved_date TEXT,
        resolved_by TEXT,
        remarks TEXT,
        FOREIGN KEY (track_id) REFERENCES track_master(track_id) ON DELETE CASCADE
    );
    """)

    # 4. Track Maintenance History Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS track_maintenance_history (
        maintenance_id TEXT PRIMARY KEY,
        track_id TEXT NOT NULL,
        maintenance_date TEXT NOT NULL,
        maintenance_type TEXT NOT NULL,
        condition_before TEXT NOT NULL,
        condition_after TEXT NOT NULL,
        duration_hours REAL NOT NULL,
        resources_used TEXT NOT NULL,
        department TEXT NOT NULL DEFAULT 'Engineering',
        remarks TEXT,
        FOREIGN KEY (track_id) REFERENCES track_master(track_id) ON DELETE CASCADE
    );
    """)

    # 5. Track Assets Relationship Table (Assets linked to track_id)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS track_assets (
        asset_id TEXT PRIMARY KEY,
        track_id TEXT NOT NULL,
        asset_name TEXT NOT NULL,
        department TEXT NOT NULL,
        km_location TEXT NOT NULL,
        installation_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPERATIONAL',
        remarks TEXT,
        FOREIGN KEY (track_id) REFERENCES track_master(track_id) ON DELETE CASCADE
    );
    """)

    # 6. Track Trains Relationship Table (Train schedules / active trains on track)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS track_trains (
        train_id TEXT PRIMARY KEY,
        train_name TEXT NOT NULL,
        track_id TEXT NOT NULL,
        section_code TEXT NOT NULL,
        train_type TEXT NOT NULL,
        scheduled_time_slot TEXT NOT NULL,
        priority_tier TEXT NOT NULL DEFAULT 'NORMAL',
        speed_kmph INTEGER DEFAULT 100,
        FOREIGN KEY (track_id) REFERENCES track_master(track_id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2. PROTOTYPE SYNTHETIC DATASET SEEDING (WCR JABALPUR DIVISION)
# ─────────────────────────────────────────────────────────────────────────────

def seed_track_db_if_empty() -> None:
    """Pre-seed database with realistic WCR Jabalpur Division prototype synthetic data."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM track_master")
    count = cur.fetchone()[0]
    if count > 0:
        conn.close()
        return

    # Prototype Synthetic Tracks across WCR Jabalpur Division
    tracks = [
        {
            "track_id": "TRK-JBP-KTE-UP-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "JBP-KTE",
            "section_name": "Jabalpur - Katni Heavy Freight Route",
            "from_station": "Jabalpur (JBP)",
            "to_station": "Katni Jn (KTE)",
            "track_type": "Main Line (UP)",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 2,
            "track_length_km": 91.2,
            "km_from": 990.0,
            "km_to": 1081.2,
            "maximum_permissible_speed": 130,
            "traffic_density": 142.5,
            "line_capacity": 125.0,
            "track_criticality": "CRITICAL",
            "current_condition": "FAIR",
            "last_track_maintenance_date": "2026-06-10",
            "next_track_maintenance_date": "2026-08-25",
            "active_block_status": "MAINTENANCE_SCHEDULED",
        },
        {
            "track_id": "TRK-JBP-KTE-DN-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "JBP-KTE",
            "section_name": "Jabalpur - Katni Heavy Freight Route",
            "from_station": "Katni Jn (KTE)",
            "to_station": "Jabalpur (JBP)",
            "track_type": "Main Line (DN)",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 2,
            "track_length_km": 91.2,
            "km_from": 1081.2,
            "km_to": 990.0,
            "maximum_permissible_speed": 130,
            "traffic_density": 148.0,
            "line_capacity": 128.5,
            "track_criticality": "HIGH",
            "current_condition": "GOOD",
            "last_track_maintenance_date": "2026-07-20",
            "next_track_maintenance_date": "2026-10-15",
            "active_block_status": "NORMAL",
        },
        {
            "track_id": "TRK-JBP-KTE-GL-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "JBP-KTE",
            "section_name": "Jabalpur - Katni Heavy Freight Route",
            "from_station": "Sihora Road (SHR)",
            "to_station": "Sleemanabad (SBD)",
            "track_type": "Goods Loop Line",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 1,
            "track_length_km": 28.4,
            "km_from": 1022.0,
            "km_to": 1050.4,
            "maximum_permissible_speed": 50,
            "traffic_density": 88.0,
            "line_capacity": 94.0,
            "track_criticality": "MEDIUM",
            "current_condition": "DETERIORATED",
            "last_track_maintenance_date": "2026-04-12",
            "next_track_maintenance_date": "2026-07-30",
            "active_block_status": "SPEED_RESTRICTION",
        },
        {
            "track_id": "TRK-JBP-ET-UP-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "JBP-ET",
            "section_name": "Jabalpur - Itarsi Trunk Line",
            "from_station": "Jabalpur (JBP)",
            "to_station": "Itarsi Jn (ET)",
            "track_type": "Main Line (UP)",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 2,
            "track_length_km": 244.5,
            "km_from": 989.5,
            "km_to": 745.0,
            "maximum_permissible_speed": 130,
            "traffic_density": 135.0,
            "line_capacity": 115.0,
            "track_criticality": "HIGH",
            "current_condition": "GOOD",
            "last_track_maintenance_date": "2026-08-01",
            "next_track_maintenance_date": "2026-11-01",
            "active_block_status": "NORMAL",
        },
        {
            "track_id": "TRK-JBP-ET-DN-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "JBP-ET",
            "section_name": "Jabalpur - Itarsi Trunk Line",
            "from_station": "Itarsi Jn (ET)",
            "to_station": "Jabalpur (JBP)",
            "track_type": "Main Line (DN)",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 2,
            "track_length_km": 244.5,
            "km_from": 745.0,
            "km_to": 989.5,
            "maximum_permissible_speed": 130,
            "traffic_density": 138.5,
            "line_capacity": 116.0,
            "track_criticality": "HIGH",
            "current_condition": "FAIR",
            "last_track_maintenance_date": "2026-05-18",
            "next_track_maintenance_date": "2026-09-02",
            "active_block_status": "ACTIVE_BLOCK",
        },
        {
            "track_id": "TRK-STA-REWA-SL-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "STA-REWA",
            "section_name": "Satna - Rewa Branch Corridor",
            "from_station": "Satna Jn (STA)",
            "to_station": "Rewa (REWA)",
            "track_type": "Single Line",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 1,
            "track_length_km": 49.8,
            "km_from": 0.0,
            "km_to": 49.8,
            "maximum_permissible_speed": 100,
            "traffic_density": 58.0,
            "line_capacity": 88.0,
            "track_criticality": "MEDIUM",
            "current_condition": "GOOD",
            "last_track_maintenance_date": "2026-07-10",
            "next_track_maintenance_date": "2026-10-30",
            "active_block_status": "NORMAL",
        },
        {
            "track_id": "TRK-KTE-SGRL-CL-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "KTE-SGRL",
            "section_name": "Katni - Singrauli Coal Logistics Line",
            "from_station": "Katni Jn (KTE)",
            "to_station": "Singrauli (SGRL)",
            "track_type": "Coal Heavy Haul (CL-1)",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 2,
            "track_length_km": 260.0,
            "km_from": 1082.0,
            "km_to": 1342.0,
            "maximum_permissible_speed": 100,
            "traffic_density": 165.0,
            "line_capacity": 132.0,
            "track_criticality": "CRITICAL",
            "current_condition": "DETERIORATED",
            "last_track_maintenance_date": "2026-04-05",
            "next_track_maintenance_date": "2026-07-20",
            "active_block_status": "SPEED_RESTRICTION",
        },
    ]

    for t in tracks:
        cur.execute("""
        INSERT INTO track_master (
            track_id, zone, division, section_code, section_name, from_station, to_station,
            track_type, gauge, electrification, number_of_lines, track_length_km, km_from, km_to,
            maximum_permissible_speed, traffic_density, line_capacity, track_criticality,
            current_condition, last_track_maintenance_date, next_track_maintenance_date, active_block_status
        ) VALUES (
            :track_id, :zone, :division, :section_code, :section_name, :from_station, :to_station,
            :track_type, :gauge, :electrification, :number_of_lines, :track_length_km, :km_from, :km_to,
            :maximum_permissible_speed, :traffic_density, :line_capacity, :track_criticality,
            :current_condition, :last_track_maintenance_date, :next_track_maintenance_date, :active_block_status
        )
        """, t)

    # Prototype Track Condition Data
    conditions = [
        {
            "track_id": "TRK-JBP-KTE-UP-01",
            "rail_condition": "60kg UIC / Head Worn 3.1mm (Gauge Corner Checked)",
            "sleeper_condition": "RT-2496 PSC / Sound Condition (98% Sound)",
            "ballast_condition": "Clean Cushion 280mm / Shoulder Ballast Deficient at KM 1012",
            "track_geometry_condition": "Cross-Level Deviation & Minor Twist Alert",
            "track_defect_count": 3,
            "severe_defects_count": 1,
            "required_maintenance_resources": "CSM 09-3X Tamping Rake, Ballast Hopper Rake, 30 P-Way Staff",
            "remarks": "Heavy loaded freight rakes require urgent deep screening and tamping.",
            "last_inspection_score": 68.0,
        },
        {
            "track_id": "TRK-JBP-KTE-DN-01",
            "rail_condition": "60kg 90UTS Rail / Sound Ultrasonic Signature",
            "sleeper_condition": "PSC Sleeper 60kg / 100% Intact",
            "ballast_condition": "Clean Cushion 320mm / Adequate Consolidation",
            "track_geometry_condition": "Within High-Speed IR Tolerances (TQI: 26)",
            "track_defect_count": 0,
            "severe_defects_count": 0,
            "required_maintenance_resources": "Routine Track Patrol & USFD Testing",
            "remarks": "Recently stabilized with Dynamic Track Stabilizer (DTS).",
            "last_inspection_score": 92.0,
        },
        {
            "track_id": "TRK-JBP-KTE-GL-01",
            "rail_condition": "52kg Worn Rail / Surface Scabs & Scuffing",
            "sleeper_condition": "PSC Sleeper / 5% C-Cracked near turnout points",
            "ballast_condition": "Caked Ballast Cushion / Drainage Choked",
            "track_geometry_condition": "Alignment Deviation on Turnout Curve",
            "track_defect_count": 5,
            "severe_defects_count": 2,
            "required_maintenance_resources": "BCM Deep Screening Machine, UNIMAT Turnout Tamper, 40 Trackmen",
            "remarks": "Imposed 30 km/h temporary speed restriction pending complete screening.",
            "last_inspection_score": 48.0,
        },
        {
            "track_id": "TRK-JBP-ET-UP-01",
            "rail_condition": "60kg UIC / Premium Welded LWR",
            "sleeper_condition": "Monoblock PSC / Good Elastic Fastenings",
            "ballast_condition": "Clean Cushion 300mm / Full Shoulder Profile",
            "track_geometry_condition": "Excellent Geometry / TQI 24",
            "track_defect_count": 1,
            "severe_defects_count": 0,
            "required_maintenance_resources": "Routine USFD Vehicle Inspection",
            "remarks": "Trunk corridor handling Vande Bharat Express and Janshatabdi.",
            "last_inspection_score": 88.0,
        },
        {
            "track_id": "TRK-JBP-ET-DN-01",
            "rail_condition": "60kg UIC / Light Corrugation Wave Pattern",
            "sleeper_condition": "Monoblock PSC / Sound Fastenings",
            "ballast_condition": "Cushion 270mm / Moderate Fouling",
            "track_geometry_condition": "Slight Gauge Widening +4mm on Curve KM 810",
            "track_defect_count": 2,
            "severe_defects_count": 0,
            "required_maintenance_resources": "Rail Grinding Machine (RGM), Track Lining Gang",
            "remarks": "Currently undergoing active coordinated rolling block possession.",
            "last_inspection_score": 74.0,
        },
        {
            "track_id": "TRK-STA-REWA-SL-01",
            "rail_condition": "52kg 90UTS Rail / Sound Condition",
            "sleeper_condition": "PSC Sleeper / Sound Condition",
            "ballast_condition": "Clean Cushion 260mm / Stable Formation",
            "track_geometry_condition": "Within Standard Tolerances for Branch Line",
            "track_defect_count": 1,
            "severe_defects_count": 0,
            "required_maintenance_resources": "Manual Track Packing & Lubrication Gang",
            "remarks": "Single line section connecting Rewa terminus.",
            "last_inspection_score": 82.0,
        },
        {
            "track_id": "TRK-KTE-SGRL-CL-01",
            "rail_condition": "60kg 110UTS Wear-Resistant Rail / Severe Flange Wear",
            "sleeper_condition": "Heavy Haul PSC / 6% Surface Hairline Cracks",
            "ballast_condition": "Heavily Fouled Coal-Dust Cushion / Drainage Blocked",
            "track_geometry_condition": "Severe Vertical Profile Dip & Twist",
            "track_defect_count": 6,
            "severe_defects_count": 3,
            "required_maintenance_resources": "BCM High-Capacity Screener, 2x RGM Rakes, 50 Trackmen",
            "remarks": "Critical logistics bottleneck handling 30+ coal rakes daily from NCL mines.",
            "last_inspection_score": 42.0,
        },
    ]

    for c in conditions:
        cur.execute("""
        INSERT INTO track_condition (
            track_id, rail_condition, sleeper_condition, ballast_condition,
            track_geometry_condition, track_defect_count, severe_defects_count,
            required_maintenance_resources, remarks, last_inspection_score
        ) VALUES (
            :track_id, :rail_condition, :sleeper_condition, :ballast_condition,
            :track_geometry_condition, :track_defect_count, :severe_defects_count,
            :required_maintenance_resources, :remarks, :last_inspection_score
        )
        """, c)

    # Prototype Track Defects Data
    defects = [
        {
            "defect_id": "DEF-2026-001",
            "track_id": "TRK-JBP-KTE-UP-01",
            "detected_date": "2026-08-20",
            "defect_type": "IMR Rail Flaw / Transverse Crack",
            "severity": "CRITICAL",
            "km_location": "KM 1012/14-16",
            "defect_description": "USFD testing detected 22mm internal transverse fissure on gauge face of rail.",
            "repair_status": "OPEN",
            "target_repair_date": "2026-09-12",
            "remarks": "Jogged fishplated with 30 km/h caution order until rail piece replacement.",
        },
        {
            "defect_id": "DEF-2026-002",
            "track_id": "TRK-JBP-KTE-UP-01",
            "detected_date": "2026-08-22",
            "defect_type": "Cupped Thermit Weld",
            "severity": "MAJOR",
            "km_location": "KM 1034/08",
            "defect_description": "Thermit weld joint cupped by 1.8mm causing wheel impact hammering.",
            "repair_status": "IN_PROGRESS",
            "target_repair_date": "2026-09-15",
            "remarks": "Requires in-situ re-welding / AT weld rectification.",
        },
        {
            "defect_id": "DEF-2026-003",
            "track_id": "TRK-JBP-KTE-UP-01",
            "detected_date": "2026-08-28",
            "defect_type": "Ballast Deficiency",
            "severity": "MINOR",
            "km_location": "KM 1045/02-10",
            "defect_description": "Cushion deficiency of 60mm along cess shoulder.",
            "repair_status": "OPEN",
            "target_repair_date": "2026-09-22",
            "remarks": "Ballast hopper rake requisitioned.",
        },
        {
            "defect_id": "DEF-2026-004",
            "track_id": "TRK-JBP-KTE-GL-01",
            "detected_date": "2026-08-10",
            "defect_type": "Turnout Point Tongue Rail Chipping",
            "severity": "CRITICAL",
            "km_location": "KM 1022/18",
            "defect_description": "50mm tongue rail chipping on 1-in-12 turnout switch assembly.",
            "repair_status": "SPEED_RESTRICTED",
            "target_repair_date": "2026-09-10",
            "remarks": "Switch assembly replacement scheduled with P-Way gang.",
        },
        {
            "defect_id": "DEF-2026-005",
            "track_id": "TRK-KTE-SGRL-CL-01",
            "detected_date": "2026-08-15",
            "defect_type": "Severe Rail Corrugation & Wheel Burn",
            "severity": "CRITICAL",
            "km_location": "KM 1120/04-20",
            "defect_description": "Periodic wave corrugation depth 0.9mm over 800m track length.",
            "repair_status": "OPEN",
            "target_repair_date": "2026-09-14",
            "remarks": "Heavy vibration affecting freight locomotive traction motors.",
        },
        {
            "defect_id": "DEF-2026-006",
            "track_id": "TRK-KTE-SGRL-CL-01",
            "detected_date": "2026-08-18",
            "defect_type": "Coal Caked Ballast Drainage Choke",
            "severity": "MAJOR",
            "km_location": "KM 1145/10-30",
            "defect_description": "Water accumulation on track bed due to impermeable coal sludge.",
            "repair_status": "OPEN",
            "target_repair_date": "2026-09-18",
            "remarks": "Requires high-output ballast screening.",
        },
        {
            "defect_id": "DEF-2026-007",
            "track_id": "TRK-JBP-ET-DN-01",
            "detected_date": "2026-08-25",
            "defect_type": "Gauge Widening",
            "severity": "MAJOR",
            "km_location": "KM 810/12-16",
            "defect_description": "Track gauge measured +6mm beyond permissible tolerance on curve.",
            "repair_status": "IN_PROGRESS",
            "target_repair_date": "2026-09-11",
            "remarks": "Lining and gauge tie adjustment being executed.",
        },
    ]

    for d in defects:
        cur.execute("""
        INSERT INTO track_defects (
            defect_id, track_id, detected_date, defect_type, severity, km_location,
            defect_description, repair_status, target_repair_date, remarks
        ) VALUES (
            :defect_id, :track_id, :detected_date, :defect_type, :severity, :km_location,
            :defect_description, :repair_status, :target_repair_date, :remarks
        )
        """, d)

    # Prototype Track Maintenance History
    history = [
        {
            "maintenance_id": "MNT-2026-071",
            "track_id": "TRK-JBP-KTE-UP-01",
            "maintenance_date": "2026-06-10",
            "maintenance_type": "Track Tamping (09-3X CSM)",
            "condition_before": "Track Quality Index (TQI): 44.5 (Rough Riding)",
            "condition_after": "Track Quality Index (TQI): 28.0 (Good Standard)",
            "duration_hours": 3.5,
            "resources_used": "CSM Tamping Machine #442, DTS Stabilizer, 18 Staff",
            "department": "Engineering",
            "remarks": "Possession completed without passenger detention.",
        },
        {
            "maintenance_id": "MNT-2026-072",
            "track_id": "TRK-JBP-KTE-DN-01",
            "maintenance_date": "2026-07-20",
            "maintenance_type": "Continuous Welded Rail (CWR) De-Stressing",
            "condition_before": "High Stress Tensor due to temperature differential",
            "condition_after": "De-stressed at 42°C rail temperature, normalized tension",
            "duration_hours": 4.0,
            "resources_used": "Hydraulic Tensor Rake, Gas Cutters, 25 Trackmen",
            "department": "Engineering",
            "remarks": "Executed in coordinated window with S&T axle counter overhaul.",
        },
        {
            "maintenance_id": "MNT-2026-073",
            "track_id": "TRK-JBP-ET-UP-01",
            "maintenance_date": "2026-08-01",
            "maintenance_type": "High-Speed USFD Rail Testing",
            "condition_before": "Routine 3-month testing cycle due",
            "condition_after": "0 IMR defects, 2 minor weld flaws marked for paint monitoring",
            "duration_hours": 2.5,
            "resources_used": "SPURT Car (Self-Propelled Ultrasonic Testing), 6 Operators",
            "department": "Engineering",
            "remarks": "Track certified safe for 130 km/h commercial operations.",
        },
        {
            "maintenance_id": "MNT-2026-074",
            "track_id": "TRK-KTE-SGRL-CL-01",
            "maintenance_date": "2026-04-05",
            "maintenance_type": "Deep Screening (BCM) & Ballast Injection",
            "condition_before": "Severe ballast choking from coal dust",
            "condition_after": "Recovered 300mm clean cushion over 1.2 km section",
            "duration_hours": 4.5,
            "resources_used": "Plasser BCM 08-32, 2x MFS Wagons, 35 Staff",
            "department": "Engineering",
            "remarks": "Partially relieved speed restriction from 30 to 50 km/h.",
        },
    ]

    for h in history:
        cur.execute("""
        INSERT INTO track_maintenance_history (
            maintenance_id, track_id, maintenance_date, maintenance_type, condition_before,
            condition_after, duration_hours, resources_used, department, remarks
        ) VALUES (
            :maintenance_id, :track_id, :maintenance_date, :maintenance_type, :condition_before,
            :condition_after, :duration_hours, :resources_used, :department, :remarks
        )
        """, h)

    # Prototype Track Assets (Linked to Track ID)
    assets = [
        {
            "asset_id": "AST-ENG-1024",
            "track_id": "TRK-JBP-KTE-DN-01",
            "asset_name": "Continuous Welded Rail (CWR) KM 1010-1014",
            "department": "Engineering",
            "km_location": "KM 1012/14",
            "installation_date": "2022-03-15",
            "status": "OPERATIONAL",
            "remarks": "Primary heavy freight track asset.",
        },
        {
            "asset_id": "AST-SNT-1025",
            "track_id": "TRK-JBP-KTE-DN-01",
            "asset_name": "Digital Axle Counter (DAC) Sensor Head #04",
            "department": "S&T",
            "km_location": "KM 1012/16",
            "installation_date": "2023-11-20",
            "status": "OPERATIONAL",
            "remarks": "Dual sensor configuration for automatic block signalling.",
        },
        {
            "asset_id": "AST-ELE-1026",
            "track_id": "TRK-JBP-KTE-DN-01",
            "asset_name": "OHE Catenary Wire Span & Mast #JBP-1012",
            "department": "Electrical",
            "km_location": "KM 1012/15",
            "installation_date": "2021-08-10",
            "status": "OPERATIONAL",
            "remarks": "Regulated 25kV OHE catenary span.",
        },
        {
            "asset_id": "AST-ENG-1027",
            "track_id": "TRK-JBP-KTE-UP-01",
            "asset_name": "Diamond Turnout Point #42 (1-in-12 Curved)",
            "department": "Engineering",
            "km_location": "KM 1022/18",
            "installation_date": "2020-05-14",
            "status": "MAINTENANCE_DUE",
            "remarks": "Tongue rail under speed restriction.",
        },
        {
            "asset_id": "AST-SNT-1028",
            "track_id": "TRK-JBP-ET-UP-01",
            "asset_name": "Electronic Interlocking (EI) Field Terminal Unit",
            "department": "S&T",
            "km_location": "KM 980/10",
            "installation_date": "2024-01-15",
            "status": "OPERATIONAL",
            "remarks": "Solid state interlocking hardware.",
        },
        {
            "asset_id": "AST-ELE-1029",
            "track_id": "TRK-KTE-SGRL-CL-01",
            "asset_name": "Traction Feeder Substation Circuit Breaker",
            "department": "Electrical",
            "km_location": "KM 1110/02",
            "installation_date": "2019-09-25",
            "status": "OPERATIONAL",
            "remarks": "Feeds heavy 6000HP WAG-9 and WAG-12 electric locos.",
        },
    ]

    for a in assets:
        cur.execute("""
        INSERT INTO track_assets (
            asset_id, track_id, asset_name, department, km_location,
            installation_date, status, remarks
        ) VALUES (
            :asset_id, :track_id, :asset_name, :department, :km_location,
            :installation_date, :status, :remarks
        )
        """, a)

    # Prototype Track Trains (Train Schedules linked to track_id & section_code)
    trains = [
        {
            "train_id": "12061",
            "train_name": "Jabalpur - Habibganj Jan Shatabdi Express",
            "track_id": "TRK-JBP-ET-UP-01",
            "section_code": "JBP-ET",
            "train_type": "SUPERFAST_PASSENGER",
            "scheduled_time_slot": "05:30 – 09:15 IST",
            "priority_tier": "PREMIUM",
            "speed_kmph": 110,
        },
        {
            "train_id": "12062",
            "train_name": "Habibganj - Jabalpur Jan Shatabdi Express",
            "track_id": "TRK-JBP-ET-DN-01",
            "section_code": "JBP-ET",
            "train_type": "SUPERFAST_PASSENGER",
            "scheduled_time_slot": "18:45 – 22:30 IST",
            "priority_tier": "PREMIUM",
            "speed_kmph": 110,
        },
        {
            "train_id": "12189",
            "train_name": "Mahakaushal Express (JBP - NZM)",
            "track_id": "TRK-JBP-KTE-UP-01",
            "section_code": "JBP-KTE",
            "train_type": "EXPRESS_PASSENGER",
            "scheduled_time_slot": "18:10 – 19:35 IST",
            "priority_tier": "HIGH",
            "speed_kmph": 105,
        },
        {
            "train_id": "12853",
            "train_name": "Amarkantak Express (DURG - BPL)",
            "track_id": "TRK-JBP-KTE-DN-01",
            "section_code": "JBP-KTE",
            "train_type": "EXPRESS_PASSENGER",
            "scheduled_time_slot": "03:15 – 04:40 IST",
            "priority_tier": "HIGH",
            "speed_kmph": 100,
        },
        {
            "train_id": "BOXN-KTE-901",
            "train_name": "Singrauli - Katni Thermal Coal Heavy Freight",
            "track_id": "TRK-KTE-SGRL-CL-01",
            "section_code": "KTE-SGRL",
            "train_type": "HEAVY_FREIGHT_COAL",
            "scheduled_time_slot": "Continuous Rolling Slots (1h Headway)",
            "priority_tier": "FREIGHT",
            "speed_kmph": 75,
        },
        {
            "train_id": "BTPN-ET-440",
            "train_name": "Itarsi - Jabalpur Petroleum Tanker Rake",
            "track_id": "TRK-JBP-ET-DN-01",
            "section_code": "JBP-ET",
            "train_type": "POL_FREIGHT",
            "scheduled_time_slot": "14:00 – 17:30 IST",
            "priority_tier": "FREIGHT",
            "speed_kmph": 70,
        },
    ]

    for tr in trains:
        cur.execute("""
        INSERT INTO track_trains (
            train_id, train_name, track_id, section_code, train_type,
            scheduled_time_slot, priority_tier, speed_kmph
        ) VALUES (
            :train_id, :train_name, :track_id, :section_code, :train_type,
            :scheduled_time_slot, :priority_tier, :speed_kmph
        )
        """, tr)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 3. DYNAMIC CALCULATED FIELDS ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def calculate_overdue_days(next_maintenance_date_str: str) -> int:
    """
    Calculate overdue days dynamically using system date:
    overdue_days = current_date - next_track_maintenance_date
    If next_date is in future, overdue_days = 0.
    """
    try:
        next_dt = datetime.strptime(next_maintenance_date_str.strip(), "%Y-%m-%d").date()
        today = date.today()
        diff = (today - next_dt).days
        return max(0, diff)
    except Exception:
        return 0


def calculate_track_health(
    track: Dict[str, Any],
    condition: Optional[Dict[str, Any]] = None,
    defects: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, str, str]:
    """
    Calculate dynamic Track Health Status:
    Status options: 'GOOD', 'WARNING', 'ATTENTION REQUIRED', 'CRITICAL'
    Based on:
    - severe_defects_count
    - track_defect_count
    - overdue_days
    - current_condition & inspection score

    Returns: (health_status, badge_class, description)
    """
    overdue_days = calculate_overdue_days(track.get("next_track_maintenance_date", ""))
    severe_defects = condition.get("severe_defects_count", 0) if condition else 0
    total_defects = condition.get("track_defect_count", 0) if condition else 0
    inspection_score = condition.get("last_inspection_score", 80.0) if condition else 80.0
    current_cond = str(track.get("current_condition", "GOOD")).upper()

    # Rule evaluation:
    # 1. CRITICAL
    if severe_defects > 0 or overdue_days > 30 or total_defects >= 5 or current_cond in ["DETERIORATED", "CRITICAL"]:
        reasons = []
        if severe_defects > 0:
            reasons.append(f"{severe_defects} Severe Track Flaws")
        if overdue_days > 30:
            reasons.append(f"{overdue_days} Days Maintenance Overdue")
        if total_defects >= 5:
            reasons.append(f"{total_defects} Defect Clusters")
        if current_cond in ["DETERIORATED", "CRITICAL"]:
            reasons.append(f"Condition: {current_cond}")
        desc = " | ".join(reasons) or "Immediate safety intervention required"
        return ("CRITICAL", "ty-badge-red", desc)

    # 2. ATTENTION REQUIRED
    elif overdue_days > 0 or total_defects >= 2 or current_cond in ["FAIR", "POOR"] or inspection_score < 70:
        reasons = []
        if overdue_days > 0:
            reasons.append(f"{overdue_days} Days Overdue")
        if total_defects >= 2:
            reasons.append(f"{total_defects} Active Defects")
        if current_cond in ["FAIR", "POOR"]:
            reasons.append(f"Condition: {current_cond}")
        desc = " | ".join(reasons) or "Priority slot scheduling recommended"
        return ("ATTENTION REQUIRED", "ty-badge-amber", desc)

    # 3. WARNING
    elif total_defects >= 1 or inspection_score < 80 or track.get("active_block_status") == "SPEED_RESTRICTION":
        desc = f"Minor Flaws ({total_defects}) or Speed Restriction Active"
        return ("WARNING", "ty-badge-purple", desc)

    # 4. GOOD
    else:
        return ("GOOD", "ty-badge-green", "Track parameters fully compliant with IR standards")


# ─────────────────────────────────────────────────────────────────────────────
# 4. QUERY & DATA RETRIEVAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_all_tracks(
    search_query: Optional[str] = None,
    section_code: Optional[str] = None,
    criticality: Optional[str] = None,
    condition: Optional[str] = None,
    block_status: Optional[str] = None,
    km_min: Optional[float] = None,
    km_max: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Query tracks with optional multi-attribute search and filtering."""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM track_master WHERE 1=1"
    params = []

    if section_code and section_code != "ALL":
        query += " AND section_code = ?"
        params.append(section_code)

    if criticality and criticality != "ALL":
        query += " AND track_criticality = ?"
        params.append(criticality)

    if condition and condition != "ALL":
        query += " AND current_condition = ?"
        params.append(condition)

    if block_status and block_status != "ALL":
        query += " AND active_block_status = ?"
        params.append(block_status)

    if km_min is not None:
        query += " AND km_to >= ?"
        params.append(km_min)

    if km_max is not None:
        query += " AND km_from <= ?"
        params.append(km_max)

    if search_query:
        s = f"%{search_query.strip()}%"
        query += " AND (track_id LIKE ? OR section_name LIKE ? OR from_station LIKE ? OR to_station LIKE ?)"
        params.extend([s, s, s, s])

    query += " ORDER BY section_code ASC, track_id ASC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Append dynamic calculated fields
    for r in rows:
        r["overdue_days"] = calculate_overdue_days(r.get("next_track_maintenance_date", ""))
        cond = get_track_condition(r["track_id"])
        h_status, h_badge, h_desc = calculate_track_health(r, cond)
        r["health_status"] = h_status
        r["health_badge"] = h_badge
        r["health_description"] = h_desc

    return rows


def get_track_by_id(track_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM track_master WHERE track_id = ?", (track_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["overdue_days"] = calculate_overdue_days(d.get("next_track_maintenance_date", ""))
    cond = get_track_condition(track_id)
    h_status, h_badge, h_desc = calculate_track_health(d, cond)
    d["health_status"] = h_status
    d["health_badge"] = h_badge
    d["health_description"] = h_desc
    return d


def get_track_condition(track_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM track_condition WHERE track_id = ?", (track_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_track_defects(track_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    if status_filter and status_filter != "ALL":
        cur.execute("SELECT * FROM track_defects WHERE track_id = ? AND repair_status = ? ORDER BY detected_date DESC", (track_id, status_filter))
    else:
        cur.execute("SELECT * FROM track_defects WHERE track_id = ? ORDER BY detected_date DESC", (track_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_all_defects(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    if status_filter and status_filter != "ALL":
        cur.execute("SELECT * FROM track_defects WHERE repair_status = ? ORDER BY detected_date DESC", (status_filter,))
    else:
        cur.execute("SELECT * FROM track_defects ORDER BY detected_date DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_track_maintenance_history(track_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM track_maintenance_history WHERE track_id = ? ORDER BY maintenance_date DESC", (track_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_track_assets(track_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM track_assets WHERE track_id = ? ORDER BY km_location ASC", (track_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_track_trains(track_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM track_trains WHERE track_id = ? ORDER BY scheduled_time_slot ASC", (track_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_active_blocks_for_track(track_id: str) -> List[Dict[str, Any]]:
    """Retrieve active and upcoming block requisitions linked to this track line."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM block_requests
    WHERE section_track LIKE ? OR section_track LIKE ?
    ORDER BY created_at DESC
    """, (f"%{track_id}%", "%UP-Main%" if "UP" in track_id else ("%DN-Main%" if "DN" in track_id else "%Loop%")))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 5. TRACK CRITICALITY & DEFECT MANAGEMENT (ADMIN RESTRICTED)
# ─────────────────────────────────────────────────────────────────────────────

def update_track_criticality(
    track_id: str,
    new_criticality: str,
    user_role: str,
    user_designation: str,
    remarks: str = ""
) -> bool:
    """
    Update track criticality with role validation.
    Track Criticality is controlled by Track Master / Admin (Chief Controller).
    Regular department users are barred from editing track criticality arbitrarily.
    """
    if user_role != "CHIEF_CONTROLLER":
        raise PermissionError("Track Criticality can only be updated by Chief Controller / Admin (Track Master Authority). Regular departments have read-only access.")

    valid_crits = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if new_criticality not in valid_crits:
        raise ValueError(f"Invalid criticality: {new_criticality}. Must be one of {valid_crits}")

    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    UPDATE track_master
    SET track_criticality = ?, updated_at = ?
    WHERE track_id = ?
    """, (new_criticality, now_str, track_id))
    conn.commit()
    conn.close()

    from backend.db import add_audit_log
    add_audit_log(user_designation, f"Updated Track Criticality of {track_id} to {new_criticality}. Note: {remarks}")
    return True


def update_defect_status(
    defect_id: str,
    new_status: str,
    user_designation: str,
    remarks: str = ""
) -> bool:
    """Update repair status of a track defect."""
    valid_statuses = ["OPEN", "SPEED_RESTRICTED", "IN_PROGRESS", "RESOLVED"]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid defect status: {new_status}. Must be one of {valid_statuses}")

    conn = get_connection()
    cur = conn.cursor()
    resolved_date = datetime.now().strftime("%Y-%m-%d") if new_status == "RESOLVED" else None

    cur.execute("""
    UPDATE track_defects
    SET repair_status = ?, resolved_date = ?, resolved_by = ?, remarks = ?
    WHERE defect_id = ?
    """, (new_status, resolved_date, user_designation if new_status == "RESOLVED" else None, remarks, defect_id))

    # Also update defect counts in track_condition
    cur.execute("SELECT track_id FROM track_defects WHERE defect_id = ?", (defect_id,))
    row = cur.fetchone()
    if row:
        trk_id = row["track_id"]
        cur.execute("SELECT COUNT(*) FROM track_defects WHERE track_id = ? AND repair_status != 'RESOLVED'", (trk_id,))
        open_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM track_defects WHERE track_id = ? AND repair_status != 'RESOLVED' AND severity = 'CRITICAL'", (trk_id,))
        sev_count = cur.fetchone()[0]
        cur.execute("""
        UPDATE track_condition
        SET track_defect_count = ?, severe_defects_count = ?, updated_at = CURRENT_TIMESTAMP
        WHERE track_id = ?
        """, (open_count, sev_count, trk_id))

    conn.commit()
    conn.close()

    from backend.db import add_audit_log
    add_audit_log(user_designation, f"Updated Defect {defect_id} status to {new_status}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 6. CSV DATA IMPORT & STRICT VALIDATION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_TRACK_CSV_FIELDS = [
    "track_id",
    "zone",
    "division",
    "section_code",
    "section_name",
    "from_station",
    "to_station",
    "track_type",
    "gauge",
    "electrification",
    "number_of_lines",
    "track_length_km",
    "km_from",
    "km_to",
    "maximum_permissible_speed",
    "traffic_density",
    "line_capacity",
    "track_criticality",
    "current_condition",
    "last_track_maintenance_date",
    "next_track_maintenance_date",
    "active_block_status",
]

VALID_CRITICALITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_CONDITIONS = {"GOOD", "FAIR", "DETERIORATED", "CRITICAL", "POOR"}
VALID_BLOCK_STATUSES = {"NORMAL", "ACTIVE_BLOCK", "SPEED_RESTRICTION", "MAINTENANCE_SCHEDULED"}


def validate_and_import_track_csv(df: pd.DataFrame, user_designation: str = "Chief Controller") -> Dict[str, Any]:
    """
    Strict validation and import of Track Master CSV:
    Checks:
    - Missing required fields
    - Duplicate track_ids
    - Invalid dates (format YYYY-MM-DD)
    - Invalid numeric ranges (speed, km, density, capacity)
    - Invalid enum values (criticality, condition, block status)
    """
    results = {
        "total_rows": len(df),
        "valid_count": 0,
        "rejected_count": 0,
        "valid_records": [],
        "rejected_records": [],
        "success": False,
    }

    # Normalize column names
    col_map = {c.strip().lower(): c for c in df.columns}
    missing_headers = []
    for req in REQUIRED_TRACK_CSV_FIELDS:
        if req.lower() not in col_map:
            missing_headers.append(req)

    if missing_headers:
        results["rejected_records"].append({
            "row_index": "Header",
            "track_id": "N/A",
            "errors": [f"Missing required CSV column headers: {', '.join(missing_headers)}"]
        })
        results["rejected_count"] = len(df)
        return results

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT track_id FROM track_master")
    existing_ids = set(r[0] for r in cur.fetchall())

    seen_in_batch = set()

    for idx, row in df.iterrows():
        row_idx = idx + 1
        errors = []

        # 1. Check track_id
        t_id = str(row.get(col_map["track_id"], "")).strip()
        if not t_id or t_id == "nan":
            errors.append("track_id is empty/missing")
        elif t_id in seen_in_batch:
            errors.append(f"Duplicate track_id '{t_id}' in uploaded file")
        else:
            seen_in_batch.add(t_id)

        # 2. Check stations and sections
        sec_code = str(row.get(col_map["section_code"], "")).strip()
        sec_name = str(row.get(col_map["section_name"], "")).strip()
        from_stn = str(row.get(col_map["from_station"], "")).strip()
        to_stn = str(row.get(col_map["to_station"], "")).strip()

        if not sec_code or sec_code == "nan":
            errors.append("section_code is empty")
        if not sec_name or sec_name == "nan":
            errors.append("section_name is empty")
        if not from_stn or from_stn == "nan":
            errors.append("from_station is empty")
        if not to_stn or to_stn == "nan":
            errors.append("to_station is empty")

        # 3. Numeric Validations
        try:
            num_lines = int(row.get(col_map["number_of_lines"], 1))
            if num_lines < 1:
                errors.append("number_of_lines must be >= 1")
        except Exception:
            errors.append("number_of_lines must be an integer")
            num_lines = 1

        try:
            length_km = float(row.get(col_map["track_length_km"], 0))
            if length_km <= 0:
                errors.append("track_length_km must be > 0")
        except Exception:
            errors.append("track_length_km must be numeric")
            length_km = 0.0

        try:
            km_from = float(row.get(col_map["km_from"], 0))
            km_to = float(row.get(col_map["km_to"], 0))
            if abs(km_to - km_from) < 0.01:
                errors.append("km_from and km_to cannot be identical")
        except Exception:
            errors.append("km_from and km_to must be numeric")
            km_from, km_to = 0.0, 0.0

        try:
            speed = int(row.get(col_map["maximum_permissible_speed"], 100))
            if speed < 20 or speed > 200:
                errors.append("maximum_permissible_speed must be between 20 and 200 km/h")
        except Exception:
            errors.append("maximum_permissible_speed must be an integer")
            speed = 100

        try:
            density = float(row.get(col_map["traffic_density"], 0))
            if density < 0:
                errors.append("traffic_density must be >= 0")
        except Exception:
            errors.append("traffic_density must be numeric")
            density = 0.0

        try:
            capacity = float(row.get(col_map["line_capacity"], 0))
            if capacity < 0 or capacity > 200:
                errors.append("line_capacity must be between 0 and 200%")
        except Exception:
            errors.append("line_capacity must be numeric")
            capacity = 0.0

        # 4. Enum Validations
        crit = str(row.get(col_map["track_criticality"], "NORMAL")).strip().upper()
        if crit not in VALID_CRITICALITIES:
            errors.append(f"Invalid track_criticality '{crit}'. Must be one of {sorted(VALID_CRITICALITIES)}")

        cond = str(row.get(col_map["current_condition"], "GOOD")).strip().upper()
        if cond not in VALID_CONDITIONS:
            errors.append(f"Invalid current_condition '{cond}'. Must be one of {sorted(VALID_CONDITIONS)}")

        b_stat = str(row.get(col_map["active_block_status"], "NORMAL")).strip().upper()
        if b_stat not in VALID_BLOCK_STATUSES:
            errors.append(f"Invalid active_block_status '{b_stat}'. Must be one of {sorted(VALID_BLOCK_STATUSES)}")

        # 5. Date Validations (YYYY-MM-DD)
        last_m_str = str(row.get(col_map["last_track_maintenance_date"], "")).strip()
        next_m_str = str(row.get(col_map["next_track_maintenance_date"], "")).strip()

        date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if not date_regex.match(last_m_str):
            errors.append(f"Invalid last_track_maintenance_date '{last_m_str}'. Expected format YYYY-MM-DD")
        else:
            try:
                datetime.strptime(last_m_str, "%Y-%m-%d")
            except ValueError:
                errors.append(f"last_track_maintenance_date '{last_m_str}' is not a valid calendar date")

        if not date_regex.match(next_m_str):
            errors.append(f"Invalid next_track_maintenance_date '{next_m_str}'. Expected format YYYY-MM-DD")
        else:
            try:
                datetime.strptime(next_m_str, "%Y-%m-%d")
            except ValueError:
                errors.append(f"next_track_maintenance_date '{next_m_str}' is not a valid calendar date")

        if errors:
            results["rejected_records"].append({
                "row_index": row_idx,
                "track_id": t_id or f"Row {row_idx}",
                "errors": errors,
            })
        else:
            rec = {
                "track_id": t_id,
                "zone": str(row.get(col_map["zone"], "WCR")).strip(),
                "division": str(row.get(col_map["division"], "Jabalpur (JBP)")).strip(),
                "section_code": sec_code,
                "section_name": sec_name,
                "from_station": from_stn,
                "to_station": to_stn,
                "track_type": str(row.get(col_map["track_type"], "Main Line")).strip(),
                "gauge": str(row.get(col_map["gauge"], "Broad Gauge (1676mm)")).strip(),
                "electrification": str(row.get(col_map["electrification"], "25kV AC Electric")).strip(),
                "number_of_lines": num_lines,
                "track_length_km": length_km,
                "km_from": km_from,
                "km_to": km_to,
                "maximum_permissible_speed": speed,
                "traffic_density": density,
                "line_capacity": capacity,
                "track_criticality": crit,
                "current_condition": cond,
                "last_track_maintenance_date": last_m_str,
                "next_track_maintenance_date": next_m_str,
                "active_block_status": b_stat,
            }
            results["valid_records"].append(rec)

    conn.close()
    results["valid_count"] = len(results["valid_records"])
    results["rejected_count"] = len(results["rejected_records"])
    results["success"] = results["valid_count"] > 0
    return results


def commit_valid_track_records(records: List[Dict[str, Any]], user_designation: str) -> int:
    """Commit validated records to SQLite using INSERT OR REPLACE."""
    conn = get_connection()
    cur = conn.cursor()
    committed = 0

    for r in records:
        cur.execute("""
        INSERT OR REPLACE INTO track_master (
            track_id, zone, division, section_code, section_name, from_station, to_station,
            track_type, gauge, electrification, number_of_lines, track_length_km, km_from, km_to,
            maximum_permissible_speed, traffic_density, line_capacity, track_criticality,
            current_condition, last_track_maintenance_date, next_track_maintenance_date, active_block_status,
            updated_at
        ) VALUES (
            :track_id, :zone, :division, :section_code, :section_name, :from_station, :to_station,
            :track_type, :gauge, :electrification, :number_of_lines, :track_length_km, :km_from, :km_to,
            :maximum_permissible_speed, :traffic_density, :line_capacity, :track_criticality,
            :current_condition, :last_track_maintenance_date, :next_track_maintenance_date, :active_block_status,
            CURRENT_TIMESTAMP
        )
        """, r)

        cur.execute("""
        INSERT OR IGNORE INTO track_condition (
            track_id, rail_condition, sleeper_condition, ballast_condition,
            track_geometry_condition, track_defect_count, severe_defects_count,
            required_maintenance_resources, remarks
        ) VALUES (
            ?, '60kg UIC / Sound', 'PSC Sleeper / Sound', 'Clean Cushion 300mm',
            'Within Tolerances', 0, 0, 'Routine Inspection', 'Imported via Track Master CSV'
        )
        """, (r["track_id"],))

        committed += 1

    conn.commit()
    conn.close()

    from backend.db import add_audit_log
    add_audit_log(user_designation, f"Imported {committed} Track Master records via validated CSV upload.")
    return committed


def generate_sample_track_csv() -> str:
    """Generate sample CSV data for template download."""
    sample_rows = [
        {
            "track_id": "TRK-JBP-KTE-UP-02",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "JBP-KTE",
            "section_name": "Jabalpur - Katni Heavy Freight Route",
            "from_station": "Jabalpur (JBP)",
            "to_station": "Katni Jn (KTE)",
            "track_type": "Main Line",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 2,
            "track_length_km": 91.2,
            "km_from": 990.0,
            "km_to": 1081.2,
            "maximum_permissible_speed": 130,
            "traffic_density": 145.0,
            "line_capacity": 120.0,
            "track_criticality": "HIGH",
            "current_condition": "GOOD",
            "last_track_maintenance_date": "2026-07-01",
            "next_track_maintenance_date": "2026-10-01",
            "active_block_status": "NORMAL",
        },
        {
            "track_id": "TRK-BINA-KTE-UP-01",
            "zone": "WCR",
            "division": "Jabalpur (JBP)",
            "section_code": "BINA-KTE",
            "section_name": "Bina - Katni Freight Corridor",
            "from_station": "Bina Jn (BINA)",
            "to_station": "Katni Jn (KTE)",
            "track_type": "Main Line",
            "gauge": "Broad Gauge (1676mm)",
            "electrification": "25kV AC Electric",
            "number_of_lines": 2,
            "track_length_km": 261.0,
            "km_from": 820.0,
            "km_to": 1081.0,
            "maximum_permissible_speed": 110,
            "traffic_density": 115.0,
            "line_capacity": 105.0,
            "track_criticality": "MEDIUM",
            "current_condition": "FAIR",
            "last_track_maintenance_date": "2026-05-15",
            "next_track_maintenance_date": "2026-08-30",
            "active_block_status": "MAINTENANCE_SCHEDULED",
        },
    ]
    df = pd.DataFrame(sample_rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# Automatically initialize and seed on load
init_track_db()
seed_track_db_if_empty()
