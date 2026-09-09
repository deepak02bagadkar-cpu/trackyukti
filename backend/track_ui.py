"""
backend/track_ui.py
-------------------
Interactive UI Components for Track Master & Infrastructure Database Subsystem.
West Central Railway (WCR) — Jabalpur Division.

Features:
- Track Search & Multi-Attribute Filters (Track ID, Section, Station, KM, Condition, Criticality, Block Status)
- Interactive Track Detail Dossier with dynamic health badge & overdue calculation
- Physical Condition & Flaw Register
- Defect Status Management & Action controls
- Track Assets & Train Traffic Exposure Relationships
- Active & Scheduled Rolling Blocks Linkage
- Track Maintenance History Timeline
- Track Criticality Administration (Admin controlled, read-only for departments)
- Strict CSV Data Import Validator with Detailed Error Reporting & Sample Template Download
- Full CSV Export
"""

import io
import time
import pandas as pd
import streamlit as st
from datetime import datetime, date

from backend.track_db import (
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


def render_track_master_subsystem(is_admin: bool = False, user_role: str = "", user_designation: str = ""):
    """
    Render complete Track Master & Infrastructure Database subsystem.
    
    Parameters:
    - is_admin: If True (Chief Controller), grants track criticality modification & CSV import privileges.
    - user_role: Current session user role.
    - user_designation: Current session officer designation.
    """
    # ── Top Banner & Data Source Badge ─────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:16px;">
      <div>
        <div style="font-size:18px;font-weight:900;color:#FFFFFF;letter-spacing:-0.01em;">
          🛤️ Permanent Way & Track Master Database
        </div>
        <div style="font-size:12.5px;color:#E2E8F0;margin-top:2px;">
          West Central Railway · Jabalpur Division · Unified Infrastructure Registry & Flaw Telemetry
        </div>
      </div>
      <div>
        <span class="ty-badge ty-badge-amber" style="padding:6px 14px;font-size:11.5px;font-weight:800;letter-spacing:0.04em;">
          📌 DATA SOURCE: PROTOTYPE SYNTHETIC DATASET (IR-WCR JBP SPECIFICATION)
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── High-Level Infrastructure Metric Tiles ────────────────────────────────
    all_tracks = get_all_tracks()
    all_defects = get_all_defects()

    total_tracks = len(all_tracks)
    critical_tracks = sum(1 for t in all_tracks if t.get("health_status") == "CRITICAL")
    overdue_tracks = sum(1 for t in all_tracks if t.get("overdue_days", 0) > 0)
    open_defects = sum(1 for d in all_defects if d.get("repair_status") != "RESOLVED")
    active_block_tracks = sum(1 for t in all_tracks if t.get("active_block_status") in ["ACTIVE_BLOCK", "SPEED_RESTRICTION"])

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Total Track Lines</div>
          <div class="ty-stat-value" style="color:#38BDF8;">{total_tracks}</div>
          <div style="font-size:11px;color:#CBD5E1;margin-top:3px;">Permanent Way Assets</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Critical Health Lines</div>
          <div class="ty-stat-value" style="color:{'#EF4444' if critical_tracks > 0 else '#10B981'};">{critical_tracks}</div>
          <div style="font-size:11px;color:#FCA5A5;margin-top:3px;">Immediate Safety Priority</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Maintenance Overdue</div>
          <div class="ty-stat-value" style="color:{'#F59E0B' if overdue_tracks > 0 else '#10B981'};">{overdue_tracks}</div>
          <div style="font-size:11px;color:#FCD34D;margin-top:3px;">Inspection Window Expired</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Active Track Flaws</div>
          <div class="ty-stat-value" style="color:#EF4444;">{open_defects}</div>
          <div style="font-size:11px;color:#CBD5E1;margin-top:3px;">USFD & Physical Defects</div>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        st.markdown(f"""
        <div class="ty-stat">
          <div class="ty-stat-label">Active Restrictions</div>
          <div class="ty-stat-value" style="color:#C084FC;">{active_block_tracks}</div>
          <div style="font-size:11px;color:#E9D5FF;margin-top:3px;">Possession / Caution Orders</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)

    # ── Track Search & Filtering System ───────────────────────────────────────
    st.markdown('<div class="ty-section-heading">🔍 Track Search & Corridor Filtering Engine</div>', unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns([1.5, 1, 1, 1])
    with fc1:
        search_kw = st.text_input(
            "Search Track ID / Station / Section:",
            placeholder="e.g. TRK-JBP, Katni, Sihora, Goods Loop...",
            key="trk_search_kw"
        )
    with fc2:
        sec_codes = ["ALL"] + sorted(list(set(t["section_code"] for t in all_tracks)))
        sel_sec = st.selectbox("Corridor Section Code:", sec_codes, key="trk_sel_sec")
    with fc3:
        crit_options = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
        sel_crit = st.selectbox("Track Criticality:", crit_options, key="trk_sel_crit")
    with fc4:
        cond_options = ["ALL", "GOOD", "FAIR", "DETERIORATED"]
        sel_cond = st.selectbox("Current Condition:", cond_options, key="trk_sel_cond")

    fc5, fc6 = st.columns(2)
    with fc5:
        stat_options = ["ALL", "NORMAL", "ACTIVE_BLOCK", "SPEED_RESTRICTION", "MAINTENANCE_SCHEDULED"]
        sel_block_stat = st.selectbox("Active Possession / Block Status:", stat_options, key="trk_sel_bstat")
    with fc6:
        km_slider = st.slider("Corridor KM Range Filter:", 0.0, 1400.0, (0.0, 1400.0), step=10.0, key="trk_km_slider")

    # Fetch filtered tracks
    filtered_tracks = get_all_tracks(
        search_query=search_kw,
        section_code=sel_sec,
        criticality=sel_crit,
        condition=sel_cond,
        block_status=sel_block_stat,
        km_min=km_slider[0],
        km_max=km_slider[1],
    )

    st.markdown(f'<div style="font-size:12.5px;color:#CBD5E1;margin-bottom:12px;">Displaying <b>{len(filtered_tracks)}</b> of <b>{len(all_tracks)}</b> track lines matching query parameters.</div>', unsafe_allow_html=True)

    if not filtered_tracks:
        st.warning("No track records match the selected filter criteria.")
        return

    # ── Interactive Track Selection ───────────────────────────────────────────
    track_options = {
        f"{t['track_id']} — {t['section_name']} ({t['track_type']}) [Health: {t['health_status']}]": t["track_id"]
        for t in filtered_tracks
    }
    sel_label = st.selectbox("Select Track Line for Technical Dossier:", list(track_options.keys()), key="trk_detail_selector")
    sel_track_id = track_options[sel_label]
    track_data = get_track_by_id(sel_track_id)
    cond_data = get_track_condition(sel_track_id) or {}
    defects_data = get_track_defects(sel_track_id)
    history_data = get_track_maintenance_history(sel_track_id)
    assets_data = get_track_assets(sel_track_id)
    trains_data = get_track_trains(sel_track_id)
    active_blocks = get_active_blocks_for_track(sel_track_id)

    # ── Detail View: Comprehensive Technical Dossier ──────────────────────────
    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ty-section-heading">Detailed Technical Dossier: <span class="ty-track-red" style="font-size:16px;">{track_data["track_id"]}</span></div>', unsafe_allow_html=True)

    # Dynamic Health & Overdue Banner
    health_status = track_data["health_status"]
    health_badge = track_data["health_badge"]
    health_desc = track_data["health_description"]
    overdue_days = track_data["overdue_days"]

    overdue_badge = (
        f'<span class="ty-badge ty-badge-red">⚠️ {overdue_days} DAYS MAINTENANCE OVERDUE</span>'
        if overdue_days > 0
        else '<span class="ty-badge ty-badge-green">✓ UP-TO-DATE (0 DAYS OVERDUE)</span>'
    )

    st.markdown(f"""
    <div class="ty-card" style="border-left:5px solid {'#EF4444' if health_status == 'CRITICAL' else ('#F59E0B' if health_status == 'ATTENTION REQUIRED' else '#10B981')};">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <div>
          <div style="font-size:11px;font-weight:800;color:#CBD5E1;text-transform:uppercase;letter-spacing:0.06em;">
            Dynamic Track Health & Safety Clearance Status
          </div>
          <div style="margin-top:6px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span class="ty-badge {health_badge}" style="font-size:13px;padding:4px 12px;">HEALTH: {health_status}</span>
            {overdue_badge}
            <span class="ty-badge">STATUS: {track_data['active_block_status']}</span>
            <span class="ty-badge">CRITICALITY: {track_data['track_criticality']}</span>
          </div>
          <div style="font-size:12.5px;color:#FFFFFF;margin-top:8px;">
            <b>Evaluation Rationale:</b> {health_desc}
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:11px;color:#CBD5E1;">Inspection Quality Score</div>
          <div style="font-size:24px;font-weight:900;color:{'#10B981' if cond_data.get('last_inspection_score', 80) >= 80 else ('#F59E0B' if cond_data.get('last_inspection_score', 80) >= 65 else '#EF4444')};">
            {cond_data.get('last_inspection_score', 80):.1f}/100
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 4-Column Technical Specification Grid
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.markdown(f"""
        <div class="ty-card">
          <div style="font-size:11px;font-weight:800;color:#CBD5E1;text-transform:uppercase;">Geographic Span</div>
          <div style="font-size:14px;font-weight:800;color:#FFFFFF;margin-top:4px;">{track_data['from_station']} ➔ {track_data['to_station']}</div>
          <div style="font-size:12px;color:#CBD5E1;margin-top:3px;">
            Corridor: <b>{track_data['section_name']}</b><br>
            Section Code: <b style="color:#FCD34D;">{track_data['section_code']}</b><br>
            Zone / Div: <b>{track_data['zone']} / {track_data['division']}</b>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with g2:
        st.markdown(f"""
        <div class="ty-card">
          <div style="font-size:11px;font-weight:800;color:#CBD5E1;text-transform:uppercase;">Track Line Parameters</div>
          <div style="font-size:14px;font-weight:800;color:#EF4444;margin-top:4px;">{track_data['track_type']}</div>
          <div style="font-size:12px;color:#CBD5E1;margin-top:3px;">
            Gauge: <b>{track_data['gauge']}</b><br>
            Traction: <b>{track_data['electrification']}</b><br>
            Lines Count: <b>{track_data['number_of_lines']} Track(s)</b>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with g3:
        st.markdown(f"""
        <div class="ty-card">
          <div style="font-size:11px;font-weight:800;color:#CBD5E1;text-transform:uppercase;">Length & Chainage</div>
          <div style="font-size:14px;font-weight:800;color:#38BDF8;margin-top:4px;">{track_data['track_length_km']:.1f} KM Span</div>
          <div style="font-size:12px;color:#CBD5E1;margin-top:3px;">
            Chainage: <b>KM {track_data['km_from']:.1f} to {track_data['km_to']:.1f}</b><br>
            Max Speed: <b style="color:#4ADE80;">{track_data['maximum_permissible_speed']} km/h</b><br>
            Line Capacity: <b>{track_data['line_capacity']:.1f}%</b>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with g4:
        st.markdown(f"""
        <div class="ty-card">
          <div style="font-size:11px;font-weight:800;color:#CBD5E1;text-transform:uppercase;">Maintenance Schedule</div>
          <div style="font-size:14px;font-weight:800;color:#FCD34D;margin-top:4px;">Next: {track_data['next_track_maintenance_date']}</div>
          <div style="font-size:12px;color:#CBD5E1;margin-top:3px;">
            Last Work: <b>{track_data['last_track_maintenance_date']}</b><br>
            Traffic Density: <b>{track_data['traffic_density']:.1f} GMT</b><br>
            Current Cond: <b style="color:{'#10B981' if track_data['current_condition']=='GOOD' else ('#F59E0B' if track_data['current_condition']=='FAIR' else '#EF4444')};">{track_data['current_condition']}</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Track Condition Component Parameters ───────────────────────────────────
    st.markdown('<div class="ty-section-heading" style="margin-top:10px;">🛠️ Permanent Way Condition Parameters & Engineering Inspection</div>', unsafe_allow_html=True)
    cp1, cp2 = st.columns(2)
    with cp1:
        st.markdown(f"""
        <div class="ty-card">
          <div style="font-size:13px;font-weight:800;color:#38BDF8;margin-bottom:6px;">Rails & Fastenings Condition</div>
          <div style="font-size:12.5px;color:#FFFFFF;"><b>Rail Profile:</b> {cond_data.get('rail_condition', 'Standard 60kg 90UTS')}</div>
          <div style="font-size:12.5px;color:#FFFFFF;margin-top:4px;"><b>Sleeper Assembly:</b> {cond_data.get('sleeper_condition', 'RT-2496 Monoblock PSC')}</div>
          <div style="font-size:12px;color:#CBD5E1;margin-top:8px;">
            Flaw Status: <b>{cond_data.get('track_defect_count', 0)} Active Flaws</b> ({cond_data.get('severe_defects_count', 0)} Severe IMR Flaws)
          </div>
        </div>
        """, unsafe_allow_html=True)
    with cp2:
        st.markdown(f"""
        <div class="ty-card">
          <div style="font-size:13px;font-weight:800;color:#38BDF8;margin-bottom:6px;">Ballast Cushion & Geometry</div>
          <div style="font-size:12.5px;color:#FFFFFF;"><b>Ballast Bed:</b> {cond_data.get('ballast_condition', 'Clean 300mm Cushion')}</div>
          <div style="font-size:12.5px;color:#FFFFFF;margin-top:4px;"><b>Geometry / TQI:</b> {cond_data.get('track_geometry_condition', 'Within Tolerances')}</div>
          <div style="font-size:12px;color:#CBD5E1;margin-top:8px;">
            <b>Required Resources:</b> {cond_data.get('required_maintenance_resources', 'Routine Track Gang')}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Track Defects Register ────────────────────────────────────────────────
    st.markdown(f'<div class="ty-section-heading" style="margin-top:10px;">⚠️ Active Track Defects & Flaw Register ({len(defects_data)} Records)</div>', unsafe_allow_html=True)
    if not defects_data:
        st.success("✓ Zero active defects or flaws reported for this track line. All parameters nominal.")
    else:
        for d in defects_data:
            d_sev_color = {
                "CRITICAL": "ty-badge-red",
                "MAJOR": "ty-badge-amber",
                "MINOR": "ty-badge",
            }.get(d.get("severity", "MINOR"), "ty-badge")

            d_stat_color = {
                "OPEN": "ty-badge-red",
                "SPEED_RESTRICTED": "ty-badge-amber",
                "IN_PROGRESS": "ty-badge-purple",
                "RESOLVED": "ty-badge-green",
            }.get(d.get("repair_status", "OPEN"), "ty-badge")

            st.markdown(f"""
            <div class="ty-card" style="border-left:4px solid {'#EF4444' if d['severity']=='CRITICAL' else '#F59E0B'};margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span class="ty-badge {d_sev_color}">{d['severity']}</span>
                  <span class="ty-badge {d_stat_color}">STATUS: {d['repair_status']}</span>
                  <span style="font-size:14px;font-weight:800;color:#FFFFFF;margin-left:6px;">{d['defect_id']} — {d['defect_type']}</span>
                  <div style="font-size:12.5px;color:#FFFFFF;margin-top:4px;">
                    Location: <b class="ty-track-red">{d['km_location']}</b> &nbsp;|&nbsp;
                    Detected Date: <b>{d['detected_date']}</b> &nbsp;|&nbsp;
                    Target Repair: <b style="color:#FCD34D;">{d['target_repair_date']}</b>
                  </div>
                  <div style="font-size:12px;color:#CBD5E1;margin-top:3px;">
                    Description: {d['defect_description']} &nbsp;|&nbsp; Notes: <i>{d.get('remarks') or 'None'}</i>
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Quick Defect Status Update
            df_col1, df_col2, df_col3 = st.columns([1.5, 1.5, 1])
            with df_col1:
                new_d_stat = st.selectbox(
                    f"Update Status ({d['defect_id']}):",
                    ["OPEN", "SPEED_RESTRICTED", "IN_PROGRESS", "RESOLVED"],
                    index=["OPEN", "SPEED_RESTRICTED", "IN_PROGRESS", "RESOLVED"].index(d["repair_status"]),
                    key=f"d_stat_sel_{d['defect_id']}"
                )
            with df_col2:
                d_rem = st.text_input(f"Action Remarks ({d['defect_id']}):", value="", key=f"d_rem_{d['defect_id']}")
            with df_col3:
                st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                if st.button(f"💾 Update {d['defect_id']}", key=f"btn_d_upd_{d['defect_id']}", use_container_width=True):
                    update_defect_status(
                        defect_id=d["defect_id"],
                        new_status=new_d_stat,
                        user_designation=user_designation,
                        remarks=d_rem or f"Status updated to {new_d_stat}"
                    )
                    st.success(f"✓ Defect {d['defect_id']} updated to {new_d_stat}!")
                    time.sleep(0.3)
                    st.rerun()

    # ── Relational Views: Assets & Train Traffic Exposure ──────────────────────
    st.markdown('<div class="ty-section-heading" style="margin-top:14px;">🔗 Relational Linkages: Track Assets & Train Schedules</div>', unsafe_allow_html=True)
    rel_col1, rel_col2 = st.columns(2)

    with rel_col1:
        st.markdown(f"""
        <div class="ty-card" style="border-top:3px solid #38BDF8;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:13px;font-weight:800;color:#38BDF8;text-transform:uppercase;">Installed Assets on Track</div>
            <span class="ty-badge">{len(assets_data)} Assets</span>
          </div>
        """, unsafe_allow_html=True)
        if not assets_data:
            st.info("No specific asset hardware registered on this track line.")
        else:
            for ast_item in assets_data:
                st.markdown(f"""
                <div style="padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.15);font-size:12px;">
                  <div style="display:flex;justify-content:space-between;">
                    <b>{ast_item['asset_id']} ({ast_item['department']})</b>
                    <span class="ty-badge {'ty-badge-green' if ast_item['status']=='OPERATIONAL' else 'ty-badge-amber'}">{ast_item['status']}</span>
                  </div>
                  <div style="color:#FFFFFF;margin-top:2px;">{ast_item['asset_name']}</div>
                  <div style="color:#CBD5E1;margin-top:1px;">Location: <b class="ty-track-red">{ast_item['km_location']}</b> | Installed: {ast_item['installation_date']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with rel_col2:
        st.markdown(f"""
        <div class="ty-card" style="border-top:3px solid #F59E0B;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:13px;font-weight:800;color:#FCD34D;text-transform:uppercase;">Scheduled Train Traffic Exposure</div>
            <span class="ty-badge">{len(trains_data)} Trains</span>
          </div>
        """, unsafe_allow_html=True)
        if not trains_data:
            st.info("No regular passenger or freight trains mapped directly to this line.")
        else:
            for tr_item in trains_data:
                st.markdown(f"""
                <div style="padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.15);font-size:12px;">
                  <div style="display:flex;justify-content:space-between;">
                    <b>{tr_item['train_id']} — {tr_item['train_name']}</b>
                    <span class="ty-badge {'ty-badge-purple' if 'SUPERFAST' in tr_item['train_type'] else 'ty-badge'}">{tr_item['priority_tier']}</span>
                  </div>
                  <div style="color:#CBD5E1;margin-top:2px;">Slot: <b style="color:#FCD34D;">{tr_item['scheduled_time_slot']}</b> | Speed: <b>{tr_item['speed_kmph']} km/h</b></div>
                  <div style="color:#94A3B8;margin-top:1px;">Category: {tr_item['train_type']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Maintenance History & Active Rolling Blocks ───────────────────────────
    st.markdown('<div class="ty-section-heading" style="margin-top:14px;">⏱️ Past Maintenance History & Active Possession Blocks</div>', unsafe_allow_html=True)
    mh_col1, mh_col2 = st.columns(2)

    with mh_col1:
        st.markdown(f"""
        <div class="ty-card" style="border-top:3px solid #10B981;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:13px;font-weight:800;color:#34D399;text-transform:uppercase;">Maintenance History Log</div>
            <span class="ty-badge ty-badge-green">{len(history_data)} Records</span>
          </div>
        """, unsafe_allow_html=True)
        if not history_data:
            st.info("No past maintenance records found for this track.")
        else:
            for h in history_data:
                st.markdown(f"""
                <div style="padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.15);font-size:12px;">
                  <div style="display:flex;justify-content:space-between;">
                    <b>{h['maintenance_id']} — {h['maintenance_type']}</b>
                    <span class="ty-badge">{h['maintenance_date']}</span>
                  </div>
                  <div style="color:#CBD5E1;margin-top:2px;">Duration: <b>{h['duration_hours']}h</b> | Dept: <b>{h['department']}</b></div>
                  <div style="color:#94A3B8;margin-top:1px;">Before: {h['condition_before']} ➔ After: <span style="color:#4ADE80;">{h['condition_after']}</span></div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with mh_col2:
        st.markdown(f"""
        <div class="ty-card" style="border-top:3px solid #C084FC;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:13px;font-weight:800;color:#C084FC;text-transform:uppercase;">Associated Block Possessions</div>
            <span class="ty-badge">{len(active_blocks)} Requests</span>
          </div>
        """, unsafe_allow_html=True)
        if not active_blocks:
            st.info("No active or queued block requisitions currently targeting this track.")
        else:
            for ab in active_blocks[:4]:
                st.markdown(f"""
                <div style="padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.15);font-size:12px;">
                  <div style="display:flex;justify-content:space-between;">
                    <b>{ab['block_id']} ({ab['department']})</b>
                    <span class="ty-badge {'ty-badge-green' if ab['approval_status']=='APPROVED' else 'ty-badge-amber'}">{ab['approval_status']}</span>
                  </div>
                  <div style="color:#FFFFFF;margin-top:2px;">{ab['action']}</div>
                  <div style="color:#CBD5E1;margin-top:1px;">Duration: <b>{ab['requested_duration_mins']} mins</b> | Slot: {ab.get('start_time', 'TBD')} – {ab.get('end_time', 'TBD')}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Track Criticality Control (Chief Controller / Admin Restricted) ───────
    st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ty-section-heading">🛡️ Track Criticality Control & Governance</div>', unsafe_allow_html=True)

    if is_admin:
        st.markdown("""
        <div style="font-size:12.5px;color:#CBD5E1;margin-bottom:8px;">
          <i>Track Criticality defines optimizer scheduling weights and safety priority. As Chief Controller / Admin (Track Master Authority), you can update the criticality level below.</i>
        </div>
        """, unsafe_allow_html=True)

        cr_c1, cr_c2, cr_c3 = st.columns([1.5, 1.5, 1])
        with cr_c1:
            crit_choices = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            curr_crit_idx = crit_choices.index(track_data["track_criticality"]) if track_data["track_criticality"] in crit_choices else 1
            new_crit = st.selectbox(f"Set Track Criticality for {track_data['track_id']}:", crit_choices, index=curr_crit_idx, key="admin_crit_sel")
        with cr_c2:
            crit_remarks = st.text_input("Authorization Reason / Remarks:", value="", key="admin_crit_rem")
        with cr_c3:
            st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
            if st.button("💾 Save Criticality", type="primary", use_container_width=True, key="btn_save_crit"):
                try:
                    update_track_criticality(
                        track_id=track_data["track_id"],
                        new_criticality=new_crit,
                        user_role=user_role,
                        user_designation=user_designation,
                        remarks=crit_remarks or "Criticality updated via Track Master console"
                    )
                    st.success(f"✓ Track {track_data['track_id']} criticality successfully updated to {new_crit}!")
                    time.sleep(0.3)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.markdown(f"""
        <div class="ty-card" style="border-left:4px solid #94A3B8;">
          <div style="font-size:12.5px;color:#CBD5E1;">
            🔒 <b>Track Criticality: {track_data['track_criticality']} (READ-ONLY)</b><br>
            Under Indian Railways standard operating procedure, Track Criticality can only be modified by the Chief Controller / Track Master Administrator. Regular department workstations have read-only visibility.
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── CSV Data Import & Export Subsystem (Chief Controller / Admin) ─────────
    if is_admin:
        st.markdown('<div class="ty-divider"></div>', unsafe_allow_html=True)
        with st.expander("📥 Track Master CSV Data Import & Export (Strict Validation Pipeline)"):
            st.markdown("""
            <div style="font-size:12.5px;color:#CBD5E1;margin-bottom:12px;">
              Upload bulk Track Master CSV files. The validation engine performs strict verification:
              <br>• Missing required fields & headers
              <br>• Duplicate <code>track_id</code> detection
              <br>• Calendar date validation (<code>YYYY-MM-DD</code>)
              <br>• Numeric sanity checks (Speed 20–200 km/h, KM spans, positive lengths)
              <br>• Strict Enum validation (Criticality, Condition, Active Block Status)
            </div>
            """, unsafe_allow_html=True)

            up_col1, up_col2 = st.columns([2, 1])

            with up_col1:
                uploaded_csv = st.file_uploader("Upload Track Master CSV File:", type=["csv"], key="track_csv_uploader")
                if uploaded_csv is not None:
                    try:
                        csv_df = pd.read_csv(uploaded_csv)
                        val_res = validate_and_import_track_csv(csv_df, user_designation=user_designation)

                        # Display validation report
                        st.markdown(f"""
                        <div class="ty-card" style="margin-top:10px;">
                          <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div style="font-size:14px;font-weight:800;color:#FFFFFF;">CSV Validation Report</div>
                            <div>
                              <span class="ty-badge ty-badge-green">Valid: {val_res['valid_count']}</span>
                              <span class="ty-badge {'ty-badge-red' if val_res['rejected_count']>0 else ''}">Rejected: {val_res['rejected_count']}</span>
                            </div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        if val_res["rejected_count"] > 0:
                            st.markdown('<div style="font-size:12px;color:#FCA5A5;font-weight:700;margin:6px 0;">Validation Errors Detected:</div>', unsafe_allow_html=True)
                            for rej in val_res["rejected_records"][:10]:
                                st.error(f"Row {rej['row_index']} ({rej['track_id']}): {'; '.join(rej['errors'])}")

                        if val_res["valid_count"] > 0:
                            st.markdown(f'<div style="font-size:12.5px;color:#4ADE80;margin:8px 0;">✓ <b>{val_res["valid_count"]} valid records ready to commit.</b></div>', unsafe_allow_html=True)
                            if st.button("🚀 Commit Valid Records to SQLite Database", type="primary", key="btn_commit_csv"):
                                committed = commit_valid_track_records(val_res["valid_records"], user_designation)
                                st.balloons()
                                st.success(f"✓ Successfully imported and updated {committed} Track Master records!")
                                time.sleep(0.4)
                                st.rerun()

                    except Exception as ex:
                        st.error(f"Failed to read CSV: {ex}")

            with up_col2:
                sample_csv_data = generate_sample_track_csv()
                st.download_button(
                    label="📄 Download Sample CSV Template",
                    data=sample_csv_data,
                    file_name="track_master_template.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_tmpl"
                )

                # Export full Track Master dataset
                full_tracks_df = pd.DataFrame(all_tracks)
                full_csv_buf = io.StringIO()
                full_tracks_df.to_csv(full_csv_buf, index=False)
                st.download_button(
                    label="📤 Export Complete Track Master (CSV)",
                    data=full_csv_buf.getvalue(),
                    file_name=f"track_master_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_full_tracks"
                )
