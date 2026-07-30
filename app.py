from typing import Dict, List

import pandas as pd
import streamlit as st
from disease import load_diseases, get_priority_by_disease

def update_priority():
    df = st.session_state.get("patient_editor")

    if isinstance(df, dict):
        return

    for index in df.index:
        disease = df.loc[index, "Loại bệnh"]

        if pd.notna(disease):
            df.loc[index, "Mức ưu tiên"] = get_priority_by_disease(disease)

    st.session_state["patient_editor"] = df

COLUMN_NAMES = {
    "id": "Mã BN",
    "disease": "Loại bệnh",
    "arrival_time": "Thời điểm đến",
    "burst_time": "Thời gian khám",
    "priority": "Mức ưu tiên",
    "effective_priority": "Ưu tiên hiệu dụng",
    "remaining_time": "Thời gian còn lại",
    "waiting_time": "Thời gian chờ",
    "waiting_start_time": "Bắt đầu chờ",
    "turnaround_time": "Thời gian hoàn thành",
    "start_time": "Bắt đầu khám",
    "completion_time": "Kết thúc khám",
}
from algorithms import (
    Patient,
    generate_random_patients,
    patient_to_row,
    clone_patient,
    run_fcfs,
    run_sjf,
    run_priority_nonpreemptive,
    run_priority_preemptive,
    run_round_robin,
    calculate_metrics,
)
from simulation_ui import build_comparison_result
from step_ui import init_simulation_state, render_step_by_step_ui
from ui_helpers import draw_gantt_chart

st.set_page_config(page_title="Mô phỏng hệ thống bốc số phòng khám", layout="wide")

from pathlib import Path

# Header logos (stable in layout) — use Streamlit images in columns so they remain visible
_logo_dir = Path(__file__).parent / "anh"
try:
    logo_col, _ = st.columns([0.18, 0.82])
    with logo_col:
        c1, c2 = st.columns([1, 1.2])
        try:
            c1.image(str(_logo_dir / "logodaihoc.png"), width=72, clamp=True, output_format="PNG")
        except Exception:
            pass
        try:
            c2.image(str(_logo_dir / "logobenhvien.png"), width=96, clamp=True, output_format="PNG")
        except Exception:
            pass
except Exception:
    pass

st.session_state.setdefault("patients", [])
st.session_state.setdefault("result", None)
st.session_state.setdefault("comparison_result", None)
st.session_state.setdefault("patient_count", 5)
st.session_state.setdefault("apply_aging", False)
st.session_state.setdefault("aging_interval", 3)
st.session_state.setdefault("aging_step", 1)
st.session_state.setdefault("step_by_step", False)
st.session_state.setdefault("sim_speed_factor", 1.0)
st.session_state.setdefault("sim_last_changes", [])

st.title("Mô phỏng hệ thống bốc số phòng khám")

with st.sidebar:
    st.header("Cấu hình hệ thống")
    st.session_state["patient_count"] = st.number_input(
        "Số lượng bệnh nhân",
        min_value=1,
        max_value=10,
        value=st.session_state["patient_count"],
        step=1,
    )

    algorithm = st.selectbox(
        "Chọn thuật toán",
        ["FCFS", "SJF", "Priority (Non-preemptive)", "Priority (Preemptive)", "Round Robin"],
    )
    st.session_state["sim_speed_factor"] = st.slider(
    "⚡ Tốc độ mô phỏng",
    min_value=0.25,
    max_value=5.0,
    value=st.session_state.get("sim_speed_factor", 1.0),
    step=0.25,
    help="Kéo sang phải để mô phỏng nhanh hơn."
)

    if algorithm == "Round Robin":
        time_quantum = st.number_input("Time Quantum", min_value=1, value=2, step=1)
    else:
        time_quantum = 2

    st.session_state["apply_aging"] = st.checkbox(
        "Áp dụng Aging",
        value=st.session_state["apply_aging"],
        help="Khi bật, các bệnh nhân chờ lâu sẽ được ưu tiên cao hơn dần.",
    )
    st.session_state["aging_interval"] = st.number_input(
        "Aging Interval (giây)",
        min_value=1,
        value=st.session_state["aging_interval"],
        step=1,
    )
    st.session_state["aging_step"] = st.number_input(
        "Aging Step",
        min_value=1,
        value=st.session_state["aging_step"],
        step=1,
    )

    if st.button("Bốc số ngẫu nhiên"):
        st.session_state["patients"] = generate_random_patients(st.session_state["patient_count"])
        st.session_state["result"] = None
        st.session_state["comparison_result"] = None

    if st.button("Reset tất cả"):
        st.session_state["patients"] = []
        st.session_state["result"] = None
        st.session_state["comparison_result"] = None
        st.session_state["patient_count"] = 5
        st.session_state["apply_aging"] = False
        st.session_state["aging_interval"] = 3
        st.session_state["aging_step"] = 1
        st.rerun()

