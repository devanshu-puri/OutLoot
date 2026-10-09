import pytest
from server.domain.geo import haversine_m, destination_point, bearing_deg
from server.domain.movement import (
    MovementState,
    evaluate_samples,
    MovementResult
)
from server.schemas import SampleItem
from server.settings import MovementConfig


def test_geo_haversine_and_destination():
    lat1, lon1 = 13.0827, 80.2707  # Chennai
    # 100m north (bearing 0)
    lat2, lon2 = destination_point(lat1, lon1, 0.0, 100.0)
    dist = haversine_m(lat1, lon1, lat2, lon2)
    assert abs(dist - 100.0) < 0.5
    brg = bearing_deg(lat1, lon1, lat2, lon2)
    assert abs(brg - 0.0) < 1.0


def test_movement_walking_qualifies():
    cfg = MovementConfig()
    lat0, lon0 = 13.0827, 80.2707
    state = MovementState()

    # Create 5 samples, 5 seconds apart, walking at 1.4 m/s (7m per step)
    samples = []
    curr_lat, curr_lon = lat0, lon0
    t0 = 1000.0
    for i in range(6):
        if i > 0:
            curr_lat, curr_lon = destination_point(curr_lat, curr_lon, 90.0, 7.0)
        samples.append(SampleItem(
            t=t0 + i * 5.0,
            lat=curr_lat,
            lon=curr_lon,
            accuracy_m=5.0
        ))

    res = evaluate_samples(state, samples, cfg, server_now=1025.0)
    assert len(res.accepted) == 6
    assert len(res.rejected) == 0
    assert res.qualifying_s == 25.0  # 5 steps * 5s
    assert abs(res.distance_m - 35.0) < 1.0
    assert res.new_state.cycle_progress_s == 25.0


def test_movement_low_accuracy_rejected():
    cfg = MovementConfig(max_accuracy_m=30.0)
    state = MovementState(last_lat=13.0827, last_lon=80.2707, last_t=1000.0, last_accuracy_m=5.0)
    sample = SampleItem(t=1005.0, lat=13.0828, lon=80.2708, accuracy_m=45.0)

    res = evaluate_samples(state, [sample], cfg, server_now=1005.0)
    assert len(res.rejected) == 1
    assert res.rejected[0].reason_code == "LOW_ACCURACY"
    assert res.qualifying_s == 0.0


def test_movement_clock_skew_rejected():
    cfg = MovementConfig(max_skew_s=60.0)
    state = MovementState(last_lat=13.0827, last_lon=80.2707, last_t=1000.0)
    # Sample from 200s in the future
    sample = SampleItem(t=1200.0, lat=13.0828, lon=80.2708, accuracy_m=5.0)

    res = evaluate_samples(state, [sample], cfg, server_now=1000.0)
    assert len(res.rejected) == 1
    assert res.rejected[0].reason_code == "CLOCK_SKEW"


def test_movement_stale_monotonic_timestamp():
    cfg = MovementConfig()
    state = MovementState(last_lat=13.0827, last_lon=80.2707, last_t=1005.0)
    sample = SampleItem(t=1003.0, lat=13.0828, lon=80.2708, accuracy_m=5.0)

    res = evaluate_samples(state, [sample], cfg, server_now=1005.0)
    assert len(res.rejected) == 1
    assert res.rejected[0].reason_code == "STALE_SAMPLE"


def test_movement_gap_too_large():
    cfg = MovementConfig(max_gap_s=30.0)
    state = MovementState(last_lat=13.0827, last_lon=80.2707, last_t=1000.0)
    # Gap of 45s
    lat2, lon2 = destination_point(13.0827, 80.2707, 0.0, 50.0)
    sample = SampleItem(t=1045.0, lat=lat2, lon=lon2, accuracy_m=5.0)

    res = evaluate_samples(state, [sample], cfg, server_now=1045.0)
    assert len(res.rejected) == 1
    assert res.rejected[0].reason_code == "GAP_TOO_LARGE"
    assert res.qualifying_s == 0.0


def test_movement_implausible_speed():
    cfg = MovementConfig(impossible_speed_mps=12.0)
    state = MovementState(last_lat=13.0827, last_lon=80.2707, last_t=1000.0)
    # Teleport 200m in 5 seconds = 40 m/s
    lat2, lon2 = destination_point(13.0827, 80.2707, 0.0, 200.0)
    sample = SampleItem(t=1005.0, lat=lat2, lon=lon2, accuracy_m=5.0)

    res = evaluate_samples(state, [sample], cfg, server_now=1005.0)
    assert len(res.rejected) == 1
    assert res.rejected[0].reason_code == "IMPLAUSIBLE_SPEED"
    assert res.qualifying_s == 0.0


def test_movement_vehicle_speed():
    cfg = MovementConfig(max_walk_speed_mps=3.5, impossible_speed_mps=12.0)
    state = MovementState(last_lat=13.0827, last_lon=80.2707, last_t=1000.0)
    # 40m in 5s = 8 m/s (car / bus speed)
    lat2, lon2 = destination_point(13.0827, 80.2707, 0.0, 40.0)
    sample = SampleItem(t=1005.0, lat=lat2, lon=lon2, accuracy_m=5.0)

    res = evaluate_samples(state, [sample], cfg, server_now=1005.0)
    assert len(res.rejected) == 1
    assert res.rejected[0].reason_code == "VEHICLE_SPEED"
    assert res.qualifying_s == 0.0


def test_movement_stationary_pauses_progress():
    cfg = MovementConfig(min_walk_speed_mps=0.5, noise_floor_m=3.0)
    state = MovementState(last_lat=13.0827, last_lon=80.2707, last_t=1000.0, cycle_progress_s=15.0)
    # 1 meter in 5s = 0.2 m/s (< 0.5 m/s and < 3m noise floor)
    lat2, lon2 = destination_point(13.0827, 80.2707, 0.0, 1.0)
    sample = SampleItem(t=1005.0, lat=lat2, lon=lon2, accuracy_m=5.0)

    res = evaluate_samples(state, [sample], cfg, server_now=1005.0)
    # Accepted without error, but 0 qualifying progress added
    assert len(res.accepted) == 1
    assert len(res.rejected) == 0
    assert res.qualifying_s == 0.0
    assert res.new_state.cycle_progress_s == 15.0
