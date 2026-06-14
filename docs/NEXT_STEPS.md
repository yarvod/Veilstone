# Next steps

Phase 15 shadow and shader polish is complete. Phase 16 structures and world richness is next.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Define a versioned structure template schema with block palette and local coordinates.
2. Add strict TOML/JSON structure loading and validation.
3. Add deterministic region-based structure placement from the world seed.
4. Check terrain footprint, slope, and replaceability before placement.
5. Add data-driven structure loot tables.
6. Implement an original ruin template and an original camp template.
7. Add resource cave features and a rare long-distance landmark.
8. Add a debug structure viewer/placement command.
9. Add golden tests for deterministic placement and template compatibility.
10. Run worldgen/streaming benchmarks and the full quality gate.
