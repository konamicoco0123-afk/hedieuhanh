import time
from typing import List

import pandas as pd
import streamlit as st

from algorithms import Patient, clone_patient, patient_to_row
from simulation import make_sim_state, step_sim_state
from ui_helpers import draw_gantt_chart


def init_simulation_state(
    patients: List[Patient],
    algorithm: str,
    time_quantum: int = 2,
    enable_aging: bool = False,
    aging_interval: int = 3,
    aging_step: int = 1,
) -> None:
    sim_state = make_sim_state(patients, algorithm, time_quantum, enable_aging, aging_interval, aging_step)
    sim_state["speed_factor"] = st.session_state.get("sim_speed_factor", sim_state.get("speed_factor", 1.0))
    st.session_state["sim_state"] = sim_state


def sim_step() -> None:
    if "sim_state" not in st.session_state:
        return
    sim = st.session_state["sim_state"]
    if sim is None:
        return
    st.session_state["sim_state"] = step_sim_state(sim)


def reset_simulation_state() -> None:
    st.session_state.pop("sim_state", None)


def get_autoplay_delay(speed_factor: float) -> float:
    return 0.8 / max(0.25, float(speed_factor or 1.0))


def render_step_by_step_ui(
    patients: List[Patient],
    algorithm: str,
    time_quantum: int,
    apply_aging: bool,
    aging_interval: int,
    aging_step: int,
) -> None:
    st.markdown("---")
    st.subheader("Mô phỏng Từng Bước")

    if st.button("Khởi tạo mô phỏng từng bước", key="step_init"):
        if not patients:
            st.warning("Vui lòng nạp dữ liệu bệnh nhân trước khi bắt đầu mô phỏng từng bước.")
        else:
            init_simulation_state(
                [clone_patient(p) for p in patients],
                algorithm,
                time_quantum=time_quantum,
                enable_aging=apply_aging,
                aging_interval=aging_interval,
                aging_step=aging_step,
            )
            st.rerun()

    sim = st.session_state.get("sim_state")
    if not sim:
        return

    cols = st.columns([1, 1, 1, 1, 1])
    with cols[0]:
        if st.button("Play", key="step_play"):
            sim["play"] = True
    with cols[1]:
        if st.button("Pause", key="step_pause"):
            sim["play"] = False
    with cols[2]:
        if st.button("Next Step", key="step_next"):
            sim_step()
            st.rerun()
    with cols[3]:
        if st.button("Reset", key="step_reset"):
            reset_simulation_state()
            st.rerun()
    with cols[4]:
        speed_factor = sim.get("speed_factor", st.session_state.get("sim_speed_factor", 1.0))
        st.markdown(f"**Tốc độ:** {speed_factor}x")

    st.markdown(f"**Current Time:** {sim['current_time']}")

    status_map = {
        "NEW": len(sim.get("future", [])),
        "READY": len(sim.get("ready", [])),
        "RUNNING": 1 if sim.get("running") else 0,
        "WAITING": len(sim.get("waiting_io", [])),
        "TERMINATED": len(sim.get("completed", [])),
    }
    status_colors = {
        "NEW": "#eef3ff",
        "READY": "#eafaf1",
        "RUNNING": "#fff3d6",
        "WAITING": "#fff0f0",
        "TERMINATED": "#f2f2f2",
    }
    status_cols = st.columns(5)
    for col, label in zip(status_cols, ["NEW", "READY", "RUNNING", "WAITING", "TERMINATED"]):
        value = status_map.get(label, 0)
        color = status_colors.get(label, "#f2f2f2")
        col.markdown(
            f"<div style='padding:10px 12px; border:1px solid #dfe3e8; border-radius:8px; background:{color}; text-align:center;'><div style='font-size:12px; color:#374151;'> {label} </div><div style='font-size:22px; font-weight:700; color:#111827;'> {value} </div></div>",
            unsafe_allow_html=True,
        )

    new_df = pd.DataFrame(
        [
            {
                "id": p.id,
                "arrival": p.arrival_time,
                "burst": p.burst_time,
                "priority": getattr(p, "effective_priority", p.priority),
                "state": "NEW",
            }
            for p in sim.get("future", [])
        ]
    )
    if not new_df.empty:
        new_df = new_df.rename(
            columns={
                "id": "Mã BN",
                "arrival": "Thời điểm đến",
                "burst": "Thời gian khám",
                "priority": "Ưu tiên",
                "state": "Trạng thái",
            }
        )
    st.caption("New")
    if new_df.empty:
        st.write("New: (trống)")
    else:
        st.dataframe(new_df, use_container_width=True)

    running = sim.get("running")
    if running:
        running_df = pd.DataFrame(
            [
                {
                    "id": running.id,
                    "arrival": running.arrival_time,
                    "rem": running.remaining_time,
                    "priority": getattr(running, "effective_priority", running.priority),
                    "state": "RUNNING",
                }
            ]
        )
        running_df = running_df.rename(
            columns={
                "id": "Mã BN",
                "arrival": "Thời điểm đến",
                "rem": "Còn lại",
                "priority": "Ưu tiên",
                "state": "Trạng thái",
            }
        )
        st.caption("Running")
        st.dataframe(running_df, use_container_width=True)
    else:
        st.caption("Running")
        st.write("Running: (trống)")

    ready_df = pd.DataFrame(
        [
            {
                "id": p.id,
                "arrival": p.arrival_time,
                "rem": p.remaining_time,
                "priority": getattr(p, "effective_priority", p.priority),
                "state": p.state,
            }
            for p in sorted(sim.get("ready", []), key=lambda p: (getattr(p, "effective_priority", p.priority), p.arrival_time, p.id))
        ]
    )
    if not ready_df.empty:
        ready_df = ready_df.rename(
            columns={
                "id": "Mã BN",
                "arrival": "Thời điểm đến",
                "rem": "Còn lại",
                "priority": "Ưu tiên",
                "state": "Trạng thái",
            }
        )
    st.caption("Ready Queue")
    if ready_df.empty:
        st.write("Ready Queue: (trống)")
    else:
        st.dataframe(ready_df, use_container_width=True)

    waiting_df = pd.DataFrame(
        [
            {
                "id": p.id,
                "state": p.state,
                "io_remaining": p.io_time_remaining,
                "rem": p.remaining_time,
            }
            for p in sim.get("waiting_io", [])
        ]
    )
    if not waiting_df.empty:
        waiting_df = waiting_df.rename(
            columns={
                "id": "Mã BN",
                "state": "Trạng thái",
                "io_remaining": "I/O còn lại",
                "rem": "Còn lại",
            }
        )
    st.caption("Waiting (I/O)")
    if waiting_df.empty:
        st.write("Waiting (I/O): (trống)")
    else:
        st.dataframe(waiting_df, use_container_width=True)

    comp_df = pd.DataFrame([patient_to_row(p) for p in sim.get("completed", [])])
    if not comp_df.empty:
        comp_df = comp_df.rename(
            columns={
                "id": "Mã BN",
                "disease": "Bệnh",
                "arrival_time": "Thời điểm đến",
                "burst_time": "Thời gian khám",
                "priority": "Ưu tiên",
                "effective_priority": "Ưu tiên hiệu dụng",
                "remaining_time": "Còn lại",
                "waiting_time": "Thời gian chờ",
                "waiting_start_time": "Bắt đầu chờ",
                "turnaround_time": "Thời gian quay vòng",
                "start_time": "Thời điểm bắt đầu",
                "completion_time": "Thời điểm kết thúc",
                "state": "Trạng thái",
                "io_time_remaining": "I/O còn lại",
            }
        )
    st.caption("Completed")
    if comp_df.empty:
        st.write("Completed: (trống)")
    else:
        st.dataframe(comp_df, use_container_width=True)

    summary = (
        f"NEW: {status_map.get('NEW', 0)} | "
        f"READY: {status_map.get('READY', 0)} | "
        f"RUNNING: {status_map.get('RUNNING', 0)} | "
        f"WAITING: {status_map.get('WAITING', 0)} | "
        f"TERMINATED: {status_map.get('TERMINATED', 0)}"
    )
    st.caption(summary)

    if sim.get("done"):
        st.success("Hoàn thành mô phỏng.")

    if sim.get("last_changes"):
        for change in sim.get("last_changes", []):
            st.info(change)

    temp_schedule = list(sim.get("schedule", []))
    running = sim.get("running")
    start = sim.get("running_segment_start")
    if running and start is not None:
        dur = sim["current_time"] - start
        if dur <= 0:
            dur = 1
        temp_schedule.append({"patient_id": running.id, "start": start, "duration": dur})
    if temp_schedule:
        st.pyplot(draw_gantt_chart(temp_schedule, title=f"Gantt (từng bước) - {sim.get('algorithm')}"))

    st.session_state["sim_state"] = sim

    if sim.get("play") and not sim.get("done"):
        delay = get_autoplay_delay(sim.get("speed_factor", st.session_state.get("sim_speed_factor", 1.0)))
        time.sleep(delay)
        sim_step()
        st.rerun()
