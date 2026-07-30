import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from typing import Dict, List


def draw_gantt_chart(schedule: List[Dict[str, float]], title: str = "Biểu đồ Gantt mô phỏng khám bệnh") -> plt.Figure:
    """Vẽ Gantt chart với legend rõ ràng cho từng thuật toán."""
    fig, ax = plt.subplots(figsize=(10, 3))
    colors: Dict[int, str] = {}
    legend_handles: List[Patch] = []

    for segment in schedule:
        pid = segment["patient_id"]
        if pid not in colors:
            colors[pid] = f"C{pid % 10}"
            legend_handles.append(Patch(facecolor=colors[pid], label=f"BN{pid}"))
        ax.broken_barh(
            [(segment["start"], segment["duration"])],
            (0, 9),
            facecolors=colors[pid],
            edgecolor="black",
        )
        ax.text(
            segment["start"] + segment["duration"] / 2,
            4.5,
            f"BN{pid}",
            ha="center",
            va="center",
            color="white",
            fontsize=8,
        )

    ax.set_ylim(0, 10)
    ax.set_xlabel("Thời gian")
    ax.set_yticks([4.5])
    ax.set_yticklabels(["Bác sĩ"])
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.set_title(title)
    ax.legend(handles=legend_handles, bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    return fig
