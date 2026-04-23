from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
import os
from typing import Any


def read_audit_records(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []

    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            candidate = line.strip()
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)

    rank = (len(ordered) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[lower], 3)

    lower_value = ordered[lower]
    upper_value = ordered[upper]
    interpolated = lower_value + (upper_value - lower_value) * (rank - lower)
    return round(interpolated, 3)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def build_release_dashboard(records: list[dict[str, Any]]) -> dict[str, Any]:
    action_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    performance_counts: Counter[str] = Counter()
    sigma_band_counts: Counter[str] = Counter()
    control_state_counts: Counter[str] = Counter()
    ctq_pass_counts: Counter[str] = Counter()
    ctq_total_counts: Counter[str] = Counter()
    loadrunner_pass_count = 0
    total_blocked = 0
    total_ok = 0
    all_latencies: list[float] = []
    all_dpmo: list[float] = []
    action_latencies: dict[str, list[float]] = defaultdict(list)
    action_loadrunner_pass: Counter[str] = Counter()
    action_loadrunner_total: Counter[str] = Counter()

    for record in records:
        action = str(record.get("action") or "unknown")
        action_counts[action] += 1

        status = str(record.get("status") or "unknown")
        status_counts[status] += 1
        if status == "ok":
            total_ok += 1
        if record.get("blocked") is True or status == "blocked":
            total_blocked += 1

        latency = record.get("latency_ms")
        if isinstance(latency, (int, float)):
            numeric_latency = float(latency)
            all_latencies.append(numeric_latency)
            action_latencies[action].append(numeric_latency)

        performance_status = record.get("performance_status")
        if isinstance(performance_status, str):
            performance_counts[performance_status] += 1

        ctq_metrics = record.get("ctq_metrics")
        if isinstance(ctq_metrics, dict):
            for metric_name, metric_status in ctq_metrics.items():
                ctq_total_counts[str(metric_name)] += 1
                if metric_status == "pass" or metric_status == "within_control":
                    ctq_pass_counts[str(metric_name)] += 1

        six_sigma = record.get("six_sigma")
        if isinstance(six_sigma, dict):
            sigma_band = six_sigma.get("sigma_band")
            if isinstance(sigma_band, str):
                sigma_band_counts[sigma_band] += 1
            control_state = six_sigma.get("control_state")
            if isinstance(control_state, str):
                control_state_counts[control_state] += 1
            dpmo = six_sigma.get("dpmo")
            if isinstance(dpmo, (int, float)):
                all_dpmo.append(float(dpmo))

        loadrunner = record.get("loadrunner")
        if isinstance(loadrunner, dict):
            action_loadrunner_total[action] += 1
            if loadrunner.get("passed") is True:
                loadrunner_pass_count += 1
                action_loadrunner_pass[action] += 1

    action_summary: dict[str, dict[str, Any]] = {}
    for action, count in sorted(action_counts.items()):
        latencies = action_latencies[action]
        action_summary[action] = {
            "requests": count,
            "avg_latency_ms": _average(latencies),
            "p95_latency_ms": _percentile(latencies, 0.95),
            "loadrunner_pass_rate": round(
                action_loadrunner_pass[action] / action_loadrunner_total[action],
                3,
            ) if action_loadrunner_total[action] else 0.0,
        }

    ctq_summary: dict[str, dict[str, Any]] = {}
    for metric_name, total in sorted(ctq_total_counts.items()):
        ctq_summary[metric_name] = {
            "pass_count": ctq_pass_counts[metric_name],
            "total": total,
            "pass_rate": round(ctq_pass_counts[metric_name] / total, 3) if total else 0.0,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_requests": len(records),
            "ok_requests": total_ok,
            "blocked_requests": total_blocked,
            "unique_actions": len(action_counts),
        },
        "actions": action_summary,
        "status_counts": dict(status_counts),
        "performance": {
            "avg_latency_ms": _average(all_latencies),
            "p95_latency_ms": _percentile(all_latencies, 0.95),
            "performance_status_counts": dict(performance_counts),
            "loadrunner_pass_rate": round(loadrunner_pass_count / len(records), 3) if records else 0.0,
        },
        "quality": {
            "ctq_metrics": ctq_summary,
            "avg_dpmo": _average(all_dpmo),
            "sigma_band_counts": dict(sigma_band_counts),
            "control_state_counts": dict(control_state_counts),
        },
    }


def build_release_dashboard_from_path(path: str) -> dict[str, Any]:
    records = read_audit_records(path)
    dashboard = build_release_dashboard(records)
    dashboard["audit_log_path"] = path
    return dashboard