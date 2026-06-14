# Next steps

Phase 18 packaging is complete across native Windows, macOS, and Linux CI. Phase 19 audio
foundation is next.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Define audio backend and event bus boundaries without coupling gameplay to pyglet.
2. Add sound/music registries and volume groups.
3. Route block, footstep, mob, ambience, and music events.
4. Add audio settings UI and NullAudioBackend integration coverage.
