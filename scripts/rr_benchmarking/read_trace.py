#!/usr/bin/env python3

import struct, brotli, sys

def extract_uncompressed(path, out_path):
    with open(path, "rb") as f, open(out_path, "wb") as out_f:
        block_idx = 0
        while True:
            header = f.read(8)
            if not header:  # EOF
                break
            compressed_len, uncompressed_len = struct.unpack("<II", header)
            compressed = f.read(compressed_len)

            data = brotli.decompress(compressed)
            if len(data) != uncompressed_len:
                print(f"Block {block_idx}: size mismatch "
                      f"(expected {uncompressed_len}, got {len(data)})")
            else:
                print(f"Block {block_idx}: "
                      f"{compressed_len} bytes compressed => {uncompressed_len} bytes uncompressed")
            
            # Write uncompressed chunk to output file
            out_f.write(data)
            block_idx += 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <tracefile> <outfile>")
        sys.exit(1)
    extract_uncompressed(sys.argv[1], sys.argv[2])
