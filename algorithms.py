import random
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from disease import load_diseases


@dataclass
class Patient:

    id: int
    arrival_time: int
    burst_time: int
    priority: int
    disease: str = ""

    remaining_time: int = field(init=False)
    waiting_time: float = 0.0
    turnaround_time: float = 0.0
    start_time: float = 0.0
    completion_time: float = 0.0
    waiting_start_time: float = 0.0
    effective_priority: int = field(init=False)

    def __post_init__(self) -> None:
        self.remaining_time = self.burst_time
        self.effective_priority = self.priority


import random
from disease import load_diseases


def generate_random_patients(count):

    diseases = load_diseases()

    priority_groups = {
        1: [],
        2: [],
        3: [],
        4: [],
        5: []
    }

    for d in diseases:
        priority_groups[d["priority"]].append(d)


    patients = []

    for i in range(count):

        priority = (i % 5) + 1

        disease = random.choice(
            priority_groups[priority]
        )


        patients.append(
            Patient(
                id=i+1,
                arrival_time=random.randint(0,5),
                burst_time=random.randint(1,5),
                priority=priority,
                disease=disease["disease"]
            )
        )

    return patients
def patient_to_row(patient):

    return {

        "id": patient.id,

        "disease": patient.disease,

        "arrival_time": patient.arrival_time,

        "burst_time": patient.burst_time,

        "priority": patient.priority,

        "effective_priority": patient.effective_priority,

        "remaining_time": patient.remaining_time,

        "waiting_time": patient.waiting_time,

        "waiting_start_time": patient.waiting_start_time,

        "turnaround_time": patient.turnaround_time,

        "start_time": patient.start_time,

        "completion_time": patient.completion_time

    }


def clone_patient(patient: Patient) -> Patient:
    return Patient(
        id=patient.id,
        arrival_time=patient.arrival_time,
        burst_time=patient.burst_time,
        priority=patient.priority,
        disease=patient.disease
    )


def build_gantt_schedule(patients: List[Patient]) -> List[Dict[str, float]]:
    return [
        {
            "patient_id": patient.id,
            "start": patient.start_time,
            "duration": patient.completion_time - patient.start_time,
        }
        for patient in patients
    ]


def get_effective_priority(
    patient: Patient,
    current_time: float,
    enable_aging: bool,
    aging_interval: int,
    aging_step: int,
) -> int:
    if not enable_aging or aging_interval <= 0:
        patient.effective_priority = patient.priority
        return patient.effective_priority

    if patient.waiting_start_time <= 0:
        patient.waiting_start_time = patient.arrival_time

    age_steps = int((current_time - patient.waiting_start_time) / aging_interval)
    patient.effective_priority = max(1, patient.priority - age_steps * aging_step)
    return patient.effective_priority


def recalc_effective_priorities(
    patients: List[Patient], current_time: float, enable_aging: bool, aging_interval: int, aging_step: int
) -> List[str]:
    changes: List[str] = []
    for p in patients:
        prev = getattr(p, "effective_priority", p.priority)
        new = get_effective_priority(p, current_time, enable_aging, aging_interval, aging_step)
        if new != prev:
            changes.append(f"BN{p.id}: ưu tiên {prev} -> {new}")
    return changes


def run_fcfs(patients: List[Patient]) -> Tuple[List[Patient], List[Dict[str, float]]]:
    timeline = 0
    sorted_patients = sorted(patients, key=lambda p: p.arrival_time)
    for patient in sorted_patients:
        if timeline < patient.arrival_time:
            timeline = patient.arrival_time
        patient.start_time = timeline
        patient.waiting_time = timeline - patient.arrival_time
        timeline += patient.burst_time
        patient.completion_time = timeline
        patient.turnaround_time = patient.completion_time - patient.arrival_time
        patient.remaining_time = 0
    return sorted_patients, build_gantt_schedule(sorted_patients)


def run_sjf(patients: List[Patient]) -> Tuple[List[Patient], List[Dict[str, float]]]:
    timeline = 0
    completed: List[Patient] = []
    ready: List[Patient] = []
    waiting = sorted(patients, key=lambda p: p.arrival_time)

    while waiting or ready:
        while waiting and waiting[0].arrival_time <= timeline:
            ready.append(waiting.pop(0))
        if not ready:
            timeline = waiting[0].arrival_time
            continue
        ready.sort(key=lambda p: (p.burst_time, p.arrival_time))
        patient = ready.pop(0)
        patient.start_time = timeline
        patient.waiting_time = timeline - patient.arrival_time
        timeline += patient.burst_time
        patient.completion_time = timeline
        patient.turnaround_time = patient.completion_time - patient.arrival_time
        patient.remaining_time = 0
        completed.append(patient)

    return completed, build_gantt_schedule(completed)


