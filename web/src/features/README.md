# Feature layout

Top-level product areas live under `src/features`. Keep each feature self-contained and expose only its public entrypoints through an `index.ts` file.

Suggested future feature folders:

- `equipment-planner` - current item/equipment planner and PoE item editor.
- `skill-tree-planner` - passive tree planning UI and domain logic.
- `gem-cutting-order` - gem/link/order planning tools.
- `music-channel` - music/channel-specific UI and flows.
- `games/diablo4-planner` - only when another game becomes substantial enough to justify its own area.

Shared generic UI, app shell, and cross-feature utilities should stay outside feature folders. Game-specific data rules should remain inside the owning feature until two features genuinely share them.
