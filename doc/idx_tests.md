# Indexed Addressing Tests

Test        | Feature
------------|--------------------
idx1        | EA = 16-bit address
idx1        | ,R+
idx5        | ,R++
idx1        | ,-R
idx5        | ,--R
idx1        | ,R + 8-bit offset
idx6        | ,R + 16-bit offset - Failing now because of bad encoding (?)
idx1        | ,R
--          | DP - Needs psh/pul first
idx2        | ,R + A
idx2        | ,R + B
idx_regoff  | ,R + X
idx_regoff  | ,R + Y
idx_regoff  | ,R + U
idx_regoff  | ,R + S
idx4        | ,R + D
idx_regoff  | ,R + D
idx4        | indirect
idx_regoff  | indirect register offset
idx1        | X
idx1        | Y
idx3        | U
idx3        | S
idx7        | PC - Failing because of bad encoding (?)
