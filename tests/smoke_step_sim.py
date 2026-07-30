import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithms import Patient, run_priority_preemptive, calculate_metrics
from simulation import make_sim_state, step_sim_state


def run_step_sim_and_compare(patients, algorithm, enable_aging=False, aging_interval=3, aging_step=1):
    # Batch run
    batch_patients, batch_schedule = run_priority_preemptive(
        [Patient(id=p.id, arrival_time=p.arrival_time, burst_time=p.burst_time, priority=p.priority) for p in patients],
        enable_aging=enable_aging,
        aging_interval=aging_interval,
        aging_step=aging_step,
    )

    # Step-by-step run
    sim = make_sim_state(patients, algorithm, time_quantum=2, enable_aging=enable_aging, aging_interval=aging_interval, aging_step=aging_step)
    steps = 0
    while not sim.get("done") and steps < 1000:
        step_sim_state(sim)
        steps += 1
    step_schedule = sim.get("schedule", [])
    step_completed = sim.get("completed", [])

    # Compare total completion time
    b_avg_wait, b_avg_turnaround, b_total = calculate_metrics(batch_patients)
    s_avg_wait, s_avg_turnaround, s_total = calculate_metrics(step_completed)

    print("Batch total_completion:", b_total)
    print("Step total_completion:", s_total)
    print("Batch schedule:", batch_schedule)
    print("Step schedule:", step_schedule)

    assert abs(b_total - s_total) < 1e-6, f"Total completion mismatch: batch={b_total} step={s_total}"


if __name__ == "__main__":
    # Starvation case
    patients = [
        Patient(id=1, arrival_time=0, burst_time=10, priority=5),
        Patient(id=2, arrival_time=1, burst_time=1, priority=1),
        Patient(id=3, arrival_time=2, burst_time=1, priority=1),
    ]

    print("=== Priority Preemptive without Aging ===")
    run_step_sim_and_compare(patients, "Priority (Preemptive)", enable_aging=False)

    print("=== Priority Preemptive with Aging ===")
    run_step_sim_and_compare(patients, "Priority (Preemptive)", enable_aging=True, aging_interval=1, aging_step=1)

    print("All step-vs-batch checks passed.")
