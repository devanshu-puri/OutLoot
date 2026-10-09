from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from server.domain.geo import haversine_m
from server.schemas import SampleItem
from server.settings import MovementConfig


@dataclass
class MovementState:
    last_lat: Optional[float] = None
    last_lon: Optional[float] = None
    last_t: Optional[float] = None
    last_accuracy_m: Optional[float] = None
    cycle_start_lat: Optional[float] = None
    cycle_start_lon: Optional[float] = None
    cycle_progress_s: float = 0.0
    distance_m: float = 0.0
    implausible_count: int = 0


@dataclass
class RejectedSample:
    index: int
    reason_code: str
    message: str


@dataclass
class EvaluatedSegment:
    sample: SampleItem
    dt_s: float
    distance_m: float
    speed_mps: float
    verdict: str  # "QUALIFYING" or "NON_QUALIFYING"
    reason_code: str


@dataclass
class MovementResult:
    accepted: List[SampleItem] = field(default_factory=list)
    rejected: List[RejectedSample] = field(default_factory=list)
    segments: List[EvaluatedSegment] = field(default_factory=list)
    qualifying_s: float = 0.0
    distance_m: float = 0.0
    displacement_from_cycle_start_m: float = 0.0
    flags: List[str] = field(default_factory=list)
    new_state: MovementState = field(default_factory=MovementState)


