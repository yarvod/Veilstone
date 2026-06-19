# Known Bugs & Issues

## Resolved

### BUG-001: Player cannot swim in water ✅
- **Fixed:** buoyancy + swim_speed + in_water state added to PlayerController

### BUG-002: Cannot break blocks through water ✅
- **Fixed:** raycast now skips fluid blocks

### BUG-003: Water has no flow physics ✅
- **Fixed:** drain logic removes flowing water without source; horizontal spread decay

### BUG-004: Mobs get stuck in water and jitter ✅
- **Fixed:** smooth buoyancy with lerp; mobs surface correctly

### BUG-005: Mobs spawn inside solid blocks ✅
- **Fixed:** 2-block clearance check in spawn validation

### BUG-006: Zombie attacks through height ✅
- **Fixed:** abs(dy) <= 2.0 check in melee damage calculation

### BUG-007: Zombie attack has no animation ✅
- **Fixed:** state_phase resets on each hit for visual feedback

### BUG-008: Mob AI cannot navigate around obstacles ✅
- **Fixed:** 45°/90° turn attempt before reversing direction

### BUG-R001: Font crash on Windows ✅
- **Fixed in:** commit 501e26e

### BUG-R002: World selection buttons broken ✅
- **Fixed in:** commit 501e26e

### BUG-R003: Chunk lighting seams ✅
- **Fixed in:** commit 501e26e
