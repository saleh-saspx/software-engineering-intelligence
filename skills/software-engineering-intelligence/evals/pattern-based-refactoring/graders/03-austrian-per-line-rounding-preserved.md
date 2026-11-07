---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The refactored code keeps Austria's per-line rounding (each line's tax rounded half-up, then summed), and a test pins a case where per-line and whole-invoice rounding give different results (for example two lines of 0.13 at 20%, which must give 0.06).
