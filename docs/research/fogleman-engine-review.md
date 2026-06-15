# Fogleman Engine Reference Review

Reviewed references:

- <https://github.com/fogleman/Craft>
- <https://github.com/fogleman/Craft/blob/master/src/cube.c>
- <https://github.com/fogleman/Minecraft>

## Adopted Principles

- A box needs an intentional UV order per face. `Craft`'s cube data makes the face boundary,
  winding, normal, and texture orientation explicit; Veilstone now follows that principle in its
  own renderer and data format.
- Input and collision simulation should remain compact, deterministic, and independently tested.
- Chunk rendering should keep shared geometry/material work batched instead of binding a texture
  for every body face.

## Deliberately Not Copied

- No source, textures, sounds, models, names, or asset layouts were copied.
- The fixed-function OpenGL and older Pyglet architecture in the small Python reference is not a
  suitable replacement for the existing ModernGL, shader, ECS, and process-pool architecture.
- Craft's exact atlas coordinates and C vertex arrays are implementation-specific and were used
  only to confirm the general per-face orientation rule.

The resulting player/mob skins, audio, UV maps, shaders, tests, and runtime behavior are original
project assets and code.
