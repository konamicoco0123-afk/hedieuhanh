from typing import Dict, List
import io

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
    "state": "Trạng thái",
    "io_time_remaining": "I/O còn lại",
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

st.markdown(
    """
    <style>
    :root {
        --bg: #f2fbfb;
        --panel: rgba(255, 255, 255, 0.88);
        --panel-strong: #ffffff;
        --primary: #0e6c88;
        --primary-strong: #0b4f68;
        --secondary: #3aa6b4;
        --text: #15384b;
        --muted: #5b7686;
        --success: #eafaf2;
        --warning: #fff7db;
        --border: rgba(17, 87, 104, 0.12);
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #f3fbfb 0%, #eef7ff 100%);
        color: var(--text);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(233, 247, 250, 0.95), rgba(243, 251, 255, 0.95));
        border-right: 1px solid var(--border);
    }
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: var(--primary-strong);
        letter-spacing: 0.2px;
    }
    .subtle-text {
        color: var(--muted);
        font-size: 0.96rem;
        margin-top: -0.35rem;
        margin-bottom: 1rem;
    }
    div[data-testid="stMetric"] > div {
        background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(224, 244, 247, 0.9));
        border: 1px solid var(--border);
        border-radius: 16px;
        box-shadow: 0 6px 16px rgba(14, 108, 136, 0.08);
        padding: 0.8rem 1rem;
    }
    div.stButton > button {
        border: none;
        border-radius: 12px;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        color: white;
        font-weight: 600;
        padding: 0.55rem 1rem;
        box-shadow: 0 8px 20px rgba(14, 108, 136, 0.18);
    }
    div.stButton > button:hover {
        filter: brightness(1.04);
        box-shadow: 0 10px 24px rgba(14, 108, 136, 0.22);
    }
    [data-testid="stDataFrame"] .dataframe {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    .section-card {
        background: rgba(255,255,255,0.9);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 8px 24px rgba(16, 79, 96, 0.06);
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
    }
    .stTabs [role="tablist"] {
        gap: 0.5rem;
    }
    .stTabs [role="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 0.6rem 1rem;
        background: rgba(255,255,255,0.7);
        border: 1px solid var(--border);
    }
    .stTabs [role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(14,108,136,0.12), rgba(58,166,180,0.08));
        border-bottom: 2px solid var(--primary);
        color: var(--primary-strong);
    }
    .sidebar-title {
        color: var(--primary-strong);
        font-weight: 700;
        letter-spacing: 0.2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header logos (stable in layout) — use Streamlit images in columns so they remain visible
_logo_dir = Path(__file__).parent / "anh"
try:
    header_cols = st.columns([0.18, 0.82])
    with header_cols[0]:
        c1, c2 = st.columns([1, 1.2])
        try:
            c1.image(str(_logo_dir / "logodaihoc.png"), width=72, clamp=True, output_format="PNG")
        except Exception:
            pass
        try:
            c2.image(str(_logo_dir / "logobenhvien.png"), width=72, clamp=True, output_format="PNG")
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
st.session_state.setdefault("sim_speed_factor", 1.0)
st.session_state.setdefault("sim_last_changes", [])

st.title("Mô phỏng hệ thống bốc số phòng khám")
st.caption("Mô phỏng thuật toán lập lịch CPU – Hệ thống bốc số phòng khám")

# Define time_quantum at module level to avoid scope issues
time_quantum = 2

with st.sidebar:
    st.markdown("<div class='sidebar-title'>Dữ liệu</div>", unsafe_allow_html=True)
    st.session_state["patient_count"] = st.number_input(
        "Số lượng bệnh nhân",
        min_value=1,
        max_value=10,
        value=st.session_state["patient_count"],
        step=1,
        help="Số bệnh nhân cần tạo tự động.",
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
        st.session_state.pop("sim_state", None)
        st.rerun()

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

    st.markdown("<div class='sidebar-title'>Thuật toán</div>", unsafe_allow_html=True)
    algorithm = st.selectbox(
        "Chọn thuật toán",
        ["FCFS", "SJF", "Priority (Non-preemptive)", "Priority (Preemptive)", "Round Robin"],
        help="Thuật toán lập lịch CPU cần mô phỏng.",
    )
    if algorithm == "Round Robin":
        time_quantum = st.number_input("Quantum", min_value=1, value=2, step=1, help="Kích thước time quantum cho RR.")
    else:
        time_quantum = 2

    st.markdown("<div class='sidebar-title'>Aging</div>", unsafe_allow_html=True)
    st.session_state["apply_aging"] = st.checkbox(
        "Áp dụng Aging",
        value=st.session_state["apply_aging"],
        help="Tăng ưu tiên dần cho bệnh nhân đang chờ dài.",
    )
    st.session_state["aging_interval"] = st.number_input(
        "Khoảng Aging",
        min_value=1,
        value=st.session_state["aging_interval"],
        step=1,
        help="Chu kỳ tăng ưu tiên theo thời gian.",
    )
    st.session_state["aging_step"] = st.number_input(
        "Bước Aging",
        min_value=1,
        value=st.session_state["aging_step"],
        step=1,
        help="Mức tăng ưu tiên mỗi chu kỳ.",
    )

    st.markdown("<div class='sidebar-title'>Tốc độ mô phỏng</div>", unsafe_allow_html=True)
    st.session_state["sim_speed_factor"] = st.slider(
        "Tốc độ",
        min_value=0.25,
        max_value=5.0,
        value=st.session_state.get("sim_speed_factor", 1.0),
        step=0.25,
        help="Điều chỉnh tốc độ chạy từng bước.",
    )

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

DISPLAY_COLUMNS = list(COLUMN_NAMES.keys())

if st.session_state["patients"]:
    patient_df = pd.DataFrame([patient_to_row(patient) for patient in st.session_state["patients"]])
    for col in DISPLAY_COLUMNS:
        if col not in patient_df.columns:
            patient_df[col] = None
    patient_df = patient_df[DISPLAY_COLUMNS]
else:
    patient_df = pd.DataFrame(columns=DISPLAY_COLUMNS)

display_df = patient_df.rename(columns=COLUMN_NAMES)
disease_options = [d["disease"] for d in load_diseases()]

main_tabs = st.tabs(["Danh sách bệnh nhân + mô phỏng", "So sánh thuật toán", "Mô phỏng từng bước"])

with main_tabs[0]:
    st.markdown("<div class='section-card'><h3 style='margin-top:0'>Danh sách bệnh nhân</h3></div>", unsafe_allow_html=True)
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        key="patient_editor",
        on_change=update_priority,
        column_config={
            "Loại bệnh": st.column_config.SelectboxColumn("Loại bệnh", options=disease_options, required=True),
            "Mức ưu tiên": st.column_config.NumberColumn("Mức ưu tiên", disabled=True),
        },
    )

    if edited_df is not None and st.button("Cập nhật dữ liệu bệnh nhân", key="update_patients_btn"):
        updated_patients: List[Patient] = []
        validation_errors: List[str] = []
        reverse_column_names = {v: k for k, v in COLUMN_NAMES.items()}
        edited_df = edited_df.rename(columns=reverse_column_names)
        for idx, row in edited_df.iterrows():
            try:
                pid = int(row["id"])
                arrival = int(row["arrival_time"])
                burst = int(row["burst_time"])
                priority = get_priority_by_disease(row["disease"])
                if arrival < 0 or burst <= 0:
                    raise ValueError
                updated_patients.append(
                    Patient(
                        id=pid,
                        arrival_time=arrival,
                        burst_time=burst,
                        priority=priority,
                        disease=row["disease"],
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

    if st.button("Bắt đầu mô phỏng", key="start_sim_btn"):
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
            st.rerun()

    result = st.session_state.get("result")
    if result is not None:
        st.markdown("<div class='section-card'><h3 style='margin-top:0'>Kết quả mô phỏng</h3></div>", unsafe_allow_html=True)
        result_df = pd.DataFrame([patient_to_row(patient) for patient in result["patients"]])
        for col in COLUMN_NAMES.keys():
            if col not in result_df.columns:
                result_df[col] = None
        result_df = result_df[list(COLUMN_NAMES.keys())].rename(columns=COLUMN_NAMES)

        csv_bytes = result_df.to_csv(index=False, encoding="utf-8").encode("utf-8")
        gantt_fig = draw_gantt_chart(result["schedule"], title=f"Gantt chart - {result['algorithm']}")
        png_buffer = io.BytesIO()
        gantt_fig.savefig(png_buffer, format="png", bbox_inches="tight")
        png_buffer.seek(0)

        col_export_1, col_export_2 = st.columns(2)
        with col_export_1:
            st.download_button(
                label="Tải CSV kết quả bệnh nhân",
                data=csv_bytes,
                file_name="ketqua_benhnhan.csv",
                mime="text/csv",
            )
        with col_export_2:
            st.download_button(
                label="Tải ảnh Gantt (PNG)",
                data=png_buffer,
                file_name="gantt_chart.png",
                mime="image/png",
            )

        st.dataframe(result_df, use_container_width=True)
        st.pyplot(gantt_fig)

        avg_wait, avg_turnaround, _ = calculate_metrics(result["patients"])
        metric_cols = st.columns(2)
        metric_cols[0].metric("Avg Waiting", f"{avg_wait:.2f}")
        metric_cols[1].metric("Avg TAT", f"{avg_turnaround:.2f}")
        st.caption("Batch = thuật toán thuần; Step-by-step có thêm trạng thái WAITING khi burst ≥ 5.")
    elif st.session_state.get("patients"):
        st.info("Đã có dữ liệu bệnh nhân. Vui lòng bấm 'Bắt đầu mô phỏng' để xem kết quả.")
    else:
        st.info("Chưa có dữ liệu. Hãy bốc số ngẫu nhiên hoặc khởi tạo nhập tay.")

with main_tabs[1]:
    comparison_result = st.session_state.get("comparison_result")
    if comparison_result is not None:
        st.markdown("<div class='section-card'><h3 style='margin-top:0'>Bảng so sánh thuật toán</h3></div>", unsafe_allow_html=True)
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

        comp_cols = st.columns(2)
        with comp_cols[0]:
            st.caption("So sánh Waiting Time")
            st.bar_chart(wait_chart)
        with comp_cols[1]:
            st.caption("So sánh Turnaround Time")
            st.bar_chart(turnaround_chart)

        st.subheader("Gantt chart từng thuật toán")
        comparison_tabs = st.tabs([item["algorithm"] for item in comparison_result])
        for tab, item in zip(comparison_tabs, comparison_result):
            with tab:
                st.pyplot(draw_gantt_chart(item["schedule"], title=f"Gantt chart - {item['algorithm']}"))
    else:
        if st.session_state.get("patients"):
            st.info("Chưa có kết quả so sánh. Hãy nhấn 'So sánh tất cả thuật toán' ở sidebar để xem báo cáo.")
        else:
            st.info("Chưa có dữ liệu bệnh nhân để so sánh.")

with main_tabs[2]:
    render_step_by_step_ui(
        st.session_state["patients"],
        algorithm,
        time_quantum,
        st.session_state.get("apply_aging", False),
        st.session_state.get("aging_interval", 3),
        st.session_state.get("aging_step", 1),
    )
