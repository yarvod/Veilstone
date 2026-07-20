# cython: boundscheck=False, wraparound=False, cdivision=True, language_level=3

import numpy as np


cpdef object propagate_light(
    const unsigned char[:, :, ::1] sources,
    const unsigned char[:, :, ::1] opaque,
):
    cdef Py_ssize_t width = sources.shape[0]
    cdef Py_ssize_t height = sources.shape[1]
    cdef Py_ssize_t depth = sources.shape[2]
    cdef Py_ssize_t x, y, z, position, flat, remainder
    cdef unsigned char level, candidate
    cdef object output = np.array(sources, dtype=np.uint8, copy=True, order="C")
    cdef unsigned char[:, :, ::1] light = output
    cdef list buckets = [[] for _ in range(16)]
    cdef list bucket

    for x in range(width):
        for y in range(height):
            for z in range(depth):
                level = light[x, y, z]
                if level > 0:
                    buckets[level].append((x * height + y) * depth + z)

    for level in range(15, 1, -1):
        candidate = level - 1
        bucket = buckets[level]
        for position in range(len(bucket)):
            flat = bucket[position]
            x = flat // (height * depth)
            remainder = flat - x * height * depth
            y = remainder // depth
            z = remainder - y * depth
            if light[x, y, z] != level:
                continue

            if x > 0 and not (opaque[x - 1, y, z] and sources[x - 1, y, z] == 0):
                if light[x - 1, y, z] < candidate:
                    light[x - 1, y, z] = candidate
                    buckets[candidate].append(flat - height * depth)
            if x + 1 < width and not (
                opaque[x + 1, y, z] and sources[x + 1, y, z] == 0
            ):
                if light[x + 1, y, z] < candidate:
                    light[x + 1, y, z] = candidate
                    buckets[candidate].append(flat + height * depth)
            if y > 0 and not (opaque[x, y - 1, z] and sources[x, y - 1, z] == 0):
                if light[x, y - 1, z] < candidate:
                    light[x, y - 1, z] = candidate
                    buckets[candidate].append(flat - depth)
            if y + 1 < height and not (
                opaque[x, y + 1, z] and sources[x, y + 1, z] == 0
            ):
                if light[x, y + 1, z] < candidate:
                    light[x, y + 1, z] = candidate
                    buckets[candidate].append(flat + depth)
            if z > 0 and not (opaque[x, y, z - 1] and sources[x, y, z - 1] == 0):
                if light[x, y, z - 1] < candidate:
                    light[x, y, z - 1] = candidate
                    buckets[candidate].append(flat - 1)
            if z + 1 < depth and not (
                opaque[x, y, z + 1] and sources[x, y, z + 1] == 0
            ):
                if light[x, y, z + 1] < candidate:
                    light[x, y, z + 1] = candidate
                    buckets[candidate].append(flat + 1)

    return output
