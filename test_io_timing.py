#!/usr/bin/env python3
"""Test to verify I/O timing fix (off-by-one correction)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from algorithms import Patient
from simulation import make_sim_state, step_sim_state


def test_io_timing():
    """
    Test that I/O duration is exactly 2 time units (io_time_remaining = 2).
    
    Expected log pattern:
    [t=N] BN vào WAITING
    [t=N+1] (no log, I/O happening)
    [t=N+2] (no log, I/O happening)
    [t=N+3] BN quay lại READY (after 2 full time units)
    
    Actually, with the fix:
    - t=N (lúc chạy): vào WAITING, io_enter_time = N
    - t=N đầu bước kế: process_waiting_io chạy, current_time = N+1 > io_enter_time, trừ: io = 1
    - t=N+1 đầu bước kế: process_waiting_io chạy, current_time = N+2 > io_enter_time, trừ: io = 0, quay lại
    
    So from entering at t=N to returning at t=N+2 (after 2 decrements).
    """
    
    # Create a patient that will trigger I/O
    patients = [
        Patient(id=1, arrival_time=0, burst_time=10, priority=1)
    ]
    
    sim = make_sim_state(patients, "FCFS")
    
    # Run simulation and track I/O events
    io_enter_time = None
    io_exit_time = None
    step = 0
    
    while not sim.get("done") and step < 50:
        step_sim_state(sim)
        step += 1
        
        # Check if patient entered WAITING in this step's logs
        for log_entry in sim.get("logs", []):
            if "chuyển sang WAITING" in log_entry:
                # Extract time from log
                t_str = log_entry.split("[t=")[1].split("]")[0]
                io_enter_time = int(t_str)
                print(f"IO Enter: {log_entry}")
            elif "quay lại READY" in log_entry and io_enter_time is not None:
                t_str = log_entry.split("[t=")[1].split("]")[0]
                io_exit_time = int(t_str)
                print(f"IO Exit: {log_entry}")
    
    print(f"\n=== I/O Timing Analysis ===")
    print(f"IO Enter Time: t={io_enter_time}")
    print(f"IO Exit Time:  t={io_exit_time}")
    
    if io_enter_time is not None and io_exit_time is not None:
        duration = io_exit_time - io_enter_time
        print(f"Duration: {duration} time units")
        
        if duration == 2:
            print("✓ CORRECT: I/O took exactly 2 time units")
            return True
        else:
            print(f"✗ WRONG: Expected 2 time units, got {duration}")
            return False
    else:
        print("✗ ERROR: Could not find I/O enter/exit logs")
        return False


if __name__ == "__main__":
    success = test_io_timing()
    sys.exit(0 if success else 1)
