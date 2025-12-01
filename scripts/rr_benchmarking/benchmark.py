#!/usr/bin/env python3
import subprocess
import time
import os
import csv
import argparse
from pathlib import Path

# Configuration
SIZES_MB = [1/65536, 1, 2, 4, 8, 16, 32, 64, 128, 256] # 128 256 512
REPS = 5
WORKER_BIN = "./cmake-build-debug/nes-single-node-worker/nes-single-node-worker"
NEBULI_BIN = "./cmake-build-debug/nes-nebuli/nes-nebuli"

MODES = {
    "native": [WORKER_BIN],
    "rr": ["rr", "record", WORKER_BIN],
    "udb": ["undo", "record", WORKER_BIN],
}

QUERIES = {
    "selection": "SELECT * FROM source WHERE y < UINT64(100) INTO sink",
    "aggregation_tumbling": """
    SELECT COUNT(y) AS count_y, AVG(y) AS avg_y
    FROM source
    WINDOW TUMBLING(x, SIZE 100 MS)
    INTO sink
    """,
    "aggregation_sliding": """
    SELECT COUNT(y) AS count_y, AVG(y) AS avg_y
    FROM source
    WINDOW SLIDING(x, SIZE 100 MS, ADVANCE BY 20 MS)
    INTO sink
    """,
    "join": """
    SELECT stream1.id1 AS id,
           stream1.value1 AS value1,
           stream1.timestamp AS timestamp
    FROM (SELECT * FROM stream1)
    INNER JOIN 
    (SELECT * FROM stream2)
    ON (id1 = id2 and value1 = value2)
    WINDOW TUMBLING(timestamp, SIZE 100 MS)
    INTO sink
    """
}

def load_template(query_mode):
    """Load the appropriate YAML template for the given query mode."""
    template_path = f"scripts/templates/query_{query_mode}_template.yaml"
    
    # Fallback to generic template if specific one doesn't exist
    if not Path(template_path).exists():
        template_path = "scripts/templates/query_template.yaml"
        if not Path(template_path).exists():
            # Create a basic template if none exists
            return create_basic_template()
    
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Template {template_path} not found, using basic template")
        return create_basic_template()

def create_basic_template():
    """Create a basic YAML template that works for most query types."""
    return """query: |
  {query_type}

sinks:
  - name: sink
    type: File
    schema:
      - name: count_y
        type: UINT64
      - name: avg_y
        type: UINT64
    config:
      input_format: CSV
      file_path: "result.csv"
      append: false

logical:
  - name: source
    schema:
      - name: x
        type: UINT64
      - name: y
        type: UINT64

physical:
  - logical: source
    type: Generator
    parser_config:
      type: CSV
    source_config:
      stop_generator_when_sequence_finishes: ALL
      max_runtime_ms: 1000000
      seed: 1
      generator_schema: |
        SEQUENCE UINT64 0 {rows} 1
        SEQUENCE UINT64 0 100 1
"""

def run_test(mode_cmd, query_type, size_mb, query_mode):
    """Run a single test with the given parameters."""
    # Clean up any existing result file
    if os.path.exists("result.csv"):
        os.remove("result.csv")

    # Start the worker process
    worker = subprocess.Popen(
        mode_cmd, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)  # Give worker time to start
    
    try:
        # Load and prepare the query template
        template = load_template(query_mode)
        rows = int(size_mb * 65536)
        
        query_content = template.format(rows=rows, query_type=query_type.strip())
        
        # Write query to temporary file
        with open("query.yaml", "w") as f:
            f.write(query_content)
        
        # Run the benchmark
        start = time.time()

        subprocess.run([
            NEBULI_BIN, "-w", "--server", "127.0.0.1:8080", 
            "register", "-i", "query.yaml", "-x"
        ], check=True)

        end = time.time()
        
        return end - start
        
    finally:
        # Clean up
        worker.terminate()
        worker.wait()
        
        if os.path.exists("query.yaml"):
            os.remove("query.yaml")

def main():
    parser = argparse.ArgumentParser(description="Benchmark NES queries")
    parser.add_argument(
        "--query-mode", 
        choices=QUERIES.keys(), 
        required=True,
        help="Type of query to benchmark"
    )
    parser.add_argument(
        "--output", 
        default="bench_results.csv",
        help="Output CSV file for results"
    )
    parser.add_argument(
        "--sizes", 
        nargs="+", 
        type=float,
        default=SIZES_MB,
        help="Data sizes in MB to test"
    )
    parser.add_argument(
        "--reps", 
        type=int, 
        default=REPS,
        help="Number of repetitions per test"
    )
    parser.add_argument(
        "--modes", 
        nargs="+",
        choices=MODES.keys(),
        default=list(MODES.keys()),
        help="Execution modes to test"
    )
    
    args = parser.parse_args()
    
    query_type = QUERIES[args.query_mode]
    results_file = f"{args.query_mode}_{args.output}"
    
    print(f"Running {args.query_mode} benchmark...")
    print(f"Query: {query_type.strip()}")
    print(f"Results will be saved to: {results_file}")
    
    with open(results_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["mode", "size_mb", "rep", "time_seconds"])
        
        for mode_name in args.modes:
            if mode_name not in MODES:
                print(f"Warning: Unknown mode '{mode_name}', skipping")
                continue
                
            mode_cmd = MODES[mode_name]
            print(f"\nTesting {mode_name} mode...")
            
            for size_mb in args.sizes:
                print(f"  Size: {size_mb}MB")
                
                for rep in range(args.reps):
                    print(f"    Rep {rep+1}/{args.reps}")
                    
                    try:
                        time_taken = run_test(mode_cmd, query_type, size_mb, args.query_mode)
                        writer.writerow([mode_name, size_mb, rep+1, time_taken])
                        print(f"    Time: {time_taken:.2f}s")
                    except Exception as e:
                        print(f"    Error: {e}")
                        # Write error row with -1 to indicate failure
                        writer.writerow([mode_name, size_mb, rep+1, -1])
                    
                    time.sleep(1)  # Brief pause between runs
    
    print(f"\nDone! Results saved to {results_file}")

if __name__ == "__main__":
    main()
