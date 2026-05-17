# Equipment planner feature

This feature owns the current PoE equipment/item editor flow.

- `components/` - React UI for the feature.
- `components/item-editor/` - leaf UI pieces used by the editor modal.
- `components/debug-panels/` - legacy/developer data inspection panels kept inside the feature until they are removed or promoted to shared tooling.
- `domain/` - PoE item/equipment rules, item-local calculations, validation, text parsing, sockets, and defence logic.
- `hooks/` - stateful feature logic that should not live inside large React components.
- `index.ts` - public exports used by the rest of the app.

Keep imports from outside the feature pointed at `src/features/equipment-planner` instead of deep component paths where possible. Internal UI pieces may deep-import inside this feature, but shared app code should use the public barrel export.
