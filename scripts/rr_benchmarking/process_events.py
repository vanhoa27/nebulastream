#!/usr/bin/env python3

import os
import capnp 

import rr_trace_capnp

NUMBER_OF_EVENT_DELETIONS = 13

def printFrame(file):
    Frames = rr_trace_capnp.Frame.read_multiple_packed(file)

    counter = 0

    for frame in Frames:
        if frame.event.which() == "syscall" and frame.event.syscall.number == 1:
            counter += 1

    print(counter)
    # for frame in Frames: 
    #     print(frame)

def writeFrame(file):
    # Frames = rr_trace_capnp.Frame.read_multiple_packed(file)
    Frames = rr_trace_capnp.Frame.read_multiple_packed(file)

    with open('events_trimmed.bin', 'wb') as f:
        counter = 0
        for frame in Frames:
            # if frame.event.which() == "syscall" and frame.event.syscall.number == 1:
            counter += 1

            if counter > NUMBER_OF_EVENT_DELETIONS:
                new_frame = frame.as_builder()
                new_frame.write_packed(f)
    f.close()

def writeMMap(file):
    MMaps = rr_trace_capnp.MMap.read_multiple_packed(file)

    with open('mmaps_trimmed.bin', 'wb') as f:
        for mmap in MMaps:
            new_mmap = mmap.as_builder()
            new_mmap.frameTime -= NUMBER_OF_EVENT_DELETIONS

            if new_mmap.frameTime >= 0:
                new_mmap.write_packed(f)
    f.close()

def writeTaskEvent(file):
    TaskEvents = rr_trace_capnp.TaskEvent.read_multiple_packed(file)

    with open('tasks_trimmed.bin', 'wb') as f:
        for taskevent in TaskEvents:
            new_taskevent = taskevent.as_builder()
            new_taskevent.frameTime -= NUMBER_OF_EVENT_DELETIONS

            if new_taskevent.frameTime >= 0:
                new_taskevent.write_packed(f)

if __name__ == '__main__':
    with open('events.bin', 'rb') as f:
        writeFrame(f)
        f.close()

    with open('mmaps.bin', 'rb') as f:
        writeMMap(f)
        f.close()

    with open('tasks.bin', 'rb') as f:
        writeTaskEvent(f)
        f.close()
