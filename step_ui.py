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
    running = sim.get("running")
    if running:
        st.markdown(
            f"<div style='background:#ffe6b3;padding:8px;border-radius:4px;'>**Running:** <strong>BN{running.id}</strong> (rem={running.remaining_time})</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("**Running:** -")

    if sim.get("done"):
        st.success("Hoàn thành mô phỏng.")

    if sim.get("last_changes"):
        for change in sim.get("last_changes", []):
            st.info(change)

    if sim.get("ready"):
        ready_df = pd.DataFrame(
            [
                {
                    "id": p.id,
                    "arrival": p.arrival_time,
                    "rem": p.remaining_time,
                    "eff_prio": getattr(p, "effective_priority", p.priority),
                }
                for p in sorted(sim.get("ready"), key=lambda p: (getattr(p, "effective_priority", p.priority), p.arrival_time, p.id))
            ]
        )
        ready_df = ready_df.rename(
            columns={
                "id": "Mã BN",
                "arrival": "Thời điểm đến",
                "rem": "Còn lại",
                "eff_prio": "Ưu tiên",
            }
        )
        st.caption("Ready Queue")
        st.dataframe(ready_df, use_container_width=True)
    else:
        st.caption("Ready Queue: (trống)")

    if sim.get("completed"):
        comp_df = pd.DataFrame([patient_to_row(p) for p in sim.get("completed")])
        st.caption("Completed")
        st.dataframe(comp_df, use_container_width=True)

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
        sim_step()
        st.rerun()