if st.button("Khởi tạo nhập tay"):

    st.session_state["patients"] = []

    for i in range(1, st.session_state["patient_count"] + 1):

        st.session_state["patients"].append(
            Patient(
                id=i,
                arrival_time=0,
                burst_time=1,
                priority=5,
                disease=""
            )
        )

    st.session_state["result"] = None
    st.session_state["comparison_result"] = None

    st.session_state["result"] = None
    st.session_state["comparison_result"] = None
        
    st.session_state["result"] = None
    st.session_state["comparison_result"] = None

    st.session_state["step_by_step"] = st.checkbox(
        "Bật Step-by-Step",
        value=st.session_state.get("step_by_step", False),
        help="Bật chế độ mô phỏng từng bước (hiển thị các điều khiển Play/Pause/Next/Reset)",
    )
    if st.session_state["step_by_step"]:
        speed_val = st.select_slider(
            "Tốc độ mô phỏng",
            options=[0.5, 1.0, 2.0, 4.0],
            value=st.session_state.get("sim_speed_factor", 1.0),
        )
        st.session_state["sim_speed_factor"] = speed_val
        if "sim_state" in st.session_state and st.session_state.get("sim_state") is not None:
            st.session_state["sim_state"]["speed_factor"] = speed_val
        if st.button("Bắt đầu Mô phỏng Từng Bước (Sidebar)"):
            if not st.session_state["patients"]:
                st.warning("Vui lòng nạp dữ liệu bệnh nhân trước khi bắt đầu mô phỏng từng bước.")
            else:
                init_simulation_state(
                    [clone_patient(p) for p in st.session_state["patients"]],
                    algorithm,
                    time_quantum=time_quantum,
                    enable_aging=st.session_state.get("apply_aging", False),
                    aging_interval=st.session_state.get("aging_interval", 3),
                    aging_step=st.session_state.get("aging_step", 1),
                )
                st.session_state["sim_state"]["speed_factor"] = st.session_state.get("sim_speed_factor", 1.0)
                st.rerun()

st.subheader("Danh sách bệnh nhân")

DISPLAY_COLUMNS = list(COLUMN_NAMES.keys())

if st.session_state["patients"]:

    patient_df = pd.DataFrame(
        [patient_to_row(patient) for patient in st.session_state["patients"]]
    )

    for col in DISPLAY_COLUMNS:
        if col not in patient_df.columns:
            patient_df[col] = None

    patient_df = patient_df[DISPLAY_COLUMNS]

else:
    patient_df = pd.DataFrame(columns=DISPLAY_COLUMNS)


display_df = patient_df.rename(columns=COLUMN_NAMES)


disease_options = [
    d["disease"]
    for d in load_diseases()
]


edited_df = st.data_editor(
    display_df,
    num_rows="dynamic",
    use_container_width=True,
    key="patient_editor",
    on_change=update_priority,
    column_config={
        "Loại bệnh": st.column_config.SelectboxColumn(
            "Loại bệnh",
            options=disease_options,
            required=True
        ),
        "Mức ưu tiên": st.column_config.NumberColumn(
            "Mức ưu tiên",
            disabled=True
        )
    }
)

if not st.session_state["patients"]:
    st.caption("Chưa có dữ liệu. Hãy bấm 'Bốc số ngẫu nhiên' hoặc 'Khởi tạo nhập tay'.")

if edited_df is not None and st.button("Cập nhật dữ liệu bệnh nhân"):
    updated_patients: List[Patient] = []
    validation_errors: List[str] = []
    reverse_column_names = {v: k for k, v in COLUMN_NAMES.items()}
    edited_df = edited_df.rename(columns=reverse_column_names)
    for idx, row in edited_df.iterrows():
        try:
            pid = int(row["id"])
            arrival = int(row["arrival_time"])
            burst = int(row["burst_time"])

            priority = get_priority_by_disease(
                row["disease"]
            )

            if arrival < 0 or burst <= 0:
                raise ValueError
            updated_patients.append(
    Patient(
        id=pid,
        arrival_time=arrival,
        burst_time=burst,
        priority=priority,
        disease=row["disease"]
    )
)
        except Exception:
            validation_errors.append(f"Dòng {idx + 1} có dữ liệu không hợp lệ.")

    if validation_errors:
        st.warning("\n".join(validation_errors))
    else:
        if updated_patients:
            st.session_state["patients"] = updated_patients
            st.session_state["result"] = None
            st.session_state["comparison_result"] = None
            st.success("Cập nhật danh sách bệnh nhân thành công.")

