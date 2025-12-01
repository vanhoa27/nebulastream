#!/usr/bin/env python3

import csv
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

WORKLOAD_SIZES_MB = [1/65536, 1, 2, 4, 8, 16, 32, 64, 128, 256]

def bytes_to_mb(bytes_val):
    """Convert bytes to megabytes"""
    return bytes_val / (1024 * 1024)

def create_comparison_plot(trace_type_1, data_1_mb, trace_type_2, data_2_mb, output_file):
    """
    Compare normalized growth of two trace components
    """
    plt.figure(figsize=(10, 6))
    
    # Normalize both to start at 1.0
    # data_1_mb = [x / data_1_mb[0] for x in data_1_mb]
    # data_2_mb = [x / data_2_mb[0] for x in data_2_mb]
    
    plt.plot(WORKLOAD_SIZES_MB, data_1_mb, 
             marker='o', linewidth=2, markersize=8, label=f'{trace_type_1} (normalized)')
    plt.plot(WORKLOAD_SIZES_MB, data_2_mb, 
             marker='s', linewidth=2, markersize=8, label=f'{trace_type_2} (normalized)')
    
    plt.xlabel('Workload Size (MiB)', fontsize=12)
    plt.ylabel('Growth Factor (relative to smallest workload)', fontsize=12)
    plt.title(f'{trace_type_1} vs {trace_type_2} Growth Rate Comparison', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ylim(0, max(max(data_1_mb), max(data_2_mb)) * 1.1)
    plt.tight_layout()
    
    ouput_dir = Path("plots")
    ouput_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(ouput_dir / output_file, dpi=300)
    plt.show()

def create_plot(trace_type_name, output_plot_file, collected_data_mb):
    plt.figure(figsize=(10, 6))
    plt.plot(WORKLOAD_SIZES_MB, collected_data_mb, marker='o', linewidth=2, markersize=8)
    
    plt.xlabel('Workload Size (MiB)', fontsize=12)
    plt.ylabel('Total Trace Size (MiB)', fontsize=12)
    plt.title(f"RR Trace {trace_type_name} Size vs Workload Size", fontsize=14)
    plt.grid(True, alpha=0.3)

    plt.ylim(0, max(collected_data_mb) * 1.05)
    
    # plt.tight_layout()
    ouput_dir = Path("plots")
    ouput_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(ouput_dir / output_plot_file, dpi=300)
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate plots for rr traces'
    )

    parser.add_argument(
        "csvfile_name",
        nargs="?",
        default="trace_size.csv",
    )

    args = parser.parse_args()

    csvfile_name = args.csvfile_name 
    
    # Read and parse CSV
    fields = ["data", "events", "mmap_hardlink", "mmaps", "tasks"]
    trace_records = {field: [] for field in fields }
    
    with open(csvfile_name, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in fields: 
                trace_records[field].append(bytes_to_mb(int(row[field])))

    total_sizes_mb = list(map(sum, zip(*trace_records.values()))) 
    
    # Create plots
    create_plot("total", "rr_total_trace.png", total_sizes_mb)
    create_plot("data", "rr_data_trace.png", trace_records["data"])
    create_plot("events", "rr_event_trace.png", trace_records["events"])
    create_plot("mmap_hardlink", "rr_mmap_hardlinks_trace.png", trace_records["mmap_hardlink"])
    create_plot("mmaps", "rr_mmaps_trace.png", trace_records["mmaps"])
    create_plot("tasks", "rr_tasks_trace.png", trace_records["tasks"])

    create_comparison_plot("data", trace_records["data"], 
                       "events", trace_records["events"],
                       "data_vs_events_comparison.png")

    # Print summary
    # print(f"Number of data points: {len(total_sizes_mb)}")
    # print(f"Workload sizes (MB): {WORKLOAD_SIZES_MB}")
    # print(f"Trace sizes (MB): {[f'{size:.2f}' for size in total_sizes_mb]}")

    plt.show()
    
