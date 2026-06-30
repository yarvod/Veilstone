# Resource Pack Support

Veilstone supports a focused Minecraft Java-style resource-pack subset.

## Supported

- Folder or ZIP packs with `pack.mcmeta`.
- Bundled `resource_packs/default` folder uses the same Java-style layout as
  user packs and is the fallback source for missing supported block textures.
- Block texture resource locations such as `minecraft:block/stone`.
- Entity texture resource locations such as `minecraft:entity/cow/cow`,
  `minecraft:entity/zombie/zombie`, and `minecraft:entity/player/player`.
- Sound resource locations such as `minecraft:ui/click`,
  `minecraft:player/hurt`, `minecraft:entity/cow/hurt_1`, and
  `minecraft:music/exploration`.
- New gameplay textures and sounds belong under
  `resource_packs/default/assets/<namespace>/textures|sounds/...`; root
  `assets/` is reserved for non-resource-pack files such as app branding.
- Runtime apply through `/resourcepack <path>` and the Settings texture-pack UI.
- Atlas cache reuse under the save cache root for user packs.
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
