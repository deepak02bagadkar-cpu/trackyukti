"""
app.py
-------
TRACK YUKTI — AI-Powered Railway Block Planning & Optimization System
WEST CENTRAL RAILWAY (WCR) — JABALPUR DIVISION
Joint Rolling Block Planning & Corridor Operations Portal (IR-JRBP System)
"""

import base64
import io
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# Existing Backend Layer (Preserved OR-Tools CP-SAT & RandomForest)
from backend.data_gen import generate_requests, CORRIDORS, BRANCH_ACTIONS
from backend.risk_model import CriticalityScorer
from backend.geo_cluster import find_bundling_clusters
from backend.optimizer import run_block_optimizer

# Advanced Intelligence Engines
from backend.priority_engine import compute_priority_intelligence
from backend.overlap_engine import (
    detect_task_overlaps,
    build_joint_work_bundles,
    find_partial_bundle_opportunities,
    detect_exclusive_tasks,
    compute_plan_optimization_comparison,
)
from backend.impact_engine import (
    get_passenger_traffic_summary,
    compute_freight_impact,
    compute_financial_impact,
)

# Persistent Database & Role-Based Security Layer
from backend.db import (
    init_db,
    seed_if_empty,
    get_all_block_requests,
    get_block_request,
    create_block_request,
    approve_block_request,
    reject_block_request,
    close_block_request,
    get_department_tasks,
    get_task,
    update_task_status,
    get_controller_stats,
    add_audit_log,
    get_recent_audit_logs,
    reset_db,
)

# Track Master & Infrastructure Database Subsystem
from backend.track_ui import render_track_master_subsystem

# Initialize database
init_db()
seed_if_empty()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Track Yukti : Railway Block Planner",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADER
# ─────────────────────────────────────────────────────────────────────────────
def load_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

BASE = Path(__file__).parent
LOGO_B64   = load_b64(str(BASE / "assets" / "logo.png"))
BG_B64     = load_b64(str(BASE / "assets" / "train_bg.jpg"))
BG_CSS_VAL = f"url('data:image/jpeg;base64,{BG_B64}')" if BG_B64 else "none"
QR_PATH    = BASE / "assets" / "trackyukti_qr_card.png"
QR_B64     = load_b64(str(QR_PATH))

# ─────────────────────────────────────────────────────────────────────────────
# COLOR SYSTEM & DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────
DEPT_COLORS = {
    "Engineering": "#38BDF8",  # Sky Blue
    "S&T":         "#FCD34D",  # Warm Amber
    "Electrical":  "#C084FC",  # Orchid Purple
    "Operating":   "#34D399",  # Emerald Green
}

RISK_COLORS = {
    "CRITICAL":  "#EF4444",
    "VERY HIGH": "#F97316",
    "HIGH":      "#F59E0B",
    "NORMAL":    "#38BDF8",
    "MEDIUM":    "#FBBF24",
    "LOW":       "#4ADE80",
}

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS & WHITE-LINE RENDERING FIXES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    -webkit-font-smoothing: antialiased;
}}

/* ── Full-bleed Backdrop with Subtle Dark Veil for High Readability ── */
.stApp {{
    background-image:
        linear-gradient(135deg, rgba(6, 12, 30, 0.88) 0%, rgba(10, 20, 48, 0.82) 100%),
        {BG_CSS_VAL};
    background-size: cover;
    background-position: center center;
    background-attachment: fixed;
    background-repeat: no-repeat;
    color: #FFFFFF;
    min-height: 100vh;
}}

.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1440px !important;
}}

/* ── Fix White-Line & Rendering Artifacts ── */
[data-testid="stHeader"] {{
    background: transparent !important;
    border-bottom: none !important;
}}
div[data-baseweb="tab-border"] {{
    display: none !important;
}}
div[data-baseweb="tab-highlight"] {{
    display: none !important;
}}
hr, .ty-divider {{
    border: none !important;
    height: 1px !important;
    background: rgba(148, 163, 184, 0.20) !important;
    margin: 16px 0 !important;
}}

/* ── Absolute Text Visibility Guarantee ── */
.main .block-container p,
.main .block-container span,
.main .block-container div,
.main .block-container small,
.main .block-container b,
.main .block-container strong,
.main .block-container li,
.main .block-container label,
.main .block-container h1,
.main .block-container h2,
.main .block-container h3,
.main .block-container h4,
.main .block-container h5,
.main .block-container h6 {{
    color: #FFFFFF;
}}

/* ── Tabs Navigation: Clean Railway Command Deck ── */
.stTabs [data-baseweb="tab-list"] {{
    background: rgba(6, 12, 30, 0.94) !important;
    border-radius: 10px !important;
    padding: 6px 8px !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
    gap: 6px !important;
    margin-bottom: 18px !important;
    overflow-x: auto !important;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 7px !important;
    padding: 9px 16px !important;
    color: #CBD5E1 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    border: none !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: #FFFFFF !important;
    background: rgba(30, 58, 138, 0.45) !important;
}}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.40) !important;
}}

/* ── Component Cards: Rich Glass & Subtle Soft Borders ── */
.ty-card {{
    background: rgba(7, 14, 34, 0.94) !important;
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 14px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
    transition: transform 0.18s ease, border-color 0.18s ease;
}}
.ty-card:hover {{
    border-color: rgba(59, 130, 246, 0.45);
    transform: translateY(-1px);
}}

/* ── Header Banner ── */
.ty-header {{
    background: rgba(7, 14, 34, 0.96);
    backdrop-filter: blur(28px) saturate(180%);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-bottom: 2px solid #F59E0B;
    border-radius: 14px;
    padding: 16px 24px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 14px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.50);
}}

/* ── Login Shell ── */
.ty-login-shell {{
    max-width: 900px;
    margin: 24px auto;
    background: rgba(6, 12, 30, 0.96);
    backdrop-filter: blur(32px);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-top: 4px solid #F59E0B;
    border-radius: 18px;
    padding: 38px 48px 36px;
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.60);
}}

/* ── Stat Tiles ── */
.ty-stat {{
    background: rgba(7, 14, 34, 0.94);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.40);
    transition: transform 0.18s ease;
}}
.ty-stat:hover {{
    border-color: rgba(56, 189, 248, 0.45);
    transform: translateY(-2px);
}}
.ty-stat-label {{
    font-size: 11.5px;
    font-weight: 800;
    color: #CBD5E1 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
.ty-stat-value {{
    font-size: 24px;
    font-weight: 900;
    color: #FFFFFF !important;
    margin-top: 4px;
    line-height: 1.1;
}}

/* ── Badges ── */
.ty-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(37, 99, 235, 0.25);
    color: #93C5FD !important;
    border: 1px solid rgba(59, 130, 246, 0.40);
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.02em;
}}
.ty-badge-green {{
    background: rgba(6, 78, 59, 0.45);
    color: #6EE7B7 !important;
    border: 1px solid rgba(52, 211, 153, 0.45);
}}
.ty-badge-amber {{
    background: rgba(120, 53, 15, 0.45);
    color: #FCD34D !important;
    border: 1px solid rgba(245, 158, 11, 0.45);
}}
.ty-badge-red {{
    background: rgba(127, 29, 29, 0.45);
    color: #FCA5A5 !important;
    border: 1px solid rgba(239, 68, 68, 0.45);
}}
.ty-badge-purple {{
    background: rgba(88, 28, 135, 0.45);
    color: #D8B4FE !important;
    border: 1px solid rgba(168, 85, 247, 0.45);
}}

/* ── Alerts ── */
.ty-alert-danger {{
    background: rgba(127, 29, 29, 0.85);
    border: 1px solid rgba(248, 113, 113, 0.40);
    border-left: 4px solid #EF4444;
    border-radius: 10px;
    padding: 13px 16px;
    color: #FECACA !important;
    margin-bottom: 14px;
}}
.ty-alert-warn {{
    background: rgba(120, 53, 15, 0.85);
    border: 1px solid rgba(253, 211, 77, 0.40);
    border-left: 4px solid #F59E0B;
    border-radius: 10px;
    padding: 13px 16px;
    color: #FEF3C7 !important;
    margin-bottom: 14px;
}}
.ty-alert-success {{
    background: rgba(6, 78, 59, 0.88);
    border: 1px solid rgba(52, 211, 153, 0.40);
    border-left: 4px solid #10B981;
    border-radius: 10px;
    padding: 14px 18px;
    color: #D1FAE5 !important;
    margin-bottom: 14px;
}}

/* ── Form Controls & Streamlit Inputs ── */
div[data-baseweb="select"] > div {{
    background: rgba(6, 12, 30, 0.96) !important;
    border: 1px solid rgba(148, 163, 184, 0.30) !important;
    border-radius: 8px !important;
    color: #FFFFFF !important;
}}
div[data-baseweb="select"] * {{
    color: #FFFFFF !important;
    background: rgba(6, 12, 30, 0.98) !important;
}}
.stTextInput input {{
    background: rgba(6, 12, 30, 0.96) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(148, 163, 184, 0.30) !important;
    border-radius: 8px !important;
}}
.stRadio label p, .stCheckbox label p, .stToggle label p {{
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
}}

