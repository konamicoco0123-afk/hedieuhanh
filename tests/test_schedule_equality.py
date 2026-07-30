import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithms import Patient, run_priority_preemptive, run_round_robin, run_sjf
from simulation import make_sim_state, step_sim_state


def normalize(schedule):
    # convert numeric fields to ints for stable equality
    return [{
        "patient_id": int(seg["patient_id"]),
        "start": int(round(seg["start"])),
        "duration": int(round(seg["duration"]))
    } for seg in schedule]


def assert_schedules_equal(batch_schedule, step_schedule):
    b = normalize(batch_schedule)
    s = normalize(step_schedule)
    print("Batch schedule:", b)
    print("Step schedule:", s)
    assert b == s, f"Schedules differ:\nBATCH: {b}\nSTEP:  {s}"


def run_priority_case(patients, enable_aging=False, aging_interval=3, aging_step=1):
    batch_patients, batch_schedule = run_priority_preemptive(
        [Patient(id=p.id, arrival_time=p.arrival_time, burst_time=p.burst_time, priority=p.priority) for p in patients],
        enable_aging=enable_aging,
        aging_interval=aging_interval,
        aging_step=aging_step,
    )

    sim = make_sim_state(patients, "Priority (Preemptive)", time_quantum=2, enable_aging=enable_aging, aging_interval=aging_interval, aging_step=aging_step)
    steps = 0
    while not sim.get("done") and steps < 2000:
        step_sim_state(sim)
        steps += 1
    step_schedule = sim.get("schedule", [])

    assert_schedules_equal(batch_schedule, step_schedule)


def run_rr_case(patients, time_quantum=2):
    batch_completed, batch_schedule = run_round_robin(
        [Patient(id=p.id, arrival_time=p.arrival_time, burst_time=p.burst_time, priority=p.priority) for p in patients],
        time_quantum=time_quantum,
    )

    sim = make_sim_state(patients, "Round Robin", time_quantum=time_quantum)
    steps = 0
    while not sim.get("done") and steps < 2000:
        step_sim_state(sim)
        steps += 1
    step_schedule = sim.get("schedule", [])

    assert_schedules_equal(batch_schedule, step_schedule)


if __name__ == "__main__":
    patients = [
        Patient(id=1, arrival_time=0, burst_time=10, priority=5),
        Patient(id=2, arrival_time=1, burst_time=1, priority=1),
        Patient(id=3, arrival_time=2, burst_time=1, priority=1),
    ]

    print("Testing Priority Preemptive without Aging")
    run_priority_case(patients, enable_aging=False)

    print("Testing Priority Preemptive with Aging")
    run_priority_case(patients, enable_aging=True, aging_interval=1, aging_step=1)

    print("Testing Round Robin equality")
    run_rr_case(patients, time_quantum=2)

    print("All strict schedule-equality tests passed.")
