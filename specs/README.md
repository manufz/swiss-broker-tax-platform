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

The schemas remain attributed to Verein eCH and their authors. eCH-0196's
content responsibility is the Swiss Tax Conference; its listed author is
Christian Holzreiter (GFT). Section 5 of the
[official standard](https://www.ech.ch/sites/default/files/dosvers/hauptdokument/STAN_d_DEF_2022-06-07_eCH-0196_V2.2.0_E-Steuerauszug_.pdf)
describes reuse/distribution with attribution. The project's MIT license does
not relicense these schemas. See [third-party notices](../THIRD_PARTY_NOTICES.md).
