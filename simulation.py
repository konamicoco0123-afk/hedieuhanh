from collections import deque
from typing import Dict, List, Optional
from algorithms import Patient, get_effective_priority, recalc_effective_priorities


def make_sim_state(patients: List[Patient], algorithm: str, time_quantum: int = 2, enable_aging: bool = False, aging_interval: int = 3, aging_step: int = 1) -> Dict:
    sim_patients = [Patient(id=p.id, arrival_time=p.arrival_time, burst_time=p.burst_time, priority=p.priority, disease=p.disease) for p in patients]
    future = deque(sorted(sim_patients, key=lambda p: p.arrival_time))
    return {
        "current_time": 0,
        "future": future,
        "ready": [],
        "waiting_io": [],
        "running": None,
        "completed": [],
        "schedule": [],
        "algorithm": algorithm,
        "time_quantum": time_quantum,
        "rr_slice_remaining": time_quantum,
        "running_segment_start": None,
        "enable_aging": enable_aging,
        "aging_interval": aging_interval,
        "aging_step": aging_step,
        "play": False,
        "done": False,
        "speed_factor": 1.0,
        "last_changes": [],
    }


def step_sim_state(sim: Dict) -> Dict:
    """Advance sim state by one time unit. Returns sim dict modified in-place."""
    if sim.get("done"):
        return sim
    t = sim["current_time"]
    sim["last_changes"] = []

    def process_waiting_io() -> None:
        """Cập nhật thời gian chờ I/O cho bệnh nhân đang WAITING."""
        completed_io = []
        for p in list(sim["waiting_io"]):
            p.io_time_remaining -= 1
            if p.io_time_remaining <= 0:
                if p.remaining_time == 0:
                    p.state = "TERMINATED"
                    p.completion_time = sim["current_time"]
                    p.turnaround_time = p.completion_time - p.arrival_time
                    p.waiting_time = p.turnaround_time - p.burst_time
                    sim["completed"].append(p)
                else:
                    p.state = "READY"
                    p.waiting_start_time = sim["current_time"]
                    sim["ready"].append(p)
                completed_io.append(p)
        for p in completed_io:
            sim["waiting_io"].remove(p)

    process_waiting_io()

    # move arrivals
    while sim["future"] and sim["future"][0].arrival_time <= t:
        p = sim["future"].popleft()
        p.state = "READY"
        if p.waiting_start_time <= 0:
            p.waiting_start_time = t
        sim["ready"].append(p)

    # aging updates
    if sim.get("enable_aging"):
        for p in sim["ready"]:
            prev = getattr(p, "effective_priority", p.priority)
            new = get_effective_priority(p, t, sim.get("enable_aging", False), sim.get("aging_interval", 3), sim.get("aging_step", 1))
            if new != prev:
                sim.setdefault("last_changes", []).append(f"BN{p.id}: ưu tiên {prev} -> {new}")
        # also check the running process for effective-priority changes
        running_proc = sim.get("running")
        if running_proc is not None:
            prev = getattr(running_proc, "effective_priority", running_proc.priority)
            new = get_effective_priority(running_proc, t, sim.get("enable_aging", False), sim.get("aging_interval", 3), sim.get("aging_step", 1))
            if new != prev:
                sim.setdefault("last_changes", []).append(f"BN{running_proc.id}: ưu tiên {prev} -> {new}")

    # If aging produced effective-priority changes this tick, split the current running
    # segment at the current time so the schedule records the boundary (batch algorithm
    # also slices runs at aging-change times). This ensures step-mode produces the
    # same per-unit segments when aging_interval is small.
    if sim.get("last_changes") and sim.get("running") is not None:
        start = sim.get("running_segment_start")
        if start is not None and t - start > 0:
            sim["schedule"].append({"patient_id": sim["running"].id, "start": start, "duration": t - start})
        # reopen running segment at current time
        sim["running_segment_start"] = t

    alg = sim.get("algorithm")

    # pickers
    def pick_fcfs():
        sim["ready"].sort(key=lambda x: (x.arrival_time, x.id))
        return sim["ready"].pop(0) if sim["ready"] else None

    def pick_sjf():
        sim["ready"].sort(key=lambda x: (x.burst_time, x.arrival_time, x.id))
        return sim["ready"].pop(0) if sim["ready"] else None

    def pick_pr_np():
        sim["ready"].sort(key=lambda x: (x.effective_priority, x.arrival_time, x.id))
        return sim["ready"].pop(0) if sim["ready"] else None

    def pick_pr_p_candidate():
        sim["ready"].sort(key=lambda x: (x.effective_priority, x.arrival_time, x.id))
        return sim["ready"][0] if sim["ready"] else None

    def pick_rr():
        return sim["ready"].pop(0) if sim["ready"] else None

    running = sim.get("running")

    # preemptive priority handling
    if alg == "Priority (Preemptive)":
        if running is None:
            cand = pick_pr_p_candidate()
            if cand:
                sim["ready"].remove(cand)
                cand.state = "RUNNING"
                sim["running"] = cand
                sim["running_segment_start"] = t
                if cand.start_time == 0 and cand.remaining_time == cand.burst_time:
                    cand.start_time = t
        else:
            # update effective priorities
            for p in sim["ready"]:
                get_effective_priority(p, t, sim.get("enable_aging", False), sim.get("aging_interval", 3), sim.get("aging_step", 1))
            get_effective_priority(running, t, sim.get("enable_aging", False), sim.get("aging_interval", 3), sim.get("aging_step", 1))
            if sim["ready"]:
                best = min(sim["ready"], key=lambda x: (x.effective_priority, x.arrival_time, x.id))
                if best.effective_priority < running.effective_priority:
                    # preempt
                    # close current segment
                    end = t
                    start = sim.get("running_segment_start")
                    if start is not None and end - start > 0:
                        sim["schedule"].append({"patient_id": running.id, "start": start, "duration": end - start})
                    running.state = "READY"
                    running.waiting_start_time = t
                    sim["ready"].append(running)
                    sim["ready"].remove(best)
                    best.state = "RUNNING"
                    sim["running"] = best
                    sim["running_segment_start"] = t

    # if no running, pick based on algorithm
    if sim.get("running") is None:
        if alg == "FCFS":
            next_p = pick_fcfs()
            if next_p:
                if next_p.remaining_time == 0 and next_p.has_been_to_io:
                    next_p.completion_time = t
                    next_p.turnaround_time = next_p.completion_time - next_p.arrival_time
                    next_p.waiting_time = next_p.turnaround_time - next_p.burst_time
                    next_p.state = "TERMINATED"
                    sim["completed"].append(next_p)
                else:
                    next_p.state = "RUNNING"
                    sim["running"] = next_p
                    sim["running_segment_start"] = t
                    if next_p.start_time == 0 and next_p.remaining_time == next_p.burst_time:
                        next_p.start_time = t
        elif alg == "SJF":
            next_p = pick_sjf()
            if next_p:
                next_p.state = "RUNNING"
                sim["running"] = next_p
                sim["running_segment_start"] = t
                if next_p.start_time == 0 and next_p.remaining_time == next_p.burst_time:
                    next_p.start_time = t
        elif alg == "Priority (Non-preemptive)":
            next_p = pick_pr_np()
            if next_p:
                next_p.state = "RUNNING"
                sim["running"] = next_p
                sim["running_segment_start"] = t
                if next_p.start_time == 0 and next_p.remaining_time == next_p.burst_time:
                    next_p.start_time = t
        elif alg == "Round Robin":
            next_p = pick_rr()
            if next_p:
                next_p.state = "RUNNING"
                sim["running"] = next_p
                sim["running_segment_start"] = t
                sim["rr_slice_remaining"] = sim.get("time_quantum", 2)
                if next_p.start_time == 0 and next_p.remaining_time == next_p.burst_time:
                    next_p.start_time = t

    # execute one time unit
    running = sim.get("running")

    # compute next aging time (like batch) and if it falls exactly on the next
    # tick (t+1) force a split after executing this unit so the schedule records
    # the aging boundary even when no ready candidate overtakes the running job.
    def next_aging_time_for(p: Patient) -> float:
        if not sim.get("enable_aging") or p.waiting_start_time is None:
            return float("inf")
        ws = p.waiting_start_time if p.waiting_start_time > 0 else p.arrival_time
        if ws >= t:
            return ws + sim.get("aging_interval", 3)
        age_steps = int((t - ws) / sim.get("aging_interval", 3))
        return ws + (age_steps + 1) * sim.get("aging_interval", 3)

    next_aging = float("inf")
    for p in list(sim.get("ready", [])) + ([running] if running is not None else []):
        try:
            tnext = next_aging_time_for(p)
            if tnext > t:
                next_aging = min(next_aging, tnext)
        except Exception:
            continue

    def close_running_segment(end_time: int) -> None:
        start = sim.get("running_segment_start")
        if sim.get("running") is not None and start is not None and end_time - start > 0:
            sim["schedule"].append({"patient_id": sim["running"].id, "start": start, "duration": end_time - start})

    if next_aging != float("inf") and next_aging == t + 1:
        sim["_force_split_after_unit"] = True
    if running:
        running.remaining_time -= 1
        if alg == "Round Robin":
            sim["rr_slice_remaining"] -= 1

        sim["current_time"] += 1

        if not running.has_been_to_io:
            close_running_segment(sim["current_time"])
            if running.remaining_time == 0:
                running.completion_time = sim["current_time"]
                running.turnaround_time = running.completion_time - running.arrival_time
                running.waiting_time = running.turnaround_time - running.burst_time
                running.state = "TERMINATED"
                sim["completed"].append(running)
                sim["running"] = None
                sim["running_segment_start"] = None
                sim["rr_slice_remaining"] = sim.get("time_quantum", 2)
            elif running.burst_time >= 5:
                running.io_time_remaining = 2
                running.state = "WAITING"
                running.has_been_to_io = True
                sim["waiting_io"].append(running)
                sim["running"] = None
                sim["running_segment_start"] = None
                sim["rr_slice_remaining"] = sim.get("time_quantum", 2)
            else:
                running.has_been_to_io = True
                sim["running_segment_start"] = sim["current_time"]
        else:
            if running.remaining_time == 0:
                close_running_segment(sim["current_time"])
                running.completion_time = sim["current_time"]
                running.turnaround_time = running.completion_time - running.arrival_time
                running.waiting_time = running.turnaround_time - running.burst_time
                running.state = "TERMINATED"
                sim["completed"].append(running)
                sim["running"] = None
                sim["rr_slice_remaining"] = sim.get("time_quantum", 2)
            elif alg == "Round Robin" and sim["rr_slice_remaining"] <= 0:
                close_running_segment(sim["current_time"])
                while sim["future"] and sim["future"][0].arrival_time <= sim["current_time"]:
                    p = sim["future"].popleft()
                    p.state = "READY"
                    if p.waiting_start_time <= 0:
                        p.waiting_start_time = sim["current_time"]
                    sim["ready"].append(p)
                running.state = "READY"
                running.waiting_start_time = sim["current_time"]
                sim["ready"].append(running)
                sim["running"] = None
                sim["rr_slice_remaining"] = sim.get("time_quantum", 2)
            else:
                # Continue current running segment.
                pass
    else:
        sim["current_time"] += 1

    # If a forced split was requested for the aging boundary after this unit,
    # close and reopen the running segment now (if still running).
    if sim.pop("_force_split_after_unit", False) and sim.get("running") is not None:
        start = sim.get("running_segment_start")
        end = sim.get("current_time")
        if start is not None and end - start > 0:
            sim["schedule"].append({"patient_id": sim["running"].id, "start": start, "duration": end - start})
        sim["running_segment_start"] = sim.get("current_time")

    # post-step aging recalculation
    if sim.get("enable_aging"):
        for p in sim["ready"]:
            prev = getattr(p, "effective_priority", p.priority)
            new = get_effective_priority(p, sim["current_time"], sim.get("enable_aging", False), sim.get("aging_interval", 3), sim.get("aging_step", 1))
            if new != prev:
                sim.setdefault("last_changes", []).append(f"BN{p.id}: ưu tiên {prev} -> {new}")
        running_proc = sim.get("running")
        if running_proc is not None:
            prev = getattr(running_proc, "effective_priority", running_proc.priority)
            new = get_effective_priority(running_proc, sim["current_time"], sim.get("enable_aging", False), sim.get("aging_interval", 3), sim.get("aging_step", 1))
            if new != prev:
                sim.setdefault("last_changes", []).append(f"BN{running_proc.id}: ưu tiên {prev} -> {new}")

    # If aging produced effective-priority changes after this unit, split the running
    # segment at the new current_time so the schedule records the boundary and the
    # next tick can pick a different process if needed (matching batch behavior).
    if sim.get("last_changes") and sim.get("running") is not None:
        start = sim.get("running_segment_start")
        end = sim.get("current_time")
        if start is not None and end - start > 0:
            sim["schedule"].append({"patient_id": sim["running"].id, "start": start, "duration": end - start})
        sim["running_segment_start"] = sim.get("current_time")

    # mark done
    if not sim["future"] and not sim["ready"] and not sim["waiting_io"] and sim.get("running") is None:
        sim["done"] = True
        sim["play"] = False

    return sim