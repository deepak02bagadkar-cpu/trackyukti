"""
Test Track DB Subsystem
"""
import sys
import io
import pandas as pd
from pathlib import Path

# Add project root to sys.path
BASE = Path(__file__).parent / "TrackYukti-Railway-Block-Planner"
sys.path.insert(0, str(BASE))

from backend.track_db import (
    get_all_tracks, get_track_by_id, get_track_condition, get_track_defects,
    get_track_maintenance_history, get_track_assets, get_track_trains,
    validate_and_import_track_csv, generate_sample_track_csv,
    update_track_criticality, update_defect_status
)

def test_track_subsystem():
    tracks = get_all_tracks()
    print(f"Total seeded tracks: {len(tracks)}")
    assert len(tracks) >= 7, f"Expected at least 7 tracks, found {len(tracks)}"

    for t in tracks:
        print(f"Track: {t['track_id']} | Sec: {t['section_code']} | Cond: {t['current_condition']} | Health: {t['health_status']} | Overdue: {t['overdue_days']} days")

    t0 = tracks[0]["track_id"]
    cond = get_track_condition(t0)
    assert cond is not None, "Condition must not be None"
    print(f"Condition for {t0}: {cond['rail_condition'][:40]}...")

    defects = get_track_defects(t0)
    print(f"Defects for {t0}: {len(defects)}")

    assets = get_track_assets(t0)
    print(f"Assets for {t0}: {len(assets)}")

    trains = get_track_trains(t0)
    print(f"Trains for {t0}: {len(trains)}")

    # Test CSV validation
    sample_csv = generate_sample_track_csv()
    df = pd.read_csv(io.StringIO(sample_csv))
    res = validate_and_import_track_csv(df)
    print(f"CSV Validation Result: Total={res['total_rows']}, Valid={res['valid_count']}, Rejected={res['rejected_count']}")
    assert res["valid_count"] == 2, f"Expected 2 valid records, got {res['valid_count']}"

    # Test Permission on Criticality update (Regular dept vs Chief Controller)
    try:
        update_track_criticality(t0, "CRITICAL", user_role="DEPARTMENT_1", user_designation="DEN")
        assert False, "Department should not be able to update track criticality"
    except PermissionError as e:
        print(f"Security check passed: {e}")

    # Chief controller update
    ok = update_track_criticality(t0, "HIGH", user_role="CHIEF_CONTROLLER", user_designation="Chief Controller", remarks="Safety review")
    assert ok is True
    print("Chief Controller criticality update passed!")

    print("ALL TRACK SUBSYSTEM CHECKS PASSED!")

if __name__ == "__main__":
    test_track_subsystem()
