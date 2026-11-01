# Data quality and anomaly screening

Uploaded triangles are checked for square shape, unique labels, numeric finite observed cells, blank future cells, nonnegative nondecreasing cumulative claims, and positive development volumes.

For each development age, observed factors are compared with the age-specific median and median absolute deviation (MAD). Robust z-score = 0.6745 * (factor - median) / MAD. Absolute scores above 3.5 are flagged. At least four positive-paid pairs and nonzero MAD are required. Other pairs are unassessable, not normal.

Flags are prompts for actuarial review, not proof of errors or fraud. The tool never removes or modifies flagged observations. Portfolio shifts, inflation, large losses, and sparse triangles can distort this diagnostic. Exported CSV includes all assessed and unassessed pairs.
