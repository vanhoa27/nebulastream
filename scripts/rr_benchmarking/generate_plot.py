#!/usr/bin/env python3

import pandas as pd 
import matplotlib.pyplot as plt

df = pd.read_csv("selection_bench_results.csv")

avg_times = df.groupby(["mode", "size_mb"]).mean().reset_index()

plt.figure(figsize=(10, 6))

for mode in avg_times["mode"].unique():
    mode_data = avg_times[avg_times["mode"] == mode]
    plt.plot(mode_data["size_mb"], mode_data["time_seconds"], marker="o", label=mode)

plt.xlabel("Input Size/Workload (MB)")
plt.ylabel("Runtime (seconds)")
plt.title("Runtime by Workload Size and Mode")
plt.legend()
plt.grid(True)

plt.savefig("performance_plot.png", dpi=300, bbox_inches="tight")
plt.show()
