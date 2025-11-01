#!/usr/bin/env python3

import argparse, os, csv, glob
from pathlib import Path

# https://stackoverflow.com/questions/34339461/how-to-get-all-the-filename-and-filesize-in-current-directory-in-python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Parse the size of the resulting trace"
    )

    parser.add_argument(
        "trace_directory",
        nargs = "?",
        default = "rr_traces/",
        help = "trace directory"
    )

    parser.add_argument(
        "output_file",
        nargs = "?",
        default = "trace_size.csv",
        help = "output csv file"
    )

    args = parser.parse_args()

    trace_directory_path = Path(args.trace_directory)
    output_file = Path(args.output_file)
    
    # https://stackoverflow.com/questions/2225564/get-a-filtered-list-of-files-in-a-directory#2225582
    trace_dirs = glob.glob(f"{trace_directory_path}/nes-single*")

    trace_dirs.sort()

    # https://stackoverflow.com/questions/61781443/how-to-remove-a-substrings-from-a-list-of-strings
    # trace_dir_names = [x.split('/')[-1] for x in trace_dirs]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['data', 'events', 'mmap_hardlink', 'mmaps', 'tasks', 'version'])
        
        for trace_dir in trace_dirs:
            sizes = []
            for filename in ['data', 'events', 'mmap_hardlink', 'mmaps', 'tasks', 'version']:
                if filename == 'mmap_hardlink':
                    # Find all files starting with mmap_hardlink and sum their sizes
                    matching_files = glob.glob(os.path.join(trace_dir, 'mmap_hardlink*'))
                    total_size = sum(os.stat(f).st_size for f in matching_files)
                    sizes.append(total_size)
                else:
                    filepath = os.path.join(trace_dir, filename)
                    if os.path.exists(filepath):
                        sizes.append(os.stat(filepath).st_size)
                    else:
                        sizes.append(0)
            
            writer.writerow(sizes)
