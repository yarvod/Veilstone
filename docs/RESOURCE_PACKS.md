# Resource Pack Support

Veilstone supports a focused Minecraft Java-style block texture subset.

## Supported

- Folder or ZIP packs with `pack.mcmeta`.
- Block texture resource locations such as `minecraft:block/stone`.
- Runtime apply through `/resourcepack <path>` and the Settings texture-pack UI.
- Atlas cache reuse under the save cache root.
- Alpha-tested cutout blocks for leaf-style textures. Blocks marked with
  `render_layer = "cutout"` discard transparent atlas texels in the chunk shader.
- Faithful-style `oak_leaves.png` alpha is preserved through import.
- A transparent-foliage smoke scene is available through
  `voxel foliage-smoke-scene` for manual cutout/backdrop checks.

## Planned

- Translucent non-water block blending beyond alpha test.
- Minecraft item models and 3D inventory icons.
- Broader block-state model JSON support.
- More complete animated texture handling beyond first-frame fallback.