if st.button("Bắt đầu mô phỏng"):
    if not st.session_state["patients"]:
        st.warning("Vui lòng nạp dữ liệu bệnh nhân trước khi bắt đầu mô phỏng.")
    else:
        simulation_patients: List[Patient] = [clone_patient(p) for p in st.session_state["patients"]]
        if algorithm == "FCFS":
            patients_result, schedule = run_fcfs(simulation_patients)
        elif algorithm == "SJF":
            patients_result, schedule = run_sjf(simulation_patients)
        elif algorithm == "Priority (Non-preemptive)":
            patients_result, schedule = run_priority_nonpreemptive(
                simulation_patients,
                enable_aging=st.session_state["apply_aging"],
                aging_interval=st.session_state["aging_interval"],
                aging_step=st.session_state["aging_step"],
            )
        elif algorithm == "Priority (Preemptive)":
            patients_result, schedule = run_priority_preemptive(
                simulation_patients,
                enable_aging=st.session_state["apply_aging"],
                aging_interval=st.session_state["aging_interval"],
                aging_step=st.session_state["aging_step"],
            )
        else:
            patients_result, schedule = run_round_robin(simulation_patients, time_quantum)

        display_algorithm = algorithm
        if algorithm in ["Priority (Non-preemptive)", "Priority (Preemptive)"] and st.session_state["apply_aging"]:
            display_algorithm = f"{algorithm} + Aging"

        st.session_state["result"] = {
            "algorithm": display_algorithm,
            "patients": patients_result,
            "schedule": schedule,
            "time_quantum": time_quantum,
        }
        st.session_state["comparison_result"] = None

if st.button("So sánh tất cả thuật toán"):
    if not st.session_state["patients"]:
        st.warning("Vui lòng nạp dữ liệu bệnh nhân trước khi so sánh.")
    else:
        st.session_state["comparison_result"] = build_comparison_result(
            [clone_patient(p) for p in st.session_state["patients"]],
            time_quantum,
            st.session_state["apply_aging"],
            st.session_state["aging_interval"],
            st.session_state["aging_step"],
        )

render_step_by_step_ui(
    st.session_state["patients"],
    algorithm,
    time_quantum,
    st.session_state.get("apply_aging", False),
    st.session_state.get("aging_interval", 3),
    st.session_state.get("aging_step", 1),
)

result = st.session_state.get("result")

if result is not None:
    st.subheader(f"Kết quả mô phỏng: {result['algorithm']}")
    result_df = pd.DataFrame(
        [patient_to_row(patient) for patient in result["patients"]]
    )

    for col in COLUMN_NAMES.keys():
        if col not in result_df.columns:
            result_df[col] = None

    result_df = result_df[list(COLUMN_NAMES.keys())]

    result_df = result_df.rename(columns=COLUMN_NAMES)

    st.dataframe(result_df, use_container_width=True)

    gantt_fig = draw_gantt_chart(result["schedule"], title=f"Gantt chart - {result['algorithm']}")
    st.pyplot(gantt_fig)

    avg_wait, avg_turnaround, _ = calculate_metrics(result["patients"])
    col1, col2 = st.columns(2)
    col1.metric("Thời gian chờ trung bình", f"{avg_wait:.2f}")
    col2.metric("Thời gian hoàn thành trung bình", f"{avg_turnaround:.2f}")

comparison_result = st.session_state.get("comparison_result")
if comparison_result is not None:
    st.subheader("Bảng so sánh thuật toán")
    comparison_df = pd.DataFrame(comparison_result)
    comparison_df = comparison_df.set_index("algorithm")
    comparison_df = comparison_df[["avg_waiting", "avg_turnaround", "total_completion"]]
    comparison_df.columns = ["Average Waiting Time", "Average Turnaround Time", "Total Completion Time"]
    st.dataframe(comparison_df, use_container_width=True)

    wait_chart = pd.DataFrame(
        {"Average Waiting Time": [item["avg_waiting"] for item in comparison_result]},
        index=[item["algorithm"] for item in comparison_result],
    )
    turnaround_chart = pd.DataFrame(
        {"Average Turnaround Time": [item["avg_turnaround"] for item in comparison_result]},
        index=[item["algorithm"] for item in comparison_result],
    )

    col1, col2 = st.columns(2)
    with col1:
        st.caption("So sánh Waiting Time")
        st.bar_chart(wait_chart)
    with col2:
        st.caption("So sánh Turnaround Time")
        st.bar_chart(turnaround_chart)

    st.subheader("Gantt chart từng thuật toán")
    tabs = st.tabs([item["algorithm"] for item in comparison_result])
    for tab, item in zip(tabs, comparison_result):
        with tab:
            st.pyplot(draw_gantt_chart(item["schedule"], title=f"Gantt chart - {item['algorithm']}"))
else:
    if st.session_state.get("patients"):
        if result is None:
            st.info("Đã có dữ liệu bệnh nhân. Vui lòng bấm 'Bắt đầu mô phỏng' để xem kết quả.")
    else:
        st.info("Chưa có dữ liệu bệnh nhân. Bạn có thể bốc số ngẫu nhiên hoặc nhập tay rồi cập nhật.")