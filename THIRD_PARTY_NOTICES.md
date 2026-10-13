# Third-party notices

The project's MIT license covers the custom application, infrastructure, tests
and documentation. It does not replace dependency, font, schema or public-data
terms. Preserve this file and `licenses/` in source distributions and images.

| Component | Pinned source / attribution | Notice |
| --- | --- | --- |
| OpenSteuerAuszug tax engine and PDF renderer | [Johannes Gerardus Maria Vroonhof](https://github.com/vroonhof/opensteuerauszug/tree/eeb3b3d790c5ba9c8cd2e256d228d0bae62ec572) | [MIT](licenses/opensteuerauszug.txt) |
| PDF417-Py fork | [Ivan Habunek; Vroonhof fork](https://github.com/vroonhof/pdf417-py/tree/44ce800bf7301ea88aaabd2e1a680238c96fc4a9) | [MIT](licenses/pdf417-py.txt) |
| ibflex fork (`ibflex2`) | [Christopher Singley; Vroonhof fork](https://github.com/vroonhof/ibflex/tree/eaffc70b5a2b1e07ec3706857aa3d1c786edd92d) | [MIT](licenses/ibflex.txt) |
| Bitstream Vera font used by ReportLab | Bitstream / GNOME | [Font notice](licenses/bitstream-vera.txt) |
| eCH XML schemas | Verein eCH / Swiss Tax Conference; eCH-0196 author Christian Holzreiter (GFT); unmodified pinned copies | [Schema provenance](specs/README.md); section 5 of the [eCH-0196 standard](https://www.ech.ch/sites/default/files/dosvers/hauptdokument/STAN_d_DEF_2022-06-07_eCH-0196_V2.2.0_E-Steuerauszug_.pdf) describes use/distribution with author attribution |
| Official Kursliste reference data | Swiss Federal Tax Administration, ICTax | [Source and checksums](docs/kursliste-provenance.md) |

Other direct/transitive dependencies retain their own notices in installed
package metadata. The runtime image keeps this metadata. `uv.lock` records their
versions, source revisions and distribution hashes. Python, Debian and uv also
retain their upstream licensing terms; the project does not claim authorship of
them. Official Kursliste databases are downloaded separately and are excluded
from the repository and image.

The repository's custom work is the HTTP API and input checks, processing lifecycle
and concurrency control, barcode-capacity adapter, Azure infrastructure,
authentication integration, release/operations tooling and acceptance tests.
Tax importing, calculation, eCH models and the PDF renderer come from the engine.
