"""
backend/db.py
-------------
Unified Persistent Data & Role Authorization Layer for TRACK YUKTI.
Uses SQLite for robust, thread-safe, refresh-persistent data consistency
across Department and Chief Controller dashboards.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.track_db import (
    init_track_db,
    seed_track_db_if_empty,
    get_all_tracks,
    get_track_by_id,
    get_track_condition,
    get_track_defects,
    get_all_defects,
    get_track_maintenance_history,
    get_track_assets,
    get_track_trains,
    get_active_blocks_for_track,
    update_track_criticality,
    update_defect_status,
    validate_and_import_track_csv,
    commit_valid_track_records,
    generate_sample_track_csv,
    calculate_track_health,
    calculate_overdue_days,
)

DB_PATH = Path(__file__).parent.parent / "trackyukti.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables for BlockRequests, DepartmentTasks, Approvals, and AuditLog."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS block_requests (
        block_id TEXT PRIMARY KEY,
        department TEXT NOT NULL,
        corridor TEXT NOT NULL,
        section_track TEXT NOT NULL,
        action TEXT NOT NULL,
        asset_id TEXT NOT NULL,
        requested_duration_mins INTEGER NOT NULL,
        start_time TEXT,
        end_time TEXT,
        start_min INTEGER DEFAULT 0,
        end_min INTEGER DEFAULT 0,
        priority_score REAL DEFAULT 50.0,
        priority_level TEXT DEFAULT 'NORMAL',
        approval_status TEXT DEFAULT 'PENDING',
        is_heavy_machinery INTEGER DEFAULT 0,
        exclusive_block INTEGER DEFAULT 0,
        overdue_days REAL DEFAULT 60.0,
        last_inspection_score REAL DEFAULT 75.0,
        traffic_density REAL DEFAULT 120.0,
        corridor_priority REAL DEFAULT 1.3,
        latitude REAL DEFAULT 23.50,
        longitude REAL DEFAULT 80.20,
        created_at TEXT NOT NULL,
        created_by TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS department_tasks (
        task_id TEXT PRIMARY KEY,
        block_id TEXT NOT NULL,
        department TEXT NOT NULL,
        action TEXT NOT NULL,
        corridor TEXT NOT NULL,
        section_track TEXT NOT NULL,
        task_status TEXT DEFAULT 'PENDING',
        scheduled_start TEXT,
        scheduled_deadline TEXT,
        priority_level TEXT DEFAULT 'NORMAL',
        risk_score REAL DEFAULT 50.0,
        updated_by TEXT,
        updated_at TEXT,
        remarks TEXT,
        FOREIGN KEY (block_id) REFERENCES block_requests(block_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
        block_id TEXT NOT NULL,
        action TEXT NOT NULL,
        officer_name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        remarks TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        user TEXT NOT NULL,
        event TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    init_track_db()


def seed_if_empty() -> None:
    """Pre-seed database with realistic Jabalpur Division initial data across all 3 departments."""
    seed_track_db_if_empty()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM block_requests")
    count = cur.fetchone()[0]
    if count > 0:
        conn.close()
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Rich pre-seeded initial requests representing WCR Jabalpur Division
    initial_requests = [
        {
            "block_id": "TB-1024",
            "department": "Engineering",
            "corridor": "Jabalpur (JBP) - Katni (KTE) Heavy Freight Route",
            "section_track": "Jabalpur (JBP) - Katni (KTE) Heavy Freight Route :: DN-Main",
            "action": "Continuous Welded Rail (CWR) De-Stressing",
            "asset_id": "AST-ENG-1024",
            "requested_duration_mins": 120,
            "start_time": "01:30 IST",
            "end_time": "03:30 IST",
            "start_min": 90,
            "end_min": 210,
            "priority_score": 92.5,
            "priority_level": "CRITICAL",
            "approval_status": "APPROVED",
            "is_heavy_machinery": 1,
            "exclusive_block": 1,
            "created_by": "Sr. Divisional Engineer (Sr. DEN / Track)",
            "task_status": "COMPLETED",
        },
        {
            "block_id": "TB-1025",
            "department": "S&T",
            "corridor": "Jabalpur (JBP) - Katni (KTE) Heavy Freight Route",
            "section_track": "Jabalpur (JBP) - Katni (KTE) Heavy Freight Route :: DN-Main",
            "action": "Digital Axle Counter (DAC) Sensor Calibration",
            "asset_id": "AST-SNT-1025",
            "requested_duration_mins": 60,
            "start_time": "01:30 IST",
            "end_time": "02:30 IST",
            "start_min": 90,
            "end_min": 150,
            "priority_score": 84.0,
            "priority_level": "VERY HIGH",
            "approval_status": "APPROVED",
            "is_heavy_machinery": 0,
            "exclusive_block": 0,
            "created_by": "Sr. Divisional Signal & Telecom Engineer (Sr. DSTE)",
            "task_status": "IN PROGRESS",
        },
        {
            "block_id": "TB-1026",
            "department": "Electrical",
            "corridor": "Katni (KTE) - Singrauli Coal Logistics Line",
            "section_track": "Katni (KTE) - Singrauli Coal Logistics Line :: Coal-Line-1",
            "action": "OHE Catenary Contact Wire Tensioning",
            "asset_id": "AST-ELC-1026",
            "requested_duration_mins": 90,
            "start_time": "02:00 IST",
            "end_time": "03:30 IST",
            "start_min": 120,
            "end_min": 210,
            "priority_score": 78.5,
            "priority_level": "HIGH",
            "approval_status": "APPROVED",
            "is_heavy_machinery": 0,
            "exclusive_block": 0,
            "created_by": "Sr. Divisional Electrical Engineer (Sr. DEE / TRD)",
            "task_status": "PENDING",
        },
        {
            "block_id": "TB-1027",
            "department": "Engineering",
            "corridor": "Satna (STA) - Rewa (REWA) Branch Corridor",
            "section_track": "Satna (STA) - Rewa (REWA) Branch Corridor :: Single-Line",
            "action": "Ultrasonic Flaw Detection (USFD) Rail Testing",
            "asset_id": "AST-ENG-1027",
            "requested_duration_mins": 75,
            "start_time": "04:00 IST",
            "end_time": "05:15 IST",
            "start_min": 240,
            "end_min": 315,
            "priority_score": 88.0,
            "priority_level": "CRITICAL",
            "approval_status": "PENDING",
            "is_heavy_machinery": 0,
            "exclusive_block": 0,
            "created_by": "Assistant Divisional Engineer (ADEN / Track)",
            "task_status": "PENDING",
        },
        {
            "block_id": "TB-1028",
            "department": "S&T",
            "corridor": "Jabalpur (JBP) - Itarsi (ET) Trunk Line",
            "section_track": "Jabalpur (JBP) - Itarsi (ET) Trunk Line :: UP-Main",
            "action": "Electronic Interlocking (EI) Overhaul",
            "asset_id": "AST-SNT-1028",
            "requested_duration_mins": 105,
            "start_time": "03:30 IST",
            "end_time": "05:15 IST",
            "start_min": 210,
            "end_min": 315,
            "priority_score": 86.0,
            "priority_level": "VERY HIGH",
            "approval_status": "PENDING",
            "is_heavy_machinery": 0,
            "exclusive_block": 0,
            "created_by": "Divisional Signal & Telecom Engineer (DSTE)",
            "task_status": "PENDING",
        },
        {
            "block_id": "TB-1029",
            "department": "Electrical",
            "corridor": "Jabalpur (JBP) - Itarsi (ET) Trunk Line",
            "section_track": "Jabalpur (JBP) - Itarsi (ET) Trunk Line :: DN-Main",
            "action": "Traction Power Feeder Isolator Maintenance",
            "asset_id": "AST-ELC-1029",
            "requested_duration_mins": 90,
            "start_time": "05:00 IST",
            "end_time": "06:30 IST",
            "start_min": 300,
            "end_min": 390,
            "priority_score": 75.0,
            "priority_level": "HIGH",
            "approval_status": "PENDING",
            "is_heavy_machinery": 0,
            "exclusive_block": 1,
            "created_by": "Divisional Electrical Engineer (DEE / TRD)",
            "task_status": "PENDING",
        },
        {
            "block_id": "TB-1030",
            "department": "Engineering",
            "corridor": "Jabalpur (JBP) - Katni (KTE) Heavy Freight Route",
            "section_track": "Jabalpur (JBP) - Katni (KTE) Heavy Freight Route :: UP-Main",
            "action": "Track Tamping & Deep Screening",
            "asset_id": "AST-ENG-1030",
            "requested_duration_mins": 180,
            "start_time": "02:00 IST",
            "end_time": "05:00 IST",
            "start_min": 120,
            "end_min": 300,
            "priority_score": 95.0,
            "priority_level": "CRITICAL",
            "approval_status": "APPROVED",
            "is_heavy_machinery": 1,
            "exclusive_block": 1,
            "created_by": "Sr. Divisional Engineer (Sr. DEN / Track)",
            "task_status": "IN PROGRESS",
        },
    ]

    for req in initial_requests:
        cur.execute("""
        INSERT INTO block_requests (
            block_id, department, corridor, section_track, action, asset_id,
            requested_duration_mins, start_time, end_time, start_min, end_min,
            priority_score, priority_level, approval_status, is_heavy_machinery,
            exclusive_block, created_at, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req["block_id"], req["department"], req["corridor"], req["section_track"],
            req["action"], req["asset_id"], req["requested_duration_mins"],
            req["start_time"], req["end_time"], req["start_min"], req["end_min"],
            req["priority_score"], req["priority_level"], req["approval_status"],
            req["is_heavy_machinery"], req["exclusive_block"], now_str, req["created_by"]
        ))

        # Create corresponding department task
        task_id = f"TASK-{req['block_id']}-{req['department'][:3].upper()}"
        cur.execute("""
        INSERT INTO department_tasks (
            task_id, block_id, department, action, corridor, section_track,
            task_status, scheduled_start, scheduled_deadline, priority_level,
            risk_score, updated_by, updated_at, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id, req["block_id"], req["department"], req["action"],
            req["corridor"], req["section_track"], req["task_status"],
            req["start_time"], req["end_time"], req["priority_level"],
            req["priority_score"], req["created_by"], now_str, "Initial synchronized schedule"
        ))

    # Add initial audit events
    cur.execute("""
    INSERT INTO audit_logs (timestamp, user, event)
    VALUES
    (?, 'Chief Controller', 'Synchronized master rolling block pool initialized for Jabalpur Division'),
    (?, 'Sr. DEN / Track', 'Logged CWR De-Stressing block request on JBP-KTE route'),
    (?, 'Sr. DSTE', 'Verified Electronic Interlocking maintenance requisitions')
    """, (now_str, now_str, now_str))

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK REQUEST OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_all_block_requests() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM block_requests ORDER BY priority_score DESC, block_id ASC")
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d["request_id"] = d.get("block_id", "BLK-00")
        d["estimated_duration_mins"] = int(d.get("requested_duration_mins", 60) or 60)
        d["risk_score"] = float(d.get("priority_score", 50.0) or 50.0)
        d["overdue_days"] = float(d.get("overdue_days", 60.0) or 60.0)
        d["last_inspection_score"] = float(d.get("last_inspection_score", 75.0) or 75.0)
        d["traffic_density"] = float(d.get("traffic_density", 120.0) or 120.0)
        d["corridor_priority"] = float(d.get("corridor_priority", 1.3) or 1.3)
        d["latitude"] = float(d.get("latitude", 23.50) or 23.50)
        d["longitude"] = float(d.get("longitude", 80.20) or 80.20)
        d["is_heavy_machinery"] = bool(d.get("is_heavy_machinery", 0))
        d["exclusive_block"] = bool(d.get("exclusive_block", 0))
        rows.append(d)
    conn.close()
    return rows


def get_block_request(block_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM block_requests WHERE block_id = ?", (block_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["request_id"] = d.get("block_id", "BLK-00")
    d["estimated_duration_mins"] = int(d.get("requested_duration_mins", 60) or 60)
    d["risk_score"] = float(d.get("priority_score", 50.0) or 50.0)
    d["overdue_days"] = float(d.get("overdue_days", 60.0) or 60.0)
    d["last_inspection_score"] = float(d.get("last_inspection_score", 75.0) or 75.0)
    d["traffic_density"] = float(d.get("traffic_density", 120.0) or 120.0)
    d["corridor_priority"] = float(d.get("corridor_priority", 1.3) or 1.3)
    d["latitude"] = float(d.get("latitude", 23.50) or 23.50)
    d["longitude"] = float(d.get("longitude", 80.20) or 80.20)
    d["is_heavy_machinery"] = bool(d.get("is_heavy_machinery", 0))
    d["exclusive_block"] = bool(d.get("exclusive_block", 0))
    return d


def create_block_request(
    department: str,
    corridor: str,
    section_track: str,
    action: str,
    asset_id: str,
    requested_duration_mins: int,
    priority_score: float,
    priority_level: str,
    created_by: str,
    is_heavy_machinery: bool = False,
    exclusive_block: bool = False,
    start_min: int = 60,
) -> str:
    """Create a new block request in PENDING approval status."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM block_requests")
    cnt = cur.fetchone()[0]
    block_id = f"TB-{1000 + cnt + 1}"

    start_h, start_m = divmod(start_min, 60)
    end_min = start_min + requested_duration_mins
    end_h, end_m = divmod(end_min, 60)
    start_time = f"{start_h:02d}:{start_m:02d} IST"
    end_time = f"{end_h:02d}:{end_m:02d} IST"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO block_requests (
        block_id, department, corridor, section_track, action, asset_id,
        requested_duration_mins, start_time, end_time, start_min, end_min,
        priority_score, priority_level, approval_status, is_heavy_machinery,
        exclusive_block, created_at, created_by
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
    """, (
        block_id, department, corridor, section_track, action, asset_id,
        requested_duration_mins, start_time, end_time, start_min, end_min,
        priority_score, priority_level, 1 if is_heavy_machinery else 0,
        1 if exclusive_block else 0, now_str, created_by
    ))

    # Also register the department task as PENDING
    task_id = f"TASK-{block_id}-{department[:3].upper()}"
    cur.execute("""
    INSERT INTO department_tasks (
        task_id, block_id, department, action, corridor, section_track,
        task_status, scheduled_start, scheduled_deadline, priority_level,
        risk_score, updated_by, updated_at, remarks
    ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?, ?)
    """, (
        task_id, block_id, department, action, corridor, section_track,
        start_time, end_time, priority_level, priority_score,
        created_by, now_str, "Requisition submitted, awaiting Chief Controller approval"
    ))

    conn.commit()
    conn.close()
    add_audit_log(created_by, f"Submitted Block Request {block_id} [{action}] on {section_track}")
    return block_id


# ─────────────────────────────────────────────────────────────────────────────
# CHIEF CONTROLLER WORKFLOW ACTIONS
# ─────────────────────────────────────────────────────────────────────────────

def approve_block_request(block_id: str, officer_name: str, remarks: str = "") -> bool:
    """Chief Controller approves a block. Automatically updates status and department tasks."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM block_requests WHERE block_id = ?", (block_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("UPDATE block_requests SET approval_status = 'APPROVED' WHERE block_id = ?", (block_id,))
    cur.execute("""
    UPDATE department_tasks
    SET task_status = 'APPROVED', updated_by = ?, updated_at = ?, remarks = ?
    WHERE block_id = ? AND task_status = 'PENDING'
    """, (officer_name, now_str, remarks or "Approved by Chief Controller", block_id))

    cur.execute("""
    INSERT INTO approvals (block_id, action, officer_name, timestamp, remarks)
    VALUES (?, 'APPROVED', ?, ?, ?)
    """, (block_id, officer_name, now_str, remarks))

    conn.commit()
    conn.close()
    add_audit_log(officer_name, f"APPROVED Block Request {block_id} ({row['department']}). Work dispatched to department queue.")
    return True


def reject_block_request(block_id: str, officer_name: str, remarks: str = "") -> bool:
    """Chief Controller rejects a block request."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM block_requests WHERE block_id = ?", (block_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("UPDATE block_requests SET approval_status = 'REJECTED' WHERE block_id = ?", (block_id,))
    cur.execute("""
    UPDATE department_tasks
    SET task_status = 'REJECTED', updated_by = ?, updated_at = ?, remarks = ?
    WHERE block_id = ?
    """, (officer_name, now_str, remarks or "Rejected by Chief Controller", block_id))

    cur.execute("""
    INSERT INTO approvals (block_id, action, officer_name, timestamp, remarks)
    VALUES (?, 'REJECTED', ?, ?, ?)
    """, (block_id, officer_name, now_str, remarks))

    conn.commit()
    conn.close()
    add_audit_log(officer_name, f"REJECTED Block Request {block_id} ({row['department']}). Reason: {remarks or 'Operational constraints'}")
    return True


def close_block_request(block_id: str, officer_name: str, remarks: str = "") -> bool:
    """Chief Controller performs final verification and closure once department work is completed."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM block_requests WHERE block_id = ?", (block_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("UPDATE block_requests SET approval_status = 'CLOSED' WHERE block_id = ?", (block_id,))
    cur.execute("""
    INSERT INTO approvals (block_id, action, officer_name, timestamp, remarks)
    VALUES (?, 'CLOSED', ?, ?, ?)
    """, (block_id, officer_name, now_str, remarks or "Verified track clearance and closed"))

    conn.commit()
    conn.close()
    add_audit_log(officer_name, f"CLOSED Block {block_id}. Track clearance verified, normal speed restored.")
    return True



# ─────────────────────────────────────────────────────────────────────────────
# DEPARTMENT TASKS & STRICT ROLE-BASED ACCESS CONTROL
# ─────────────────────────────────────────────────────────────────────────────

def get_department_tasks(department: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve tasks. If department is provided, returns ONLY that department's tasks."""
    conn = get_connection()
    cur = conn.cursor()
    if department:
        cur.execute("SELECT * FROM department_tasks WHERE department = ? ORDER BY task_id ASC", (department,))
    else:
        cur.execute("SELECT * FROM department_tasks ORDER BY department ASC, task_id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM department_tasks WHERE task_id = ?", (task_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_task_status(
    task_id: str,
    new_status: str,
    user_role: str,
    user_dept: str,
    user_designation: str,
    remarks: str = ""
) -> bool:
    """
    Update department task status with strict backend security validation.
    Department 1 (Engineering) CANNOT modify Department 2 (S&T) or Department 3 (Electrical) tasks.
    Raises PermissionError if unauthorized.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM department_tasks WHERE task_id = ?", (task_id,))
    task = cur.fetchone()
    if not task:
        conn.close()
        raise ValueError(f"Task {task_id} does not exist.")

    task_dept = task["department"]

    # BACKEND ROLE-BASED ACCESS CHECK:
    if user_role == "CHIEF_CONTROLLER":
        # Chief controller has operational oversight
        pass
    else:
        # Department users can ONLY modify their own department's tasks
        if user_dept != task_dept:
            conn.close()
            error_msg = f"Access Denied: {user_dept} ({user_role}) cannot modify {task_dept}'s task {task_id}."
            add_audit_log(user_designation, f"SECURITY VIOLATION: Unauthorized attempt to modify {task_dept}'s task {task_id}")
            raise PermissionError(error_msg)

    valid_statuses = ["PENDING", "APPROVED", "IN PROGRESS", "COMPLETED", "REJECTED"]
    if new_status not in valid_statuses:
        conn.close()
        raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    UPDATE department_tasks
    SET task_status = ?, updated_by = ?, updated_at = ?, remarks = ?
    WHERE task_id = ?
    """, (new_status, user_designation, now_str, remarks or f"Status set to {new_status}", task_id))

    conn.commit()
    conn.close()
    add_audit_log(user_designation, f"Updated Task {task_id} ({task_dept}) status to {new_status}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CONTROLLER STATS & AUDIT LOGS
# ─────────────────────────────────────────────────────────────────────────────

def get_controller_stats() -> Dict[str, Any]:
    """Calculate centralized operational statistics across all requests and tasks."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM block_requests")
    total_requests = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM block_requests WHERE approval_status = 'PENDING'")
    pending_approval = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM block_requests WHERE approval_status = 'APPROVED'")
    approved_blocks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM department_tasks WHERE task_status = 'IN PROGRESS'")
    active_blocks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM department_tasks WHERE task_status = 'COMPLETED'")
    completed_blocks = cur.fetchone()[0]

    # Department-wise breakdown
    dept_stats = {}
    for d in ["Engineering", "S&T", "Electrical"]:
        cur.execute("SELECT COUNT(*) FROM department_tasks WHERE department = ?", (d,))
        d_total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM department_tasks WHERE department = ? AND task_status = 'PENDING'", (d,))
        d_pend = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM department_tasks WHERE department = ? AND task_status = 'APPROVED'", (d,))
        d_app = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM department_tasks WHERE department = ? AND task_status = 'IN PROGRESS'", (d,))
        d_prog = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM department_tasks WHERE department = ? AND task_status = 'COMPLETED'", (d,))
        d_comp = cur.fetchone()[0]

        dept_stats[d] = {
            "total": d_total,
            "pending": d_pend,
            "approved": d_app,
            "in_progress": d_prog,
            "completed": d_comp,
        }

    conn.close()
    return {
        "total_requests": total_requests,
        "pending_approval": pending_approval,
        "approved_blocks": approved_blocks,
        "active_blocks": active_blocks,
        "completed_blocks": completed_blocks,
        "department_stats": dept_stats,
    }


def add_audit_log(user: str, event: str) -> None:
    try:
        conn = get_connection()
        cur = conn.cursor()
        now_str = datetime.now().strftime("%H:%M:%S IST")
        cur.execute("INSERT INTO audit_logs (timestamp, user, event) VALUES (?, ?, ?)", (now_str, user, event))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_recent_audit_logs(limit: int = 15) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def reset_db() -> None:
    """Reset the database to initial clean state by clearing and re-seeding tables."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS department_tasks")
        cur.execute("DROP TABLE IF EXISTS block_requests")
        cur.execute("DROP TABLE IF EXISTS approvals")
        cur.execute("DROP TABLE IF EXISTS audit_logs")
        cur.execute("DROP TABLE IF EXISTS track_defects")
        cur.execute("DROP TABLE IF EXISTS track_condition")
        cur.execute("DROP TABLE IF EXISTS track_maintenance_history")
        cur.execute("DROP TABLE IF EXISTS track_assets")
        cur.execute("DROP TABLE IF EXISTS track_trains")
        cur.execute("DROP TABLE IF EXISTS track_master")
        conn.commit()
        conn.close()
    except Exception:
        pass
    init_db()
    seed_if_empty()


# Automatically initialize and seed upon import
init_db()
seed_if_empty()
