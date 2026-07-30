import sys
import os

# ensure project root is on sys.path so importing algorithms works when running this script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from algorithms import (
    Patient,
    clone_patient,
    run_fcfs,
    run_sjf,
    run_priority_nonpreemptive,
    run_priority_preemptive,
    run_round_robin,
    calculate_metrics,
)


def make_starvation_case():
    # Low priority long job arrives first, higher priority short jobs arrive later
    return [
        Patient(id=1, arrival_time=0, burst_time=10, priority=5),
        Patient(id=2, arrival_time=1, burst_time=1, priority=1),
        Patient(id=3, arrival_time=2, burst_time=1, priority=1),
    ]


def print_result(name, patients, schedule):
    avg_wait, avg_turnaround, total_completion = calculate_metrics(patients)
    print(f"{name}: avg_wait={avg_wait:.2f}, avg_turnaround={avg_turnaround:.2f}, total_completion={total_completion}")
    print("Schedule:")
    for seg in schedule:
        print(f"  BN{seg['patient_id']} @ {seg['start']} for {seg['duration']}")
    print()


def run_all():
    base = make_starvation_case()

    for name, func in [
        ("FCFS", lambda ps: run_fcfs([clone_patient(p) for p in ps])),
        ("SJF", lambda ps: run_sjf([clone_patient(p) for p in ps])),
        ("Priority NP no aging", lambda ps: run_priority_nonpreemptive([clone_patient(p) for p in ps], enable_aging=False)),
        ("Priority NP + aging", lambda ps: run_priority_nonpreemptive([clone_patient(p) for p in ps], enable_aging=True, aging_interval=1, aging_step=1)),
        ("Priority P no aging", lambda ps: run_priority_preemptive([clone_patient(p) for p in ps], enable_aging=False)),
        ("Priority P + aging", lambda ps: run_priority_preemptive([clone_patient(p) for p in ps], enable_aging=True, aging_interval=1, aging_step=1)),
        ("Round Robin (q=2)", lambda ps: run_round_robin([clone_patient(p) for p in ps], time_quantum=2)),
    ]:
        try:
            patients, schedule = func(base)
            print_result(name, patients, schedule)
        except Exception as e:
            print(f"{name} raised an exception: {e}")
            raise


if __name__ == "__main__":
    run_all()