def run_priority_nonpreemptive(
    patients: List[Patient],
    enable_aging: bool = False,
    aging_interval: int = 3,
    aging_step: int = 1,
) -> Tuple[List[Patient], List[Dict[str, float]]]:
    timeline = 0
    completed: List[Patient] = []
    ready: List[Patient] = []
    waiting = sorted(patients, key=lambda p: p.arrival_time)

    while waiting or ready:
        while waiting and waiting[0].arrival_time <= timeline:
            patient = waiting.pop(0)
            if patient.waiting_start_time <= 0:
                patient.waiting_start_time = patient.arrival_time
            ready.append(patient)

        if not ready:
            timeline = waiting[0].arrival_time
            continue

        changes = recalc_effective_priorities(ready, timeline, enable_aging, aging_interval, aging_step)
        ready.sort(key=lambda p: (p.effective_priority, p.arrival_time))
        patient = ready.pop(0)
        patient.start_time = timeline
        patient.waiting_time = timeline - patient.arrival_time
        timeline += patient.burst_time
        patient.completion_time = timeline
        patient.turnaround_time = patient.completion_time - patient.arrival_time
        patient.remaining_time = 0
        completed.append(patient)

    return completed, build_gantt_schedule(completed)


def run_priority_preemptive(
    patients: List[Patient],
    enable_aging: bool = False,
    aging_interval: int = 3,
    aging_step: int = 1,
) -> Tuple[List[Patient], List[Dict[str, float]]]:
    timeline = 0
    waiting = sorted(patients, key=lambda p: p.arrival_time)
    ready: List[Patient] = []
    completed: List[Patient] = []
    schedule: List[Dict[str, float]] = []
    current: Optional[Patient] = None

    while waiting or ready or current:
        while waiting and waiting[0].arrival_time <= timeline:
            patient = waiting.pop(0)
            if patient.waiting_start_time <= 0:
                patient.waiting_start_time = patient.arrival_time
            ready.append(patient)

        if current is None:
            if ready:
                for patient in ready:
                    get_effective_priority(patient, timeline, enable_aging, aging_interval, aging_step)
                ready.sort(key=lambda p: (p.effective_priority, p.arrival_time))
                current = ready.pop(0)
                if current.start_time == 0 and current.remaining_time == current.burst_time:
                    current.start_time = timeline
            elif waiting:
                timeline = waiting[0].arrival_time
                continue
            else:
                break

        changes = recalc_effective_priorities(ready, timeline, enable_aging, aging_interval, aging_step)
        if ready:
            ready.sort(key=lambda p: (p.effective_priority, p.arrival_time))
            if current is not None and ready[0].effective_priority < getattr(current, "effective_priority", current.priority):
                current.waiting_start_time = timeline
                ready.append(current)
                current = None
                continue

        # determine next arrival time
        next_arrival = waiting[0].arrival_time if waiting else float("inf")

        def next_aging_time_for(p: Patient) -> float:
            if not enable_aging or p.waiting_start_time is None:
                return float("inf")
            ws = p.waiting_start_time if p.waiting_start_time > 0 else p.arrival_time
            if ws >= timeline:
                return ws + aging_interval
            age_steps = int((timeline - ws) / aging_interval)
            return ws + (age_steps + 1) * aging_interval

        next_aging = float("inf")
        for p in list(ready) + ([current] if current is not None else []):
            try:
                tnext = next_aging_time_for(p)
                if tnext > timeline:
                    next_aging = min(next_aging, tnext)
            except Exception:
                continue

        run_time = min(current.remaining_time, next_arrival - timeline, next_aging - timeline)
        if run_time <= 0:
            timeline = next_arrival
            continue

        schedule.append({"patient_id": current.id, "start": timeline, "duration": run_time})
        current.remaining_time -= run_time
        timeline += run_time

        while waiting and waiting[0].arrival_time <= timeline:
            patient = waiting.pop(0)
            if patient.waiting_start_time <= 0:
                patient.waiting_start_time = patient.arrival_time
            ready.append(patient)

        if current.remaining_time == 0:
            current.completion_time = timeline
            current.turnaround_time = current.completion_time - current.arrival_time
            current.waiting_time = current.turnaround_time - current.burst_time
            completed.append(current)
            current = None

    return completed, schedule


def run_round_robin(patients: List[Patient], time_quantum: int) -> Tuple[List[Patient], List[Dict[str, float]]]:
    timeline = 0
    future = deque(sorted(patients, key=lambda p: p.arrival_time))
    ready: deque[Patient] = deque()
    completed: List[Patient] = []
    schedule: List[Dict[str, float]] = []

    while future or ready:
        while future and future[0].arrival_time <= timeline:
            ready.append(future.popleft())

        if not ready:
            timeline = future[0].arrival_time
            continue

        patient = ready.popleft()
        if patient.start_time == 0 and patient.remaining_time == patient.burst_time:
            patient.start_time = timeline

        run_time = min(patient.remaining_time, time_quantum)
        schedule.append({"patient_id": patient.id, "start": timeline, "duration": run_time})
        patient.remaining_time -= run_time
        timeline += run_time

        while future and future[0].arrival_time <= timeline:
            ready.append(future.popleft())

        if patient.remaining_time == 0:
            patient.completion_time = timeline
            patient.turnaround_time = patient.completion_time - patient.arrival_time
            patient.waiting_time = patient.turnaround_time - patient.burst_time
            completed.append(patient)
        else:
            ready.append(patient)

    return completed, schedule


def calculate_metrics(patients: List[Patient]) -> Tuple[float, float, float]:
    if not patients:
        return 0.0, 0.0, 0.0
    avg_wait = sum(patient.waiting_time for patient in patients) / len(patients)
    avg_turnaround = sum(patient.turnaround_time for patient in patients) / len(patients)
    total_completion = max((patient.completion_time for patient in patients), default=0.0)
    return avg_wait, avg_turnaround, total_completion
