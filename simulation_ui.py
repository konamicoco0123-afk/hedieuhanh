from typing import Dict, List

from algorithms import Patient, clone_patient, calculate_metrics, run_fcfs, run_sjf, run_priority_nonpreemptive, run_priority_preemptive, run_round_robin, run_multilevel_queue


def build_comparison_result(
    base_patients: List[Patient],
    time_quantum: int,
    enable_aging: bool,
    aging_interval: int,
    aging_step: int,
) -> List[Dict[str, object]]:
    """Chạy cùng một tập bệnh nhân qua nhiều thuật toán để so sánh."""
    results: List[Dict[str, object]] = []

    for name, func in [
        ("FCFS", lambda ps: run_fcfs(ps)),
        ("SJF", lambda ps: run_sjf(ps)),
        ("Priority NP", lambda ps: run_priority_nonpreemptive(ps, enable_aging=False, aging_interval=aging_interval, aging_step=aging_step)),
        ("Priority NP + Aging", lambda ps: run_priority_nonpreemptive(ps, enable_aging=enable_aging, aging_interval=aging_interval, aging_step=aging_step)),
        ("Priority P", lambda ps: run_priority_preemptive(ps, enable_aging=False, aging_interval=aging_interval, aging_step=aging_step)),
        ("Priority P + Aging", lambda ps: run_priority_preemptive(ps, enable_aging=enable_aging, aging_interval=aging_interval, aging_step=aging_step)),
        ("Round Robin", lambda ps: run_round_robin(ps, time_quantum)),
        ("Multilevel Queue", lambda ps: run_multilevel_queue(ps, time_quantum)),
    ]:
        sim_patients, schedule = func([clone_patient(p) for p in base_patients])
        avg_wait, avg_turnaround, total_completion = calculate_metrics(sim_patients)
        results.append(
            {
                "algorithm": name,
                "avg_waiting": avg_wait,
                "avg_turnaround": avg_turnaround,
                "total_completion": total_completion,
                "schedule": schedule,
            }
        )

    return results
