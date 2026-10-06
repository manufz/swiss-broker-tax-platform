# eCH XML schemas

These unmodified schemas were copied from the `specs/` directory of
https://github.com/vroonhof/opensteuerauszug/tree/eeb3b3d790c5ba9c8cd2e256d228d0bae62ec572/specs
to match the engine commit pinned in `uv.lock`.

`eCH-0196-2-2.xsd` imports the four other schemas. The engine resolves
those imports locally, so validation requires no network access.

The API runs the engine from the project root and rejects processing if any
schema is missing. Docker includes this directory at `/app/specs`.
When updating the engine, review the schemas and validation tests together.

XSD validation checks XML structure and types. It does not establish that tax
calculations are correct or that a statement is accepted by a tax authority.
