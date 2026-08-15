# FORGE contracts

These JSON Schemas are the language-neutral API boundary between Inseon's control
plane and Joonghui's compiler workers. Python dataclasses in `src/forge/contracts`
are the executable implementation. Breaking changes require a new schema version;
never silently reinterpret units, coordinate frames, lineage, or simulation truth.