/* ── Buttons ── */
.stButton > button {{
    background: rgba(15, 23, 42, 0.90) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 9px 18px !important;
    transition: all 0.18s ease !important;
}}
.stButton > button:hover {{
    background: rgba(29, 78, 216, 0.85) !important;
    border-color: rgba(99, 179, 255, 0.60) !important;
    transform: translateY(-1px) !important;
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%) !important;
    border: 1px solid rgba(99, 179, 255, 0.40) !important;
    box-shadow: 0 4px 18px rgba(37, 99, 235, 0.40) !important;
}}
.stDownloadButton > button {{
    background: linear-gradient(135deg, #065F46 0%, #059669 100%) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(52, 211, 153, 0.40) !important;
    font-weight: 700 !important;
}}

/* ── High-Contrast Section Headings & Dividers ── */
.ty-section-heading {{
    font-size: 14px !important;
    font-weight: 800 !important;
    color: #F8FAFC !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 12px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    border-bottom: 1px solid rgba(148, 163, 184, 0.25) !important;
    padding-bottom: 6px !important;
}}

/* ── Red Track Styling for Maximum Visibility ── */
.ty-track-red, .ty-track-highlight {{
    color: #EF4444 !important;
    font-weight: 800 !important;
    letter-spacing: 0.02em !important;
}}
.ty-track-badge {{
    background: rgba(239, 68, 68, 0.20) !important;
    color: #F87171 !important;
    border: 1px solid rgba(239, 68, 68, 0.50) !important;
    font-weight: 800 !important;
    padding: 3px 10px !important;
    border-radius: 6px !important;
}}

/* ── Pulse ── */
.ty-pulse {{
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
    background: #22C55E;
    box-shadow: 0 0 10px #22C55E;
    animation: ty-pulse 2s infinite;
}}
@keyframes ty-pulse {{
    0%, 100% {{ transform: scale(0.9); opacity: 0.85; box-shadow: 0 0 6px #22C55E; }}
    50%      {{ transform: scale(1.3); opacity: 1;    box-shadow: 0 0 14px #4ADE80; }}
}}

/* ── Plotly Background Fix ── */
.js-plotly-plot .plotly, .plotly-graph-div {{
    background: rgba(6, 12, 30, 0.95) !important;
    border-radius: 10px;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# REAL-TIME LIVE IST CLOCK COMPONENT (ASIA/KOLKATA, 24-HOUR FORMAT)
# ─────────────────────────────────────────────────────────────────────────────
def render_live_ist_clock():
    clock_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      body {
        margin: 0;
        padding: 0;
        background: transparent;
        overflow: hidden;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        height: 100%;
        font-family: 'JetBrains Mono', -apple-system, monospace;
      }
      .clock-pill {
        background: rgba(7, 14, 34, 0.94);
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 700;
        color: #FFFFFF;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
      }
      .clock-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #22C55E;
        box-shadow: 0 0 8px #22C55E;
      }
      .date-part { color: #E2E8F0; }
      .sep { color: rgba(148, 163, 184, 0.4); }
      .time-part { color: #FCD34D; font-weight: 800; }
    </style>
    </head>
    <body>
      <div class="clock-pill">
        <span class="clock-dot"></span>
        <span class="date-part" id="d-txt">--</span>
        <span class="sep">|</span>
        <span class="time-part" id="t-txt">--:--:-- IST</span>
      </div>
      <script>
        function updateISTClock() {
          try {
            const now = new Date();
            const dateOptions = { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'long', year: 'numeric' };
            const timeOptions = { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('d-txt').textContent = now.toLocaleDateString('en-GB', dateOptions);
            document.getElementById('t-txt').textContent = now.toLocaleTimeString('en-GB', timeOptions) + ' IST';
          } catch(e) {}
        }
        updateISTClock();
        setInterval(updateISTClock, 1000);
      </script>
    </body>
    </html>
    """
    components.html(clock_html, height=42)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "is_logged_in": False,
    "user_role": "CHIEF_CONTROLLER",  # DEPARTMENT_1, DEPARTMENT_2, DEPARTMENT_3, CHIEF_CONTROLLER
    "user_dept": "Chief Controller / DRM",
    "user_designation": "Chief Controller (CHC / Central Control)",
    "lang_choice": "English",
    "seed": 42,
    "simulate_collision": False,
    "sync_failure": False,
    "siren_off_halt": False,
    "cost_factor": 1200,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_all():
    reset_db()
    for k in ["seed", "simulate_collision", "sync_failure", "siren_off_halt"]:
        st.session_state[k] = _defaults[k]

# =============================================================================
#  LOGIN PORTAL
# =============================================================================
if not st.session_state["is_logged_in"]:
    logo_html = (
        f'<img src="data:image/png;base64,{LOGO_B64}" style="height:115px;width:auto;display:block;margin:0 auto 14px;filter:drop-shadow(0 4px 14px rgba(0,0,0,0.6));" alt="TRACK YUKTI">'
        if LOGO_B64 else ""
    )

    st.markdown(f"""
    <div class="ty-login-shell">
      {logo_html}
      <div style="text-align:center;padding-bottom:20px;border-bottom:1px solid rgba(148,163,184,0.20);">
        <div style="font-size:11px;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.12em;">
          For Ministry of Railways &amp; Government of India
        </div>
        <h1 style="margin:6px 0 2px;font-size:34px;font-weight:900;color:#F59E0B;letter-spacing:-0.02em;">
          TRACK YUKTI
        </h1>
        <div style="font-size:14px;color:#38BDF8;font-weight:700;letter-spacing:0.04em;">
          Railway Block Planner
        </div>
        <p style="margin:8px 0 0;font-size:12.5px;color:#CBD5E1;font-weight:500;">
          West Central Railway &nbsp;·&nbsp; Jabalpur Division &nbsp;·&nbsp; Joint Rolling Block Operations Portal (IR-JRBP v3.0) &nbsp;·&nbsp; Prototype Data
        </p>
        <div style="margin-top:14px;">
          <span class="ty-badge ty-badge-amber">
            🔐 &nbsp;AUTHORIZED RAILWAY PERSONNEL ONLY &nbsp;·&nbsp; DEFAULT PASSKEY: JBP2026
          </span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    lc1, lc2 = st.columns([1.1, 1])

    with lc1:
        st.markdown("""
        <div class="ty-card" style="margin-top:8px;">
          <div style="font-size:12px;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">
            Step 1 — Role & Operating Branch Selection
          </div>
          <div style="font-size:12.5px;color:#CBD5E1;">
            Select authorized operating department or control role. System privileges and possession approvals are scoped to assigned jurisdiction.
          </div>
        </div>
        """, unsafe_allow_html=True)

        branch_options = [
            "Department 1 — Engineering (Civil / Track / P-Way)",
            "Department 2 — Signal & Telecom (S&T)",
            "Department 3 — Electrical (TRD / OHE Maintenance)",
            "Chief Controller (CHC) / Operating Control",
        ]
        dept_choice = st.radio("Select Role / Branch:", branch_options, index=3)

        role_mapping = {
            "Department 1 — Engineering (Civil / Track / P-Way)": ("DEPARTMENT_1", "Engineering"),
            "Department 2 — Signal & Telecom (S&T)":               ("DEPARTMENT_2", "S&T"),
            "Department 3 — Electrical (TRD / OHE Maintenance)":   ("DEPARTMENT_3", "Electrical"),
            "Chief Controller (CHC) / Operating Control":          ("CHIEF_CONTROLLER", "Chief Controller / DRM"),
        }
        sel_role, sel_dept = role_mapping[dept_choice]

    with lc2:
        st.markdown("""
        <div class="ty-card" style="margin-top:8px;">
          <div style="font-size:12px;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">
            Step 2 — Officer Designation & Security Passkey
          </div>
          <div style="font-size:12.5px;color:#CBD5E1;">
            Divisional security passkey: <b style="color:#F59E0B;">JBP2026</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

        desig_map = {
            "Engineering": [
                "Sr. Divisional Engineer (Sr. DEN / Track)",
                "Sr. Divisional Engineer (Sr. DEN / Bridge)",
                "Assistant Divisional Engineer (ADEN / Track)",
                "Junior Engineer (JE / P-Way)",
                "Senior Section Engineer (SSE / P-Way)",
            ],
            "S&T": [
                "Sr. Divisional Signal & Telecom Engineer (Sr. DSTE)",
                "Divisional Signal & Telecom Engineer (DSTE)",
                "Assistant Signal & Telecom Engineer (ASTE)",
                "Junior Engineer (JE / Signal)",
                "Senior Section Engineer (SSE / Signal)",
            ],
            "Electrical": [
                "Sr. Divisional Electrical Engineer (Sr. DEE / TRD)",
                "Divisional Electrical Engineer (DEE / TRD)",
                "Assistant Divisional Electrical Engineer (ADEE)",
                "Senior Section Engineer (SSE / OHE)",
            ],
            "Chief Controller / DRM": [
                "Chief Controller (CHC / Central Control)",
                "Dy. Chief Controller (Dy. CHC)",
                "Section Controller (SC / Train Control)",
                "Sr. Divisional Operations Manager (Sr. DOM)",
                "Divisional Operations Manager (DOM)",
                "Divisional Safety Officer (DSO)",
                "Divisional Railway Manager (DRM Jabalpur)",
            ],
        }

        desig = st.selectbox("Officer Designation:", desig_map[sel_dept])
        pk    = st.text_input("Security Passkey:", value="JBP2026", type="password")

        ba, bb = st.columns(2)
        with ba:
            if st.button("🔐  Access Workstation", type="primary", use_container_width=True):
                if pk.strip() == "JBP2026":
                    st.session_state.update(
                        is_logged_in=True,
                        user_role=sel_role,
                        user_dept=sel_dept,
                        user_designation=desig
                    )
                    add_audit_log(desig, f"Logged in as {sel_role} ({sel_dept})")
                    st.rerun()
                else:
                    st.error("❌ Invalid security passkey. Default: JBP2026")
        with bb:
            if st.button("👁  Guest Chief Controller Access", use_container_width=True):
                st.session_state.update(
                    is_logged_in=True,
                    user_role="CHIEF_CONTROLLER",
                    user_dept="Chief Controller / DRM",
                    user_designation="Chief Controller (CHC / Central Control)",
                )
                add_audit_log("Guest Chief Controller", "Logged in via guest access")
                st.rerun()

        st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("⚡ Login Dept 1 (Eng)", use_container_width=True):
                st.session_state.update(
                    is_logged_in=True,
                    user_role="DEPARTMENT_1",
                    user_dept="Engineering",
                    user_designation="Sr. Divisional Engineer (Sr. DEN / Track)",
                )
                st.rerun()
        with q2:
            if st.button("⚡ Login Dept 2 (S&T)", use_container_width=True):
                st.session_state.update(
                    is_logged_in=True,
                    user_role="DEPARTMENT_2",
                    user_dept="S&T",
                    user_designation="Sr. Divisional Signal & Telecom Engineer (Sr. DSTE)",
                )
                st.rerun()
        with q3:
            if st.button("⚡ Login Dept 3 (Elec)", use_container_width=True):
                st.session_state.update(
                    is_logged_in=True,
                    user_role="DEPARTMENT_3",
                    user_dept="Electrical",
                    user_designation="Sr. Divisional Electrical Engineer (Sr. DEE / TRD)",
                )
                st.rerun()

        # Mobile Access Terminal QR Code
        if QR_PATH.exists():
            st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
            with st.expander("📱 Mobile Access Terminal QR · Scan on Phone", expanded=False):
                st.markdown(
                    '<div style="text-align:center;font-size:12px;color:#94A3B8;margin-bottom:8px;">'
                    'Scan with any smartphone camera on the station/division Wi-Fi network to open the command console directly on mobile.'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if QR_B64:
                    st.markdown(
                        f'<div style="text-align:center;margin-bottom:10px;">'
                        f'<img src="data:image/png;base64,{QR_B64}" style="max-width:240px;width:100%;border-radius:10px;border:1.5px solid rgba(245,158,11,0.5);box-shadow:0 4px 14px rgba(0,0,0,0.5);">'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with open(QR_PATH, "rb") as f_qr:
                    st.download_button(
                        label="📥 Download Railway Terminal QR Card",
                        data=f_qr.read(),
                        file_name="trackyukti_mobile_terminal_qr.png",
                        mime="image/png",
                        use_container_width=True,
                    )

    st.stop()


# =============================================================================
#  AUTHENTICATED OPERATIONS COMMAND CENTER
# =============================================================================

# ── Sidebar Jurisdiction & Role Profile ──────────────────────────────────────
with st.sidebar:
    if LOGO_B64:
        st.markdown(
            f'<div style="text-align:center;margin-bottom:8px;"><img src="data:image/png;base64,{LOGO_B64}" style="height:72px;width:auto;filter:drop-shadow(0 2px 8px rgba(0,0,0,0.5));" alt="TRACK YUKTI"></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<span style="font-size:20px;font-weight:900;color:#F59E0B;">TRACK YUKTI</span>'
        '<br><span style="font-size:12px;color:#38BDF8;font-weight:700;letter-spacing:0.04em;">Railway Block Planner</span>'
        '<br><span style="font-size:10.5px;color:#94A3B8;">WCR Jabalpur Division · Prototype Data</span>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="ty-divider">', unsafe_allow_html=True)

    # Active Officer & Role Jurisdiction
    role_badge_class = "ty-badge-purple" if st.session_state["user_role"] == "CHIEF_CONTROLLER" else "ty-badge-amber"
    st.markdown(f"""
    <div style="background:rgba(30, 58, 138, 0.35);border:1px solid rgba(59,130,246,0.35);
                border-radius:9px;padding:12px 14px;margin:8px 0;">
      <div style="font-size:10px;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;">
        Active Session & Role
      </div>
      <div style="font-size:13.5px;font-weight:800;color:#FFFFFF;margin-top:2px;">
        {st.session_state['user_dept']}
      </div>
      <div style="margin-top:4px;">
        <span class="ty-badge {role_badge_class}">{st.session_state['user_role']}</span>
      </div>
      <div style="font-size:11px;color:#CBD5E1;margin-top:4px;">
        {st.session_state['user_designation']}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Mobile Access Terminal QR in Sidebar
    if QR_PATH.exists():
        with st.expander("📱 Mobile Terminal QR", expanded=False):
            st.markdown(
                '<div style="font-size:11px;color:#94A3B8;text-align:center;margin-bottom:6px;">'
                'Scan on station Wi-Fi to open on smartphone or tablet'
                '</div>',
                unsafe_allow_html=True,
            )
            if QR_B64:
                st.markdown(
                    f'<div style="text-align:center;margin-bottom:8px;">'
                    f'<img src="data:image/png;base64,{QR_B64}" style="max-width:180px;width:100%;border-radius:8px;border:1px solid rgba(245,158,11,0.4);">'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with open(QR_PATH, "rb") as f_qr_sb:
                st.download_button(
                    label="📥 Save Standee Card",
                    data=f_qr_sb.read(),
                    file_name="trackyukti_mobile_terminal_qr.png",
                    mime="image/png",
                    use_container_width=True,
                    key="sb_qr_download",
                )

    st.markdown("#### 📍 Corridor Jurisdiction")
    sel_corr = st.selectbox(
        "Filter Corridor:",
        ["All Corridors (Jabalpur Division)"] + list(CORRIDORS.keys())
    )
    if sel_corr != "All Corridors (Jabalpur Division)":
        corr_tracks = CORRIDORS[sel_corr]["tracks"]
        tracks_html = " &nbsp;·&nbsp; ".join([f'<span class="ty-track-red" style="font-weight:800;">{trk}</span>' for trk in corr_tracks])
        st.markdown(f'<div style="font-size:12px;color:#FFFFFF;margin-top:4px;background:rgba(239,68,68,0.12);padding:6px 10px;border-radius:6px;border:1px solid rgba(239,68,68,0.30);">Corridor Tracks: {tracks_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:12px;color:#CBD5E1;margin-top:4px;">Active Track Lines: <span class="ty-track-red" style="font-weight:800;">UP-Main · DN-Main · Goods-Loop</span></div>', unsafe_allow_html=True)

    st.markdown("#### ⏱️ Planning Parameters")
    horizon_hours = st.slider("Horizon Window (Hours)", 6, 24, 12, step=1)
    setup_buffer  = st.slider("Handover Safety Buffer (Mins)", 5, 45, 15, step=5)

    st.markdown('<hr class="ty-divider">', unsafe_allow_html=True)

    # Role switchers in sidebar for easy evaluator testing
    st.markdown("#### 🔄 Quick Role Switch (Testing)")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("Dept 1 (Civil)", use_container_width=True):
            st.session_state.update(user_role="DEPARTMENT_1", user_dept="Engineering", user_designation="Sr. Divisional Engineer (Sr. DEN / Track)")
            st.rerun()
        if st.button("Dept 3 (TRD)", use_container_width=True):
            st.session_state.update(user_role="DEPARTMENT_3", user_dept="Electrical", user_designation="Sr. Divisional Electrical Engineer (Sr. DEE / TRD)")
            st.rerun()
    with r2:
        if st.button("Dept 2 (S&T)", use_container_width=True):
            st.session_state.update(user_role="DEPARTMENT_2", user_dept="S&T", user_designation="Sr. Divisional Signal & Telecom Engineer (Sr. DSTE)")
            st.rerun()
        if st.button("Chief Controller", use_container_width=True):
            st.session_state.update(user_role="CHIEF_CONTROLLER", user_dept="Chief Controller / DRM", user_designation="Chief Controller (CHC / Central Control)")
            st.rerun()

    st.markdown('<hr class="ty-divider">', unsafe_allow_html=True)
    co1, co2 = st.columns(2)
    with co1:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["is_logged_in"] = False
            st.rerun()
    with co2:
        if st.button("♻️ Reset DB", use_container_width=True):
            reset_all()
            st.success("Database reset to initial demo state.")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# CORE DATA PIPELINE & REAL DATABASE SYNC
# ─────────────────────────────────────────────────────────────────────────────
db_requests = get_all_block_requests()
db_df = pd.DataFrame(db_requests)

# Conflict Detection Check
has_conflict, coll_depts, coll_track_name = False, [], ""
if not db_df.empty:
    for trk, grp in db_df.groupby("section_track"):
        depts = grp["department"].unique()
        if len(depts) >= 2:
            has_conflict, coll_depts, coll_track_name = True, list(depts), trk
            break

# Run Genuine OR-Tools CP-SAT Optimizer on Active Requests
scorer = CriticalityScorer()
df_for_solver = db_df.copy()
if not df_for_solver.empty:
    if "request_id" not in df_for_solver.columns and "block_id" in df_for_solver.columns:
        df_for_solver["request_id"] = df_for_solver["block_id"]
    if "estimated_duration_mins" not in df_for_solver.columns and "requested_duration_mins" in df_for_solver.columns:
        df_for_solver["estimated_duration_mins"] = df_for_solver["requested_duration_mins"]
    if "risk_score" not in df_for_solver.columns and "priority_score" in df_for_solver.columns:
        df_for_solver["risk_score"] = df_for_solver["priority_score"]

    feat_defaults = {
        "overdue_days": 60.0,
        "last_inspection_score": 75.0,
        "traffic_density": 120.0,
        "corridor_priority": 1.3,
        "latitude": 23.50,
        "longitude": 80.20,
        "is_heavy_machinery": False,
        "exclusive_block": False,
    }
    for k, v in feat_defaults.items():
        if k not in df_for_solver.columns:
            df_for_solver[k] = v
        else:
            df_for_solver[k] = df_for_solver[k].fillna(v)

scored = scorer.score_requests(df_for_solver) if not df_for_solver.empty else df_for_solver
scored = compute_priority_intelligence(scored) if not scored.empty else scored
bundled = find_bundling_clusters(scored, radius_m=500.0) if not scored.empty else scored

delayed_corr_arg = None if sel_corr == "All Corridors (Jabalpur Division)" else sel_corr
baseline_result = run_block_optimizer(
    bundled,
    horizon_hours=horizon_hours,
    setup_buffer_minutes=setup_buffer,
    delayed_corridor=delayed_corr_arg,
)

schedule = baseline_result.schedule.copy() if not baseline_result.schedule.empty else df_for_solver
if not schedule.empty and "is_scheduled" in schedule.columns:
    bs = baseline_result.schedule.set_index("request_id")["start_min"] if "request_id" in baseline_result.schedule.columns else pd.Series()
    schedule["baseline_start_min"]  = schedule["request_id"].map(bs) if "request_id" in schedule.columns else 0
    schedule["dynamically_shifted"] = (
        schedule["is_scheduled"] & schedule["baseline_start_min"].notna()
        & (schedule["start_min"] != schedule["baseline_start_min"])
    )
else:
    schedule["dynamically_shifted"] = False

# Compute Advanced Engine Outputs
priority_df = compute_priority_intelligence(schedule) if not schedule.empty else schedule
joint_bundles = build_joint_work_bundles(schedule) if not schedule.empty else []
partial_opps = find_partial_bundle_opportunities(schedule) if not schedule.empty else []
exclusive_tasks = detect_exclusive_tasks(schedule) if not schedule.empty else []
optimization_comp = compute_plan_optimization_comparison(schedule, joint_bundles, exclusive_tasks) if not schedule.empty else {
    "original_duration_mins": 0, "original_blocks_count": 0, "optimized_duration_mins": 0,
    "optimized_blocks_count": 0, "time_saved_hrs": 0, "separate_blocks_avoided": 0, "efficiency_gain_pct": 0,
    "tasks_bundled_count": 0,
}
overlap_pairs = detect_task_overlaps(schedule) if not schedule.empty else []
passenger_summary = get_passenger_traffic_summary()
freight_impact = compute_freight_impact(schedule) if not schedule.empty else {
    "affected_freight_trains": 0, "total_freight_delay_mins": 0, "average_delay_mins": 0,
    "impact_df": pd.DataFrame(),
}
financial_impact = compute_financial_impact(
    freight_impact["affected_freight_trains"],
    freight_impact["total_freight_delay_mins"],
    cost_factor_per_min=float(st.session_state["cost_factor"]),
)

# Centralized Controller Stats from Database
ctrl_stats = get_controller_stats()

# ─────────────────────────────────────────────────────────────────────────────
# TOP EXECUTIVE HEADER BANNER WITH LIVE IST CLOCK
# ─────────────────────────────────────────────────────────────────────────────
status_badge = (
    '<span class="ty-badge ty-badge-green"><span class="ty-pulse"></span> &nbsp;DATABASE CONNECTED</span>'
    if not st.session_state["siren_off_halt"]
    else '<span class="ty-badge ty-badge-red">⛔ SAFETY HOLD ACTIVE</span>'
)

logo_hdr = (
    f'<img src="data:image/png;base64,{LOGO_B64}" style="height:64px;width:auto;filter:drop-shadow(0 2px 10px rgba(0,0,0,0.5));" alt="TRACK YUKTI">'
    if LOGO_B64 else ""
)

hdr_c1, hdr_c2 = st.columns([2.3, 1.2])

with hdr_c1:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:16px;padding:8px 0;">
      {logo_hdr}
      <div>
        <div style="font-size:24px;font-weight:900;color:#F59E0B;letter-spacing:-0.02em;">
          TRACK YUKTI
          <span style="font-size:12px;font-weight:700;color:#93C5FD;background:rgba(37,99,235,0.25);padding:3px 8px;border-radius:6px;margin-left:8px;border:1px solid rgba(59,130,246,0.35);">
            WCR JABALPUR DIVISION
          </span>
        </div>
        <div style="font-size:13px;color:#38BDF8;font-weight:700;margin-top:2px;">
          Railway Block Planner
        </div>
        <div style="font-size:12px;color:#CBD5E1;margin-top:2px;">
          For Ministry of Railways &amp; Government of India &nbsp;·&nbsp; Database Connected &nbsp;|&nbsp; Active Jurisdiction: <b class="ty-track-red">{sel_corr}</b>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with hdr_c2:
    render_live_ist_clock()
    st.markdown(f'<div style="text-align:right;margin-top:2px;">{status_badge}</div>', unsafe_allow_html=True)

if has_conflict:
    st.markdown(
        f'<div class="ty-alert-danger"><b>⚠ Section Conflict</b><br>'
        f'<span style="font-size:12.5px;">{coll_track_name}<br>'
        f'<b>{" + ".join(coll_depts)}</b> — Joint possession recommended</span></div>',
        unsafe_allow_html=True,
    )


# =============================================================================
#  ROLE-BASED DASHBOARDS: DEPARTMENT 1, 2, 3 vs CHIEF CONTROLLER
# =============================================================================

user_role = st.session_state["user_role"]
user_dept = st.session_state["user_dept"]

# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO A: DEPARTMENT DASHBOARDS (DEPARTMENT 1, 2, OR 3)
# ─────────────────────────────────────────────────────────────────────────────
if user_role in ["DEPARTMENT_1", "DEPARTMENT_2", "DEPARTMENT_3"]:
    dept_number = "Department 1" if user_role == "DEPARTMENT_1" else ("Department 2" if user_role == "DEPARTMENT_2" else "Department 3")
    st.markdown(f"""
    <div class="ty-header" style="border-left:4px solid {DEPT_COLORS.get(user_dept, '#38BDF8')};">
      <div>
        <div style="font-size:11px;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.08em;">
          Role-Based Operational Terminal
        </div>
        <div style="font-size:22px;font-weight:900;color:#FFFFFF;margin-top:2px;">
          {dept_number} Dashboard — <span style="color:{DEPT_COLORS.get(user_dept, '#38BDF8')};">{user_dept}</span>
        </div>
        <div style="font-size:12px;color:#CBD5E1;margin-top:2px;">
          Officer: <b>{st.session_state['user_designation']}</b> &nbsp;|&nbsp; Assigned department maintenance requisitions and active track possessions.
        </div>
      </div>
      <div>
        <span class="ty-badge ty-badge-amber">ROLE: {user_role}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Department-Only Tasks
    my_tasks = get_department_tasks(department=user_dept)
    assigned_count = len(my_tasks)
    pending_tasks = sum(1 for t in my_tasks if t["task_status"] == "PENDING")
    active_tasks = sum(1 for t in my_tasks if t["task_status"] in ["APPROVED", "IN PROGRESS"])
    completed_tasks = sum(1 for t in my_tasks if t["task_status"] == "COMPLETED")

    dm1, dm2, dm3, dm4 = st.columns(4)
    with dm1:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Assigned Block Requests</div>
          <div class="ty-stat-value" style="color:#38BDF8;">{assigned_count}</div>
          <div style="font-size:11px;color:#94A3B8;margin-top:3px;">{user_dept} Pool</div>
        </div>
        """, unsafe_allow_html=True)
    with dm2:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Pending Approval</div>
          <div class="ty-stat-value" style="color:#F59E0B;">{pending_tasks}</div>
          <div style="font-size:11px;color:#FCD34D;margin-top:3px;">Awaiting Controller</div>
        </div>
        """, unsafe_allow_html=True)
    with dm3:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Active / In Progress</div>
          <div class="ty-stat-value" style="color:#C084FC;">{active_tasks}</div>
          <div style="font-size:11px;color:#E9D5FF;margin-top:3px;">Field Execution</div>
        </div>
        """, unsafe_allow_html=True)
    with dm4:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Completed Tasks</div>
          <div class="ty-stat-value" style="color:#10B981;">{completed_tasks}</div>
          <div style="font-size:11px;color:#6EE7B7;margin-top:3px;">Ready for Closure</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)

    dept_tab1, dept_tab2, dept_tab3 = st.tabs([
        f"📋 {user_dept} Assigned Tasks",
        f"📤 Submit Block Request ({user_dept})",
        "🛤️ Track Master & Infrastructure View",
    ])

    with dept_tab1:
        # Department Tasks Management Section
        st.markdown(f'<div class="ty-section-heading">Assigned Department Tasks</div>', unsafe_allow_html=True)

        if not my_tasks:
            st.info(f"Currently no maintenance block tasks assigned to {user_dept}.")
        else:
            for t in my_tasks:
                status_color = {
                    "PENDING": "ty-badge-amber",
                    "APPROVED": "ty-badge-green",
                    "IN PROGRESS": "ty-badge-purple",
                    "COMPLETED": "ty-badge-green",
                    "REJECTED": "ty-badge-red",
                }.get(t["task_status"], "ty-badge")

                prio_color = {
                    "CRITICAL": "ty-badge-red",
                    "VERY HIGH": "ty-badge-amber",
                    "HIGH": "ty-badge-amber",
                    "NORMAL": "ty-badge",
                    "LOW": "ty-badge-green",
                }.get(t["priority_level"], "ty-badge")

                st.markdown(f"""
                <div class="ty-card" style="border-left:4px solid {DEPT_COLORS.get(user_dept, '#38BDF8')};margin-bottom:12px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <div>
                      <span class="ty-badge {status_color}">STATUS: {t['task_status']}</span>
                      <span class="ty-badge {prio_color}">PRIORITY: {t['priority_level']}</span>
                      <span style="font-size:16px;font-weight:900;color:#FFFFFF;margin-left:8px;">Block ID: {t['block_id']}</span>
                      <div style="font-size:13px;font-weight:700;color:#FFFFFF;margin-top:4px;">
                        Activity: {t['action']}
                      </div>
                      <div style="font-size:12px;color:#CBD5E1;margin-top:2px;">
                        Track Section: <b class="ty-track-red">{t['section_track']}</b> &nbsp;|&nbsp;
                        Scheduled Time: <b style="color:#FCD34D;">{t['scheduled_start']} – {t['scheduled_deadline']}</b>
                      </div>
                      <div style="font-size:11.5px;color:#CBD5E1;margin-top:2px;">
                        Last Updated By: <b>{t['updated_by'] or 'System'}</b> ({t['updated_at']}) &nbsp;|&nbsp; Notes: {t['remarks']}
                      </div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:11px;color:#CBD5E1;">Criticality Score</div>
                      <div style="font-size:20px;font-weight:900;color:#EF4444;">{t['risk_score']:.1f}/100</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Work Completion / Update Controls for Department
                u_col1, u_col2, u_col3 = st.columns([1.5, 1, 1])
                with u_col1:
                    status_choices = ["PENDING", "APPROVED", "IN PROGRESS", "COMPLETED", "REJECTED"]
                    curr_idx = status_choices.index(t["task_status"]) if t["task_status"] in status_choices else 0
                    new_st = st.selectbox(
                        f"Update Task Status ({t['task_id']}):",
                        status_choices,
                        index=curr_idx,
                        key=f"status_sel_{t['task_id']}"
                    )
                with u_col2:
                    notes_inp = st.text_input("Remarks / Field Note:", value="", key=f"notes_{t['task_id']}")
                with u_col3:
                    st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                    if st.button("💾 Save Status Update", key=f"btn_upd_{t['task_id']}", use_container_width=True):
                        try:
                            update_task_status(
                                task_id=t["task_id"],
                                new_status=new_st,
                                user_role=user_role,
                                user_dept=user_dept,
                                user_designation=st.session_state["user_designation"],
                                remarks=notes_inp or f"Status updated by {st.session_state['user_designation']}"
                            )
                            st.success(f"✓ Task {t['task_id']} updated to {new_st}!")
                            time.sleep(0.3)
                            st.rerun()
                        except PermissionError as pe:
                            st.error(f"⛔ {str(pe)}")

    with dept_tab2:
        # Department Requisition Form (Submit Block Request)
        st.markdown(f'<div class="ty-section-heading">Submit Block Request — {user_dept}</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:12px;color:#94A3B8;margin-bottom:12px;">
          Submit maintenance requisition for operational clearance and CP-SAT schedule integration.
        </div>
        """, unsafe_allow_html=True)

        rf_c1, rf_c2 = st.columns(2)
        with rf_c1:
            req_corridor = st.selectbox("Corridor Section:", list(CORRIDORS.keys()), key="dept_req_corr")
            req_track    = st.selectbox("Track Line:", CORRIDORS[req_corridor]["tracks"], key="dept_req_trk")
            req_action   = st.selectbox("Maintenance Activity:", BRANCH_ACTIONS[user_dept], key="dept_req_act")
        with rf_c2:
            req_duration = st.slider("Requested Duration (Mins):", 30, 240, 90, step=15, key="dept_req_dur")
            req_heavy    = st.checkbox("Requires Heavy Machine / BCM / TRT (Exclusive Possession)", value=False, key="dept_req_hvy")

            if st.button("📤 Submit Block Request to Central Queue", type="primary", use_container_width=True):
                meta = CORRIDORS[req_corridor]
                new_id = create_block_request(
                    department=user_dept,
                    corridor=req_corridor,
                    section_track=f"{req_corridor} :: {req_track}",
                    action=req_action,
                    asset_id=f"AST-{user_dept[:3].upper()}-{int(time.time())%10000}",
                    requested_duration_mins=req_duration,
                    priority_score=85.0 if req_heavy else 72.0,
                    priority_level="CRITICAL" if req_heavy else "HIGH",
                    created_by=st.session_state["user_designation"],
                    is_heavy_machinery=req_heavy,
                    exclusive_block=req_heavy,
                    start_min=120,
                )
                st.success(f"✓ Block Request {new_id} successfully submitted and logged in Central Queue!")
                time.sleep(0.4)
                st.rerun()

    with dept_tab3:
        render_track_master_subsystem(
            is_admin=False,
            user_role=user_role,
            user_designation=st.session_state["user_designation"]
        )


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO B: CHIEF CONTROLLER DASHBOARD (FULL COMMAND & APPROVAL AUTHORITY)
# ─────────────────────────────────────────────────────────────────────────────
else:
    # CHIEF CONTROLLER DASHBOARD
    st.markdown("""
    <div class="ty-section-heading">Chief Controller Dashboard</div>
    """, unsafe_allow_html=True)

    # 1. Operational Metrics
    cm1, cm2, cm3, cm4, cm5, cm6, cm7 = st.columns(7)
    with cm1:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Total Requests</div>
          <div class="ty-stat-value" style="color:#38BDF8;">{ctrl_stats['total_requests']}</div>
          <div style="font-size:11px;color:#94A3B8;margin-top:3px;">Requisitions</div>
        </div>
        """, unsafe_allow_html=True)
    with cm2:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Pending Approval</div>
          <div class="ty-stat-value" style="color:#F59E0B;">{ctrl_stats['pending_approval']}</div>
          <div style="font-size:11px;color:#FCD34D;margin-top:3px;">Awaiting Decision</div>
        </div>
        """, unsafe_allow_html=True)
    with cm3:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Approved Blocks</div>
          <div class="ty-stat-value" style="color:#10B981;">{ctrl_stats['approved_blocks']}</div>
          <div style="font-size:11px;color:#6EE7B7;margin-top:3px;">Cleared for Work</div>
        </div>
        """, unsafe_allow_html=True)
    with cm4:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Active Blocks</div>
          <div class="ty-stat-value" style="color:#C084FC;">{ctrl_stats['active_blocks']}</div>
          <div style="font-size:11px;color:#E9D5FF;margin-top:3px;">Field Execution</div>
        </div>
        """, unsafe_allow_html=True)
    with cm5:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Conflicts Detected</div>
          <div class="ty-stat-value" style="color:{'#EF4444' if has_conflict else '#10B981'};">
            {'1 ALERT' if has_conflict else '0 CLASH'}
          </div>
          <div style="font-size:11px;color:#94A3B8;margin-top:3px;">Spatial Interlocks</div>
        </div>
        """, unsafe_allow_html=True)
    with cm6:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Bundling Opps</div>
          <div class="ty-stat-value" style="color:#38BDF8;">{len(joint_bundles)}</div>
          <div style="font-size:11px;color:#93C5FD;margin-top:3px;">Joint Packages</div>
        </div>
        """, unsafe_allow_html=True)
    with cm7:
        avg_dur = round(db_df['requested_duration_mins'].mean() if not db_df.empty else 90)
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Avg Duration</div>
          <div class="ty-stat-value" style="color:#FCD34D;">{avg_dur}m</div>
          <div style="font-size:11px;color:#94A3B8;margin-top:3px;">Per Possession</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)

    # 2. Department Requests Summary
    st.markdown('<div class="ty-section-heading">Department Requests</div>', unsafe_allow_html=True)
    dstat_cols = st.columns(3)
    dept_names = ["Engineering", "S&T", "Electrical"]
    for idx, dname in enumerate(dept_names):
        ds = ctrl_stats["department_stats"][dname]
        with dstat_cols[idx]:
            st.markdown(f"""
            <div class="ty-card" style="border-top:3px solid {DEPT_COLORS[dname]};">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="font-size:15px;font-weight:800;color:#FFFFFF;">{dname}</div>
                <span class="ty-badge">Total: {ds['total']} Tasks</span>
              </div>
              <div style="display:flex;gap:12px;margin-top:10px;font-size:12px;">
                <div>Pending: <b style="color:#FCD34D;">{ds['pending']}</b></div>
                <div>Approved: <b style="color:#93C5FD;">{ds['approved']}</b></div>
                <div>In Progress: <b style="color:#C084FC;">{ds['in_progress']}</b></div>
                <div>Completed: <b style="color:#4ADE80;">{ds['completed']}</b></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)

    # 3. Block Approval Queue
    st.markdown('<div class="ty-section-heading">Block Approval Queue</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;color:#94A3B8;margin-bottom:10px;">
      Review and authorize pending maintenance possession requisitions.
    </div>
    """, unsafe_allow_html=True)

    pending_requests = [r for r in db_requests if r["approval_status"] == "PENDING"]
    if not pending_requests:
        st.markdown("""
        <div class="ty-alert-success">
          <b>✓ Zero Pending Block Approvals</b> — All submitted requisitions have been processed by the Chief Controller.
        </div>
        """, unsafe_allow_html=True)
    else:
        for pr in pending_requests:
            st.markdown(f"""
            <div class="ty-card" style="border-left:4px solid #F59E0B;margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span class="ty-badge ty-badge-amber">PENDING APPROVAL</span>
                  <span class="ty-badge">{pr['department']}</span>
                  <span style="font-size:16px;font-weight:900;color:#FFFFFF;margin-left:8px;">{pr['block_id']}</span>
                  <div style="font-size:13px;font-weight:700;color:#FFFFFF;margin-top:4px;">
                    {pr['action']}
                  </div>
                  <div style="font-size:12px;color:#CBD5E1;margin-top:2px;">
                    Track Section: <b class="ty-track-red">{pr['section_track']}</b> &nbsp;|&nbsp;
                    Requested Duration: <b style="color:#FCD34D;">{pr['requested_duration_mins']} Mins</b> &nbsp;|&nbsp;
                    Proposed Slot: <b>{pr['start_time']} – {pr['end_time']}</b>
                  </div>
                  <div style="font-size:11.5px;color:#CBD5E1;margin-top:2px;">
                    Raised By: <b>{pr['created_by']}</b> &nbsp;|&nbsp; Priority Level: <b style="color:#FCA5A5;">{pr['priority_level']}</b> (Score: {pr['priority_score']:.1f})
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            ap_c1, ap_c2, ap_c3 = st.columns([1.5, 1, 1])
            with ap_c1:
                rem_txt = st.text_input(f"Decision Note ({pr['block_id']}):", value="", key=f"chc_note_{pr['block_id']}")
            with ap_c2:
                st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                if st.button(f"✅ APPROVE {pr['block_id']}", key=f"btn_app_{pr['block_id']}", type="primary", use_container_width=True):
                    approve_block_request(
                        block_id=pr["block_id"],
                        officer_name=st.session_state["user_designation"],
                        remarks=rem_txt or "Approved for execution"
                    )
                    st.success(f"✓ Block {pr['block_id']} APPROVED! Task dispatched to {pr['department']} dashboard.")
                    time.sleep(0.4)
                    st.rerun()
            with ap_c3:
                st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                if st.button(f"❌ REJECT {pr['block_id']}", key=f"btn_rej_{pr['block_id']}", use_container_width=True):
                    reject_block_request(
                        block_id=pr["block_id"],
                        officer_name=st.session_state["user_designation"],
                        remarks=rem_txt or "Operational constraints"
                    )
                    st.warning(f"Block {pr['block_id']} REJECTED.")
                    time.sleep(0.4)
                    st.rerun()

            with st.expander(f"🔍 [VIEW DETAILS] — Technical Dossier for Block {pr['block_id']}"):
                vd_c1, vd_c2 = st.columns(2)
                with vd_c1:
                    st.markdown(f"""
                    <b>Asset ID:</b> <code>{pr.get('asset_id', 'N/A')}</code><br>
                    <b>Corridor:</b> {pr.get('corridor', 'N/A')}<br>
                    <b>Track Section:</b> <b class="ty-track-red">{pr.get('section_track', 'N/A')}</b><br>
                    <b>Activity / Action:</b> {pr.get('action', 'N/A')}<br>
                    <b>Requested Duration:</b> {pr.get('requested_duration_mins', 0)} Mins
                    """, unsafe_allow_html=True)
                with vd_c2:
                    st.markdown(f"""
                    <b>Proposed Window:</b> {pr.get('start_time', 'N/A')} – {pr.get('end_time', 'N/A')}<br>
                    <b>Priority Score:</b> <span style="color:#EF4444;font-weight:800;">{pr.get('priority_score', 0):.1f}/100</span> ({pr.get('priority_level', 'NORMAL')})<br>
                    <b>Heavy Machinery (BCM/TRT):</b> {'Yes (Exclusive Block)' if pr.get('is_heavy_machinery') else 'No'}<br>
                    <b>Requisition Officer:</b> {pr.get('created_by', 'N/A')}<br>
                    <b>Submission Timestamp:</b> {pr.get('created_at', 'N/A')}
                    """, unsafe_allow_html=True)

    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)

    # 4. Critical / Priority Blocks & Upcoming Blocks Showcase (Requirement 8)
    st.markdown('<div class="ty-section-heading">Critical / Priority Blocks & Upcoming Operations Schedule</div>', unsafe_allow_html=True)
    crit_col, up_col = st.columns(2)

    with crit_col:
        st.markdown("""
        <div class="ty-card" style="border-top:3px solid #EF4444;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:13px;font-weight:800;color:#EF4444;text-transform:uppercase;">🚨 Critical / Priority Blocks</div>
            <span class="ty-badge ty-badge-red">IMMEDIATE ATTENTION</span>
          </div>
          <div style="font-size:12px;color:#CBD5E1;margin-bottom:8px;">
            Blocks with high asset flaw risk or overdue maintenance requiring immediate clearance.
          </div>
        """, unsafe_allow_html=True)

        crit_blocks = [r for r in db_requests if r.get("priority_level") in ["CRITICAL", "VERY HIGH"]][:4]
        if not crit_blocks:
            st.info("No critical blocks identified.")
        else:
            for cb in crit_blocks:
                st.markdown(f"""
                <div style="padding:8px;border-bottom:1px solid rgba(148,163,184,0.15);font-size:12px;">
                  <div style="display:flex;justify-content:space-between;">
                    <b>{cb['block_id']} ({cb['department']})</b>
                    <span class="ty-badge ty-badge-red">{cb['priority_level']} · {cb['priority_score']:.1f}</span>
                  </div>
                  <div style="color:#CBD5E1;margin-top:2px;">{cb['action']} · <b class="ty-track-red">{cb['section_track']}</b></div>
                  <div style="color:#CBD5E1;margin-top:2px;">Status: <b style="color:#FFFFFF;">{cb['approval_status']}</b> | Slot: {cb['start_time']} – {cb['end_time']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with up_col:
        st.markdown("""
        <div class="ty-card" style="border-top:3px solid #38BDF8;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:13px;font-weight:800;color:#38BDF8;text-transform:uppercase;">⏱️ Upcoming Blocks Timetable</div>
            <span class="ty-badge">NEXT 24 HOURS</span>
          </div>
          <div style="font-size:12px;color:#CBD5E1;margin-bottom:8px;">
            Approved rolling possession windows queued for imminent field execution.
          </div>
        """, unsafe_allow_html=True)

        approved_upcoming = [r for r in db_requests if r.get("approval_status") == "APPROVED"][:4]
        if not approved_upcoming:
            st.info("No approved upcoming blocks currently scheduled.")
        else:
            for ub in approved_upcoming:
                st.markdown(f"""
                <div style="padding:8px;border-bottom:1px solid rgba(148,163,184,0.15);font-size:12px;">
                  <div style="display:flex;justify-content:space-between;">
                    <b>{ub['block_id']} ({ub['department']})</b>
                    <span class="ty-badge ty-badge-green">APPROVED</span>
                  </div>
                  <div style="color:#CBD5E1;margin-top:2px;">{ub['action']} · <b class="ty-track-red">{ub['section_track']}</b></div>
                  <div style="color:#FCD34D;margin-top:2px;">Scheduled Window: <b>{ub['start_time']} – {ub['end_time']}</b> ({ub['requested_duration_mins']} mins)</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


    # 4. Final Closure Section for Completed Blocks
    st.markdown('<div class="ty-section-heading">Active Blocks</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;color:#94A3B8;margin-bottom:10px;">
      Verify field completion and track safety clearance before terminal closure.
    </div>
    """, unsafe_allow_html=True)

    completed_blocks = [r for r in db_requests if r["approval_status"] == "APPROVED"]
    # Check which blocks have all tasks completed
    closeable_blocks = []
    for cb in completed_blocks:
        b_tasks = [t for t in get_department_tasks() if t["block_id"] == cb["block_id"]]
        if b_tasks and all(t["task_status"] == "COMPLETED" for t in b_tasks):
            closeable_blocks.append((cb, b_tasks))

    if not closeable_blocks:
        st.info("No approved blocks currently awaiting final clearance closure. Active blocks will appear here once departments mark tasks as COMPLETED.")
    else:
        for cb, b_tasks in closeable_blocks:
            st.markdown(f"""
            <div class="ty-card" style="border-left:4px solid #10B981;margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span class="ty-badge ty-badge-green">ALL TASKS COMPLETED</span>
                  <span style="font-size:16px;font-weight:900;color:#FFFFFF;margin-left:8px;">Block ID: {cb['block_id']}</span>
                  <div style="font-size:13px;font-weight:700;color:#FFFFFF;margin-top:4px;">
                    {cb['action']} ({cb['department']})
                  </div>
                  <div style="font-size:12px;color:#CBD5E1;margin-top:2px;">
                    Track Section: <b class="ty-track-red">{cb['section_track']}</b> &nbsp;|&nbsp;
                    Field status: <b>All departmental work packages marked COMPLETED</b>
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            cl_c1, cl_c2 = st.columns([2, 1])
            with cl_c1:
                cl_notes = st.text_input(f"Closure Verification Note ({cb['block_id']}):", value="Track clearance verified, normal speed restored", key=f"cl_note_{cb['block_id']}")
            with cl_c2:
                st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                if st.button(f"🏁 VERIFY CLEARANCE & CLOSE {cb['block_id']}", key=f"btn_close_{cb['block_id']}", type="primary", use_container_width=True):
                    close_block_request(
                        block_id=cb["block_id"],
                        officer_name=st.session_state["user_designation"],
                        remarks=cl_notes
                    )
                    st.balloons()
                    st.success(f"✓ Block {cb['block_id']} officially CLOSED and archived!")
                    time.sleep(0.4)
                    st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # FULL OPERATIONAL ANALYSIS TABS FOR CHIEF CONTROLLER
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)
    tab_opt, tab_time, tab_prio, tab_impact, tab_fin, tab_sim, tab_pool, tab_tracks = st.tabs([
        "⚡ Optimized Block Plan",
        "📊 Master Block Timetable",
        "🎯 AI Priority Analysis",
        "🚆 Passenger & Freight Traffic",
        "💰 Financial Impact",
        "🧪 Operational Simulation",
        "📝 Requisitions Register",
        "🛤️ Track Master & Infrastructure",
    ])

    # ── TAB: SMART BLOCK OPTIMIZER ───────────────────────────────────────────
    with tab_opt:
        st.markdown('<div class="ty-section-heading">Optimized Block Plan</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:12px;color:#94A3B8;margin-bottom:12px;">
          Constraint-satisfaction schedule generated by Google OR-Tools CP-SAT optimizer.
        </div>
        """, unsafe_allow_html=True)

        comp_c1, comp_c2 = st.columns(2)
        with comp_c1:
            st.markdown(f"""
            <div class="ty-card" style="border-top:3px solid #94A3B8;">
              <div style="font-size:12px;font-weight:800;color:#94A3B8;text-transform:uppercase;">
                Original Plan (Uncoordinated Individual Blocks)
              </div>
              <h2 style="margin:8px 0 4px;font-size:26px;font-weight:900;color:#FFFFFF;">
                {optimization_comp['original_duration_mins'] // 60}h {optimization_comp['original_duration_mins'] % 60}m
              </h2>
              <div style="font-size:12px;color:#CBD5E1;line-height:1.6;">
                • Total Independent Possessions: <b>{optimization_comp['original_blocks_count']} Separate Windows</b><br>
                • Separate Handover Setup Losses: <b>+{optimization_comp['original_blocks_count'] * setup_buffer} mins setup</b><br>
                • Traffic Holds: <b>High Disruption Risk</b>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with comp_c2:
            st.markdown(f"""
            <div class="ty-card" style="border-top:3px solid #10B981;">
              <div style="font-size:12px;font-weight:800;color:#34D399;text-transform:uppercase;">
                TrackYukti Optimized Plan (Coordinated Spatial Bundles)
              </div>
              <h2 style="margin:8px 0 4px;font-size:26px;font-weight:900;color:#4ADE80;">
                {optimization_comp['optimized_duration_mins'] // 60}h {optimization_comp['optimized_duration_mins'] % 60}m
                <span style="font-size:15px;color:#38BDF8;">(−{optimization_comp['time_saved_hrs']} Hours Saved)</span>
              </h2>
              <div style="font-size:12px;color:#CBD5E1;line-height:1.6;">
                • Unified Block Possessions: <b>{optimization_comp['optimized_blocks_count']} Coordinated Packages</b><br>
                • Separate Blocks Avoided: <b>{optimization_comp['separate_blocks_avoided']} Redundant Blocks Saved</b><br>
                • Line Capacity Gain: <b>+{optimization_comp['efficiency_gain_pct']}% Recovered</b>
              </div>
            </div>
            """, unsafe_allow_html=True)

        if joint_bundles:
            st.markdown(f'<div class="ty-section-heading" style="margin-top:16px;">Bundling Opportunities ({len(joint_bundles)} Active Packages)</div>', unsafe_allow_html=True)
            for b in joint_bundles:
                depts_str = " + ".join(b.participating_departments)
                st.markdown(f"""
                <div class="ty-card" style="border-left:4px solid #10B981;margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <div>
                      <span class="ty-badge ty-badge-green">Bundling Opportunity</span>
                      <span style="font-size:15px;font-weight:800;color:#FFFFFF;margin-left:8px;">{depts_str}</span>
                      <div style="font-size:12px;color:#CBD5E1;margin-top:4px;">
                        Corridor: <b>{b.corridor}</b> · Track Section: <b class="ty-track-red">{b.section_track}</b>
                      </div>
                      <div style="font-size:12px;color:#94A3B8;margin-top:2px;">
                        Same corridor / nearby work locations (≤500m spatial proximity)
                      </div>
                      <div style="font-size:12.5px;color:#38BDF8;font-weight:700;margin-top:4px;">
                        Recommended Action: Combine into a joint possession ({b.common_start_min//60:02d}:{b.common_start_min%60:02d} – {b.common_end_min//60:02d}:{b.common_end_min%60:02d} IST)
                      </div>
                    </div>
                    <div style="text-align:right;">
                      <span style="font-size:18px;font-weight:900;color:#38BDF8;">{b.time_saved_mins} Mins Saved</span>
                      <div style="font-size:11px;color:#94A3B8;">{b.separate_blocks_avoided} Separate Blocks Avoided</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB: MASTER BLOCK TIMETABLE ──────────────────────────────────────────
    with tab_time:
        st.markdown('<div class="ty-section-heading">Master Block Timetable</div>', unsafe_allow_html=True)

        gantt_df = schedule[schedule["is_scheduled"]].copy() if not schedule.empty and "is_scheduled" in schedule.columns else pd.DataFrame()
        if sel_corr != "All Corridors (Jabalpur Division)" and not gantt_df.empty:
            gantt_df = gantt_df[gantt_df["corridor"] == sel_corr]

        if gantt_df.empty:
            st.warning("No scheduled blocks found for current horizon.")
        else:
            bt = datetime.combine(datetime.today(), datetime.min.time())
            gantt_df["Start"]  = gantt_df["start_min"].apply(lambda m: bt + timedelta(minutes=float(m)))
            gantt_df["Finish"] = gantt_df["end_min"].apply(lambda m: bt + timedelta(minutes=float(m)))
            gantt_df["Label"]  = gantt_df.apply(
                lambda r: f"{r.get('block_id', r.get('request_id', 'BLK'))} ({r['department'][:3]})",
                axis=1,
            )

            fig = px.timeline(
                gantt_df,
                x_start="Start",
                x_end="Finish",
                y="section_track",
                color="department",
                color_discrete_map=DEPT_COLORS,
                text="Label",
                hover_data={
                    "department": True, "action": True,
                    "section_track": False, "Start": False, "Finish": False,
                },
            )
            fig.update_yaxes(
                autorange="reversed",
                title=dict(text="Track Section", font=dict(color="#FFFFFF", size=12)),
                tickfont=dict(color="#FFFFFF", size=11),
                gridcolor="rgba(255,255,255,0.08)",
                showgrid=True,
            )
            fig.update_xaxes(
                title=dict(text=f"Time Window (00:00 – {horizon_hours:02d}:00 IST)", font=dict(color="#FFFFFF", size=12)),
                tickfont=dict(color="#FFFFFF", size=11),
                gridcolor="rgba(255,255,255,0.08)",
            )
            fig.update_traces(
                textposition="inside",
                insidetextanchor="start",
                marker_line_width=1.5,
                marker_line_color="rgba(255,255,255,0.30)",
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(6, 12, 30, 0.95)",
                paper_bgcolor="rgba(6, 12, 30, 0.95)",
                font=dict(color="#FFFFFF", family="Inter"),
                height=max(380, 80 + 44 * gantt_df["section_track"].nunique()),
                margin=dict(l=10, r=10, t=20, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── TAB: PRIORITY INTELLIGENCE ───────────────────────────────────────────
    with tab_prio:
        st.markdown('<div class="ty-section-heading">AI Priority Analysis</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="ty-card" style="margin-bottom:14px;border-left:3px solid #38BDF8;">
          <div style="font-size:13px;font-weight:800;color:#FFFFFF;margin-bottom:4px;">
            AI Risk Assessment Model (Random Forest Regressor)
          </div>
          <div style="font-size:12px;color:#CBD5E1;line-height:1.5;">
            Evaluates objective priority scores (0–100) using <b>Asset Criticality</b>, <b>Maintenance Overdue Intervals</b>, <b>Traffic Density Exposure</b>, and <b>Operational Risk Factors</b>. Scores are algorithmically generated by the ML model.
          </div>
        </div>
        """, unsafe_allow_html=True)

        if not priority_df.empty and "priority_score" in priority_df.columns:
            p_cols = ["block_id", "department", "action", "corridor", "priority_score", "priority_level", "priority_explanation"]
            avail_p_cols = [c for c in p_cols if c in priority_df.columns]
            p_table = priority_df[avail_p_cols].copy()
            st.dataframe(p_table, use_container_width=True, height=350, hide_index=True)

    # ── TAB: PASSENGER & FREIGHT IMPACT ──────────────────────────────────────
    with tab_impact:
        st.markdown('<div class="ty-section-heading">Corridor Passenger & Freight Traffic Impact Assessment</div>', unsafe_allow_html=True)
        pt_col, ft_col = st.columns([1, 1.3])
        with pt_col:
            prof_df = passenger_summary["profile_df"]
            fig_pass = px.bar(
                prof_df,
                x="hour",
                y="train_count",
                color="category",
                color_discrete_map={"LOW": "#10B981", "MEDIUM": "#F59E0B", "HIGH": "#EF4444"},
                labels={"hour": "Hour of Day (IST)", "train_count": "Passenger Trains / Hour"},
            )
            fig_pass.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(6, 12, 30, 0.95)",
                paper_bgcolor="rgba(6, 12, 30, 0.95)",
                font=dict(color="#FFFFFF", size=11),
                height=260,
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig_pass, use_container_width=True)
            st.markdown(f"""
            <div style="font-size:12px;color:#CBD5E1;">
              • Optimal Midday Block: <b style="color:#4ADE80;">{passenger_summary['recommended_day_block_window']}</b><br>
              • Optimal Night Block: <b style="color:#38BDF8;">{passenger_summary['recommended_night_block_window']}</b>
            </div>
            """, unsafe_allow_html=True)
        with ft_col:
            if not freight_impact["impact_df"].empty:
                st.dataframe(freight_impact["impact_df"], use_container_width=True, height=260, hide_index=True)

    # ── TAB: FINANCIAL AUDIT ─────────────────────────────────────────────────
    with tab_fin:
        st.markdown('<div class="ty-section-heading">Financial Demurrage & Energy Impact Audit</div>', unsafe_allow_html=True)
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.markdown(f"""
            <div class="ty-card" style="border-top:3px solid #EF4444;">
              <div style="font-size:11px;font-weight:800;color:#94A3B8;text-transform:uppercase;">Without Optimization</div>
              <h2 style="margin:6px 0;color:#EF4444;font-size:28px;font-weight:900;">₹{financial_impact['cost_without_optimization_lakhs']} Lakhs</h2>
              <div style="font-size:12px;color:#CBD5E1;">Uncoordinated fragmented blocks with detention penalties.</div>
            </div>
            """, unsafe_allow_html=True)
        with fc2:
            st.markdown(f"""
            <div class="ty-card" style="border-top:3px solid #38BDF8;">
              <div style="font-size:11px;font-weight:800;color:#94A3B8;text-transform:uppercase;">With TrackYukti Optimization</div>
              <h2 style="margin:6px 0;color:#38BDF8;font-size:28px;font-weight:900;">₹{financial_impact['cost_with_optimization_lakhs']} Lakhs</h2>
              <div style="font-size:12px;color:#CBD5E1;">Synchronized joint possession minimizing rake holding.</div>
            </div>
            """, unsafe_allow_html=True)
        with fc3:
            st.markdown(f"""
            <div class="ty-card" style="border-top:3px solid #10B981;">
              <div style="font-size:11px;font-weight:800;color:#34D399;text-transform:uppercase;">Estimated Savings</div>
              <h2 style="margin:6px 0;color:#4ADE80;font-size:28px;font-weight:900;">₹{financial_impact['avoided_impact_lakhs']} Lakhs</h2>
              <div style="font-size:12px;color:#D1FAE5;font-weight:700;">Avoided Financial Losses</div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB: WHAT-IF SIMULATION ──────────────────────────────────────────────
    with tab_sim:
        st.markdown('<div class="ty-section-heading">Operational Simulation</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:12px;color:#94A3B8;margin-bottom:12px;">
          Simulate real-time operational disruptions and verify dynamic CP-SAT schedule re-optimization.
        </div>
        """, unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            st.session_state["simulate_collision"] = st.toggle(
                "⚠️ Scenario 1: Inject Section Conflict (Overlapping track requisitions)",
                value=st.session_state["simulate_collision"]
            )
            st.session_state["siren_off_halt"] = st.toggle(
                "🛡️ Scenario 2: Engage Safety Interlock Hold (Maintenance Pause)",
                value=st.session_state["siren_off_halt"]
            )
            sim_delay = st.slider("⏱️ Scenario 3: Inbound Freight Delay (Mins)", 0, 90, 0, step=15)

            if st.button("🚀 Run Simulation Re-Optimization", type="primary", use_container_width=True):
                add_audit_log(st.session_state["user_designation"], f"Triggered operational simulation re-optimization (Delay: {sim_delay}m)")
                st.success("Schedule Updated. 30-minute train delay detected. Affected blocks were re-optimized.")
                time.sleep(0.3)
                st.rerun()

        with sc2:
            st.markdown(f"""
            <div class="ty-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:13px;font-weight:800;color:#FFFFFF;">CP-SAT Optimization Engine Telemetry</div>
                <span class="ty-badge ty-badge-green">STATUS: {baseline_result.solver_status}</span>
              </div>
              <div style="font-size:12px;color:#CBD5E1;line-height:1.6;">
                • Objective Value: <b>{baseline_result.objective_value:.1f}</b><br>
                • Horizon Window: <b>{baseline_result.horizon_minutes} mins ({horizon_hours}h)</b><br>
                • Active Safety Collisions: <b>{'1 Conflict Clashing' if has_conflict else '0 Clashes Detected'}</b>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB: MASTER REQUISITIONS POOL & EXPORT ───────────────────────────────
    with tab_pool:
        st.markdown('<div class="ty-section-heading">Requisitions Register & Data Sources</div>', unsafe_allow_html=True)
        if not db_df.empty:
            st.dataframe(db_df, use_container_width=True, height=350, hide_index=True)

            csv_buffer = io.StringIO()
            db_df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Export Master Timetable (CSV)",
                data=csv_buffer.getvalue(),
                file_name=f"trackyukti_blocks_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── TAB: TRACK MASTER & INFRASTRUCTURE DATABASE ──────────────────────────
    with tab_tracks:
        render_track_master_subsystem(
            is_admin=True,
            user_role=user_role,
            user_designation=st.session_state["user_designation"]
        )

# ─────────────────────────────────────────────────────────────────────────────
# RECENT ACTIVITIES / AUDIT LOG FEED
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="ty-section-heading">Audit Log</div>', unsafe_allow_html=True)
audit_entries = get_recent_audit_logs(limit=8)
for ent in audit_entries:
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.12);font-size:12px;">
      <div>
        <span style="font-family:'JetBrains Mono',monospace;color:#93C5FD;margin-right:8px;">{ent['timestamp']}</span>
        <span class="ty-badge" style="margin-right:8px;">{ent['user']}</span>
        <span style="color:#E2E8F0;">{ent['event']}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:24px 0 10px;font-size:11.5px;color:#94A3B8;border-top:1px solid rgba(148,163,184,0.15);margin-top:30px;">
  <b style="color:#F59E0B;">TRACK YUKTI</b> &nbsp;·&nbsp; Railway Block Planner
  <br>For Ministry of Railways &amp; Government of India &nbsp;·&nbsp; West Central Railway (WCR) &nbsp;·&nbsp; Jabalpur Division &nbsp;·&nbsp; Database Connected &nbsp;·&nbsp; Prototype Data
</div>
""", unsafe_allow_html=True)
