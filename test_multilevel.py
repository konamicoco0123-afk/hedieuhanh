from algorithms import Patient, run_multilevel_queue

patients = [
    Patient(id=1, arrival_time=0, burst_time=5, priority=4, disease="D1"),
    Patient(id=2, arrival_time=1, burst_time=3, priority=2, disease="D2"),
    Patient(id=3, arrival_time=2, burst_time=4, priority=1, disease="D3"),
    Patient(id=4, arrival_time=3, burst_time=2, priority=5, disease="D4"),
    Patient(id=5, arrival_time=4, burst_time=1, priority=3, disease="D5"),
    Patient(id=6, arrival_time=5, burst_time=2, priority=1, disease="D6"),
]

completed, schedule = run_multilevel_queue([Patient(id=p.id, arrival_time=p.arrival_time, burst_time=p.burst_time, priority=p.priority, disease=p.disease) for p in patients], time_quantum=2)

print("Schedule:")
for seg in schedule:
    print(seg)

print("\nCompletion order:")
for p in completed:
    print(f"id={p.id}, priority={p.priority}, arrival={p.arrival_time}, start={p.start_time}, completion={p.completion_time}, remaining={p.remaining_time}")
