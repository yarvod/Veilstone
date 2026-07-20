# cython: boundscheck=False, wraparound=False, cdivision=True, language_level=3

cpdef list greedy_rectangles(int[:, ::1] signatures, int[:, ::1] faces):
    cdef Py_ssize_t rows = signatures.shape[0]
    cdef Py_ssize_t columns = signatures.shape[1]
    cdef Py_ssize_t u, v, width, height, row, column
    cdef int signature, face_index
    cdef bint matches
    cdef list rectangles = []

    for v in range(rows):
        u = 0
        while u < columns:
            signature = signatures[v, u]
            if signature < 0:
                u += 1
                continue

            width = 1
            while u + width < columns and signatures[v, u + width] == signature:
                width += 1

            height = 1
            while v + height < rows:
                matches = True
                for column in range(u, u + width):
                    if signatures[v + height, column] != signature:
                        matches = False
                        break
                if not matches:
                    break
                height += 1

            face_index = faces[v, u]
            for row in range(v, v + height):
                for column in range(u, u + width):
                    signatures[row, column] = -1
            rectangles.append((u, v, width, height, face_index))
            u += width

    return rectangles