def evaluate_samples(
    current_state: MovementState,
    samples: List[SampleItem],
    cfg: MovementConfig,
    server_now: Optional[float] = None
) -> MovementResult:
    result = MovementResult(new_state=MovementState(
        last_lat=current_state.last_lat,
        last_lon=current_state.last_lon,
        last_t=current_state.last_t,
        last_accuracy_m=current_state.last_accuracy_m,
        cycle_start_lat=current_state.cycle_start_lat,
        cycle_start_lon=current_state.cycle_start_lon,
        cycle_progress_s=current_state.cycle_progress_s,
        distance_m=current_state.distance_m,
        implausible_count=current_state.implausible_count,
    ))

    # Sort samples by client timestamp if out of order
    for idx, sample in enumerate(samples):
        # 1. Check GPS accuracy
        if sample.accuracy_m > cfg.max_accuracy_m:
            result.rejected.append(RejectedSample(
                index=idx,
                reason_code="LOW_ACCURACY",
                message=f"GPS accuracy ({sample.accuracy_m:.1f}m) exceeds maximum allowable ({cfg.max_accuracy_m}m)"
            ))
            continue

        # 2. Check Clock Skew against server time
        if server_now is not None:
            skew = abs(server_now - sample.t)
            if skew > cfg.max_skew_s:
                result.rejected.append(RejectedSample(
                    index=idx,
                    reason_code="CLOCK_SKEW",
                    message=f"Client clock skew ({skew:.1f}s) exceeds allowable window ({cfg.max_skew_s}s)"
                ))
                continue

        # 3. Check Stale / Monotonic timestamp
        if result.new_state.last_t is not None and sample.t <= result.new_state.last_t:
            result.rejected.append(RejectedSample(
                index=idx,
                reason_code="STALE_SAMPLE",
                message=f"Sample timestamp {sample.t} is not monotonically increasing (last={result.new_state.last_t})"
            ))
            continue

        # First valid sample in session / cycle
        if result.new_state.last_lat is None or result.new_state.last_t is None:
            result.new_state.last_lat = sample.lat
            result.new_state.last_lon = sample.lon
            result.new_state.last_t = sample.t
            result.new_state.last_accuracy_m = sample.accuracy_m
            if result.new_state.cycle_start_lat is None:
                result.new_state.cycle_start_lat = sample.lat
                result.new_state.cycle_start_lon = sample.lon
            result.accepted.append(sample)
            result.segments.append(EvaluatedSegment(
                sample=sample,
                dt_s=0.0,
                distance_m=0.0,
                speed_mps=0.0,
                verdict="QUALIFYING",
                reason_code="OK"
            ))
            continue

        # Consecutive pair evaluation
        dt = sample.t - result.new_state.last_t
        d = haversine_m(result.new_state.last_lat, result.new_state.last_lon, sample.lat, sample.lon)
        v = d / dt if dt > 0 else 0.0

        # 4. Check Gap Too Large (no interpolation across big gaps)
        if dt > cfg.max_gap_s:
            result.rejected.append(RejectedSample(
                index=idx,
                reason_code="GAP_TOO_LARGE",
                message=f"Gap between samples ({dt:.1f}s) exceeds max threshold ({cfg.max_gap_s}s)"
            ))
            # Reset reference position without awarding movement
            result.new_state.last_lat = sample.lat
            result.new_state.last_lon = sample.lon
            result.new_state.last_t = sample.t
            result.new_state.last_accuracy_m = sample.accuracy_m
            result.segments.append(EvaluatedSegment(
                sample=sample,
                dt_s=dt,
                distance_m=d,
                speed_mps=v,
                verdict="NON_QUALIFYING",
                reason_code="GAP_TOO_LARGE"
            ))
            continue

        # 5. Check Implausible Speed (Teleport / GPS glitch)
        if v > cfg.impossible_speed_mps:
            result.new_state.implausible_count += 1
            if result.new_state.implausible_count >= 3:
                result.flags.append("IMPLAUSIBLE_BURST")
            result.rejected.append(RejectedSample(
                index=idx,
                reason_code="IMPLAUSIBLE_SPEED",
                message=f"Speed ({v:.1f} m/s) is physically implausible for pedestrian movement"
            ))
            result.segments.append(EvaluatedSegment(
                sample=sample,
                dt_s=dt,
                distance_m=d,
                speed_mps=v,
                verdict="NON_QUALIFYING",
                reason_code="IMPLAUSIBLE_SPEED"
            ))
            continue

        # 6. Check Vehicle Speed (e.g. car, motorbike, fast transit)
        if v > cfg.max_walk_speed_mps:
            result.rejected.append(RejectedSample(
                index=idx,
                reason_code="VEHICLE_SPEED",
                message=f"Speed ({v:.1f} m/s) exceeds maximum walking/jogging pace ({cfg.max_walk_speed_mps} m/s)"
            ))
            result.new_state.last_lat = sample.lat
            result.new_state.last_lon = sample.lon
            result.new_state.last_t = sample.t
            result.new_state.last_accuracy_m = sample.accuracy_m
            result.segments.append(EvaluatedSegment(
                sample=sample,
                dt_s=dt,
                distance_m=d,
                speed_mps=v,
                verdict="NON_QUALIFYING",
                reason_code="VEHICLE_SPEED"
            ))
            continue

        # 7. Check Stationary / Noise floor (standing still, sitting, birdwatching)
        if v < cfg.min_walk_speed_mps or d < cfg.noise_floor_m:
            # Stationary pauses the cycle timer, does NOT disqualify or advance progress
            result.new_state.last_lat = sample.lat
            result.new_state.last_lon = sample.lon
            result.new_state.last_t = sample.t
            result.new_state.last_accuracy_m = sample.accuracy_m
            result.accepted.append(sample)
            result.segments.append(EvaluatedSegment(
                sample=sample,
                dt_s=dt,
                distance_m=d,
                speed_mps=v,
                verdict="NON_QUALIFYING",
                reason_code="STATIONARY"
            ))
            continue

        # 8. Valid Qualifying Walk Segment
        result.qualifying_s += dt
        result.distance_m += d
        result.new_state.cycle_progress_s += dt
        result.new_state.distance_m += d
        result.new_state.last_lat = sample.lat
        result.new_state.last_lon = sample.lon
        result.new_state.last_t = sample.t
        result.new_state.last_accuracy_m = sample.accuracy_m
        result.new_state.implausible_count = 0
        result.accepted.append(sample)
        result.segments.append(EvaluatedSegment(
            sample=sample,
            dt_s=dt,
            distance_m=d,
            speed_mps=v,
            verdict="QUALIFYING",
            reason_code="OK"
        ))

    # Calculate net displacement from cycle start
    if result.new_state.cycle_start_lat is not None and result.new_state.last_lat is not None:
        result.displacement_from_cycle_start_m = haversine_m(
            result.new_state.cycle_start_lat,
            result.new_state.cycle_start_lon,
            result.new_state.last_lat,
            result.new_state.last_lon
        )

    return result
