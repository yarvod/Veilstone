# Next steps

Phase 18 packaging is implemented and locally verified on macOS. Native Windows CI remains
before the phase-complete tag.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Run `.github/workflows/package.yml` on Windows and inspect the uploaded artifact.
2. Confirm first launch, shaders, process pools, and user-data paths on Windows.
3. Mark the Windows checklist item and tag `phase-18-complete`.
4. Begin Phase 19 only after the native packaging gate is green.
