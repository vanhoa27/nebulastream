#!/usr/bin/env .venv/bin/python3

import argparse
import os
import struct
import brotli
import shutil
from pathlib import Path
import tempfile
import capnp
import io
import rr_trace_capnp

def find_trace_files(input_dir):
    "find all relevant files in the input trace directory"
    result = {
        'data': None,
        'events': None, 
        'mmaps': None,
        'tasks': None, 
        'mmap_hardlink': None, 
        'version': None,
    }

    for root, _, files in os.walk(input_dir):
        for filename in files:
            full_path = os.path.join(root, filename)

            if filename == "data":
                result['data'] = full_path
            elif filename == "events":
                result['events'] = full_path
            elif filename == "mmaps":
                result['mmaps'] = full_path
            elif filename == "tasks":
                result['tasks'] = full_path
            elif filename == "version":
                result['version'] = full_path
            elif filename.startswith("mmap_hardlink"):
                result['mmap_hardlink'] = full_path

    # Validate required files
    required = ['data', 'events', 'mmaps', 'tasks', 'mmap_hardlink']
    for req in required:
        if result[req] is None:
            raise FileNotFoundError(f"Required file '{req}' not found in {input_dir}")
    
    return result

def decompress_to_memory(file_path):
    """Decompress a brotli-compressed trace file into memory

    Returns raw bytes (all blocks are concatenated)
    """
    result = b""

    with open(file_path, "rb") as f:
        block_idx = 0
        while True:
            # Read block header
            header = f.read(8)
            if not header:
                break # EOF
            
            compressed_len, uncompressed_len = struct.unpack("<II", header)
            compressed_data = f.read(compressed_len)

            data = brotli.decompress(compressed_data)

            if len(data) != uncompressed_len:
                raise ValueError(
                    f"Corruption detected in {file_path} at block {block_idx}: "
                    f"expected {uncompressed_len} bytes, got {len(data)} bytes"
                )

            result += data
            block_idx += 1

    return result 

def recompress_and_write(data, output_path):
    """Compress data with bortli and prefix with 8 bit block header
    """
    uncompressed_len = len(data)

    compressed_data = brotli.compress(data, quality=5)
    compressed_len = len(compressed_data)

    header = struct.pack("<II", compressed_len, uncompressed_len)

    with open(output_path, "wb") as f:
        f.write(header)
        f.write(compressed_data)

    return compressed_len, uncompressed_len


def trim_frames(events_bytes, num_to_delete):
    """Remove first N frames from events data."""
    result = b''
    counter = 0
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
        tmp.write(events_bytes)
        tmp_path = tmp.name
    
    try:
        # Read and process
        with open(tmp_path, 'rb') as f:
            frames = rr_trace_capnp.Frame.read_multiple_packed(f)
            for frame in frames:
                counter += 1
                if counter > num_to_delete:
                    result += frame.as_builder().to_bytes_packed()
        
        return result
    finally:
        os.unlink(tmp_path)

def trim_mmaps(mmaps_bytes, num_to_delete):
    """Adjust frameTime in mmaps and remove early ones."""
    result = b''
    
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
        tmp.write(mmaps_bytes)
        tmp_path = tmp.name
    
    try:
        with open(tmp_path, 'rb') as f:
            mmaps = rr_trace_capnp.MMap.read_multiple_packed(f)
            for mmap in mmaps:
                new_mmap = mmap.as_builder()
                new_mmap.frameTime -= num_to_delete
                
                if new_mmap.frameTime >= 1:
                    result += new_mmap.to_bytes_packed()
        
        return result
    finally:
        os.unlink(tmp_path)

def trim_tasks(tasks_bytes, num_to_delete):
    """Adjust frameTime in tasks."""
    result = b''
    
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
        tmp.write(tasks_bytes)
        tmp_path = tmp.name
    
    try:
        with open(tmp_path, 'rb') as f:
            tasks = rr_trace_capnp.TaskEvent.read_multiple_packed(f)
            for task in tasks:
                new_task = task.as_builder()
                new_task.frameTime -= num_to_delete
                
                if new_task.frameTime >= 1:
                    result += new_task.to_bytes_packed()
        
        return result
    finally:
        os.unlink(tmp_path)

def main():
    parser = argparse.ArgumentParser("Trim rr trace")

    parser.add_argument(
        "input_dir",
        nargs = "?",
        default = "data/rr_traces/main-0",
        help = "Input trace directory" 
    )

    parser.add_argument(
        "output_dir",
        nargs = "?",
        default = "data/rr_traces/trimmed-trace",
        help = "Output trimmed trace directory" 
    )

    parser.add_argument(
        "--verbose", "-v",
        action = "store_true",
        help = "Enable verbose output"
    )

    parser.add_argument(
        "--delete-first",
        type=int,
        default=0,
        help="Number of events to delete from beginning"
    )

    args = parser.parse_args()


    trace_files = find_trace_files(args.input_dir)


    if args.verbose:
        print("Decompression:")

    decompressed = {}
    for file_type in ['tasks', 'events', 'mmaps', 'data']:
        decompressed[file_type] = decompress_to_memory(trace_files[file_type])

        if args.verbose:
            print(f" {file_type}: uncompressed to {len(decompressed[file_type])} bytes")

    # Trim Trace
    decompressed['data'] = decompressed['data'][1134618:]
    decompressed['events'] = trim_frames(decompressed['events'], args.delete_first)
    decompressed['tasks'] = trim_tasks(decompressed['tasks'], args.delete_first)
    decompressed['mmaps'] = trim_mmaps(decompressed['mmaps'], args.delete_first)

    # create output directory if not already available
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print(f"\nCreated output directory: {output_dir}")

    if args.verbose:
        print("\nRecompressing files...")

    for file_type, data in decompressed.items():
        output_path = output_dir / file_type
        comp_len, uncomp_len = recompress_and_write(data, output_path)
        if args.verbose:
            print(f"  {file_type}: {uncomp_len} bytes -> {comp_len} bytes compressed")

    # Copy files that don't need processing
    if args.verbose:
        print("\nCopying uncompressed files...")
    
    if trace_files['version']:
        shutil.copy2(trace_files['version'], output_dir / 'version')
        if args.verbose:
            print(f"  Copied version")

    if trace_files['mmap_hardlink']:
        mmap_filename = os.path.basename(trace_files['mmap_hardlink'])
        mmap_output = output_dir / mmap_filename

        # Remove if exists
        if mmap_output.exists():
            mmap_output.unlink()

        # Create hardlink (preserves inode)
        os.link(trace_files['mmap_hardlink'], mmap_output)

        if args.verbose:
            print(f"  Hardlinked {mmap_filename}")   


if __name__ == "__main__":
    main()
