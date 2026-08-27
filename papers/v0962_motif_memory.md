# V0.96.2 Motif Memory

V0.96.2 introduces a small motif-memory layer for phrase generation. A primary motif is created at phrase start and stored with role metadata. Later measures retrieve the primary motif or a role-specific variant and develop it through repeat, sequence up/down, answer phrase, interval expansion/contraction, fragmentation, style color, or cadential variant.

The memory report records primary motif, recurrence count, variation types, exact repetition count, developed repetition count, motif identity score, and mechanical repetition penalty. The goal is not maximum novelty; it is recognizable identity without exact copy-paste.

Candidate ranking can use this report to reward developed repetition and penalize template-like looping. The V0.96.2 evaluation also computes final-score fingerprints from right-hand intervals to confirm that motif behavior appears in the actual score.
