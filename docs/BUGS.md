# Bug Registry

This file records current corrective work. Detailed completed phase history remains in
`docs/PROGRESS.md`.

| ID | Status | Symptom | Cause and resolution | Regression |
| --- | --- | --- | --- | --- |
| BUG-001 | Fixed | Mob faces appeared on side faces, upside down, or mirrored. | Replaced global cube UV order with explicit face UVs and corrected model yaw in both entity vertex shaders. | `test_entity_animation.py`, `test_shader_files.py` |
| BUG-002 | Fixed | Cow and zombie appeared to walk backward; grazing inverted the cow head. | Unified AI/model forward convention and corrected grazing pitch sign. | `test_mob_ai.py`, `test_entity_animation.py` |
| BUG-003 | Fixed | A key event could crash with an `int`/`NoneType` comparison. | Ignore key events without a symbol before numeric hotbar checks. | `test_application_smoke.py` |
| BUG-004 | Fixed | Player could jump back toward spawn or an old position without useful logs. | Removed reconciliation against delayed client-authored echo snapshots; invalid-coordinate recovery and death respawn now log explicit reasons and positions. | multiplayer integration suite |
| BUG-005 | Fixed | LAN clients did not reliably prove mutual player visibility. | Replicated yaw, retained per-player snapshots, and added a real two-window avatar test. | `test_remote_render_client.py` |
| BUG-006 | Fixed | Hitting a cow did not produce a physical or behavioral response. | Added source-relative knockback, vertical impulse, hurt state, and passive flee state. | `test_mob_ai.py` |
| BUG-007 | Fixed | HUD lacked health/hand feedback and showed duplicate FPS readouts. | Added hearts and hand/item sprites, hurt sound, and removed Pyglet's second FPS display. | `test_application_smoke.py`, `test_audio.py` |
| BUG-008 | Fixed | Windows menu text could overlap. | Centralized platform font selection and use Segoe UI on Windows; added menu render state correction for alpha blending and disabled depth testing during menu rendering. | `test_menu.py`, `test_application_smoke.py` |

## Known Limitations

- Mob navigation is local steering, not global pathfinding.
- Fluid propagation remains chunk-local.
- The first-person arm is a HUD presentation, not a world-space articulated player body.
