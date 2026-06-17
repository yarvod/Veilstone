# Twilight Forest (World Generation Upgrade)

This document tracks the backlog and phases for upgrading the world generator to implement a "Twilight Forest" style atmosphere, per the user's request.

## Goals

1. Modify chunk generation to include giant, canopy-dense trees.
2. Alter the day/night cycle to reflect permanent twilight (or adjust sky rendering and shaders).
3. Introduce specific biome features suited to the aesthetic.
4. Integrate new shaders, lighting, and ambient effects.

## Phases

### Phase 1: Preparation
- [x] Remove old post-processing logic to make way for new volumetric/color effects.
- [x] Define new tree structures in the generation rules (giant trees with thick trunks).
- [x] Implement `GiantTreeGenerator` alongside the current `TreeGenerator`.

### Phase 2: Terrain and Biome
- [x] Update heightmap algorithms in `worldgen.py` or equivalent generator logic to have flatter terrains with scattered large hills or dense forested areas.
- [x] Introduce a "Twilight" biome definition that overrides standard spawn parameters.
- [x] Update foliage color to reflect a magical, twilight atmosphere.

### Phase 3: Lighting and Atmosphere
- [x] Alter sky shader to lock the time of day to twilight (or modify the `day_cycle_seconds` / `time` uniforms).
- [x] Introduce magical or blue-ish ambient fog (via updated moonlight and sky colors).
- [x] Implement glowing/luminescent blocks (e.g., fireflies, glowing mushrooms) and update the lighting engine to handle them efficiently.

### Phase 4: Entities (Future)
- [ ] Implement custom Twilight Forest mobs.
- [ ] Add new crafting recipes and drops for magical foliage/wood.
