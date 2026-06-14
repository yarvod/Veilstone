# Next steps

Phase 17 UI polish and settings is complete. Phase 18 packaging is next.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Define distributable application metadata and version reporting.
2. Add packaged resource verification for shaders, templates, and configuration defaults.
3. Add macOS launch/build instructions and a clean virtual-environment smoke script.
4. Build wheel and source distribution in CI-style verification.
5. Verify the installed `voxel` console entry point outside the repository.
6. Add save/config directory migration hooks for packaged releases.
7. Add release notes and a reproducible release checklist.
8. Run the full quality gate from the built wheel.
