# Repair Plan

This repair closes concrete gaps discovered in the V104.06-V104.17 and V105 artifacts without adding roadmap stages.

Rules:
- No V116/V117.
- No stage is declared production-live merely because code exists.
- External infrastructure is represented by real adapters and readiness gates; unavailable external services fail closed.
- Generic placeholder application/persistence modules are replaced by concrete bounded implementations.
