# CHANGELOG


## Unreleased

### Chores

* chore: prepare packages to upload (#72) ([`2e95436`](https://github.com/akotyla/ragbits/commit/2e95436954644318adc968172fca1a1b95ea8a72))

* chore: add script to update package version (#29) ([`73992af`](https://github.com/akotyla/ragbits/commit/73992af5a79335a8cf8ecaf890f115bd44af3e9e))

* chore: add script for ragbits package creation (#24) ([`9439868`](https://github.com/akotyla/ragbits/commit/9439868c778788bdcef636133d7b343fb8da35a3))

* chore: switch to uv packaging (#12) ([`2f1ceac`](https://github.com/akotyla/ragbits/commit/2f1ceac23dbda84e39c6150c5faf8895b0c245c1))

* chore: rename project to ragbits (#8) ([`9082362`](https://github.com/akotyla/ragbits/commit/9082362f3cfbf8bbb33e3b610a92b6095cb63343))

* chore: setup github actions for CI ([`c6dc50c`](https://github.com/akotyla/ragbits/commit/c6dc50c9dd496a5e4fe8035ef8365891b41d4e76))

* chore: add issue templates ([`fd056b4`](https://github.com/akotyla/ragbits/commit/fd056b46829a71d32fd120e9846cb268c0df16bc))

* chore: use ragnarok as a project name ([`79ee174`](https://github.com/akotyla/ragbits/commit/79ee174329683770036b30d046fe05212513f60b))

* chore: fix loading formatters configuration ([`4c2e71c`](https://github.com/akotyla/ragbits/commit/4c2e71cbe732a789eda32d1dd282e954688df19c))

* chore: add GitLab CI and pre-commit ([`fe6e426`](https://github.com/akotyla/ragbits/commit/fe6e4269648e5782579f44ebc3f1d21c7b8e5ef2))

* chore: initial commit ([`ddf54eb`](https://github.com/akotyla/ragbits/commit/ddf54ebe29cb2d1fa2a851471831c27b6dc54047))

### Features

* feat(document-search): allow to use local instance of unstructured (#74) ([`a774147`](https://github.com/akotyla/ragbits/commit/a774147b03bde937a994200f2db3af11ede9e8fa))

* feat(prompt): allow typed arguments to add_few_shot (#67)

* feat(prompt): allow typed arguments to add_few_shot

* Introduce a FewShot example type alias ([`428c7a1`](https://github.com/akotyla/ragbits/commit/428c7a1c240c0c217ea1e226ec4594298a5be0ab))

* feat(document-search): async unstructured api (#37) ([`5398d20`](https://github.com/akotyla/ragbits/commit/5398d20676d15652d18b394321a440a3648d3524))

* feat(document-search): Implement document search public interface (#58) ([`abbcdb0`](https://github.com/akotyla/ragbits/commit/abbcdb0e094ef316c18104045f8341fbb56390f9))

* feat(prompts): Make the `Prompt` interface more clear in regard to messages (#59) ([`08acb63`](https://github.com/akotyla/ragbits/commit/08acb63884a70cd7d23eb00ba6fb789dfe84f0b3))

* feat(prompt-lab): Register a CLI command for Prompt Lab (#52) ([`fdc5790`](https://github.com/akotyla/ragbits/commit/fdc5790ac106d37fa8b6e792c2949b2d5bb82aed))

* feat(prompt-discovery): Look for prompts in arbitrary files using patterns (#38) ([`d390703`](https://github.com/akotyla/ragbits/commit/d390703c7301c7b12a84e52878ba2009f56b1514))

* feat(document-search): add chunking in unstructured provider (#48) ([`c4647cc`](https://github.com/akotyla/ragbits/commit/c4647cca7125268063cb3e3cda3d255ce92cd815))

* feat(document-search): add ChromaDB support. (#27) ([`7833615`](https://github.com/akotyla/ragbits/commit/78336153c21e1b99c37fce50e96e428d6d446186))

* feat(document-search): add gcs source to the DocumentMeta (#25)

* Initial version of GCS source

* Changes in the  method

* Changes after review

* Fixes after review

* Fix tests

* More fixes

* Update packages/ragbits-document-search/src/ragbits/document_search/documents/sources.py

Co-authored-by: Mateusz Hordyński <26008518+mhordynski@users.noreply.github.com>

---------

Co-authored-by: Mateusz Hordyński <26008518+mhordynski@users.noreply.github.com> ([`584fd93`](https://github.com/akotyla/ragbits/commit/584fd939963c9450b78c3d3e9fe33df0ada8c3e3))

* feat(document-search): add document processing with unstructured (#26) ([`1d743fb`](https://github.com/akotyla/ragbits/commit/1d743fbc262a8b593d959b4bf6c4484c4d88ad76))

* feat(cli): add basic cli setup with package discovery (#22) ([`4a02d22`](https://github.com/akotyla/ragbits/commit/4a02d22211d05e4ee66978c426e00fc9d9490be7))

* feat: add local embeddings (#13) ([`5a6ebe7`](https://github.com/akotyla/ragbits/commit/5a6ebe7db5dbfddee44b601d6fa6fc438430c577))

* feat(document-search): init document-search module with basic RAG capabilities on text (#3) ([`c8ae2f9`](https://github.com/akotyla/ragbits/commit/c8ae2f98047e15e7ee131997c535312f824e55f0))

* feat: add embeddings (#2)

* feat: add embeddings
* Fix pylint and mypy errors.

---------

Co-authored-by: Patryk Wyżgowski <patryk.wyzgowski@deepsense.ai> ([`25d8249`](https://github.com/akotyla/ragbits/commit/25d82491f5c6606b9bc563045f56aaa053072395))

* feat: add prompt explorer ui (#1) ([`4fa92be`](https://github.com/akotyla/ragbits/commit/4fa92be392715b557ff5cc204d7985e7e43e2959))

* feat: better support for strucutred outputs and tests ([`2409b3c`](https://github.com/akotyla/ragbits/commit/2409b3c5c5341537d59c9b8eb20fbc2067e6b909))

* feat: improve integration of LocalLLM ([`3287422`](https://github.com/akotyla/ragbits/commit/32874222c6e30131a74d4f4a62f0cf918760af69))

* feat: add support for structured outputs and output parsing ([`747163f`](https://github.com/akotyla/ragbits/commit/747163fd538baef37b911bca5393f1b57fbc498c))

* feat: add LLM support ([`6aa3b09`](https://github.com/akotyla/ragbits/commit/6aa3b094350dec98cf184f9386b4823f2ce681e7))

* feat: add prompt management module & basic repo structure ([`4a4ce9a`](https://github.com/akotyla/ragbits/commit/4a4ce9a534f899659f5890a9d3b9296a2370f5a3))

### Fixes

* fix(document-search): avoid metadata mutation (#63) ([`704eef2`](https://github.com/akotyla/ragbits/commit/704eef2445895092f3f1ef05a0b00c24c0325780))

* fix(prompt-lab): prevent crash when sending to LLM before rendering (#57) ([`2857978`](https://github.com/akotyla/ragbits/commit/2857978dff681cd583a782a13002aafe0dca4f85))

* fix(prompt-lab): app shouldn't crash when no prompts found (#53) ([`877b35f`](https://github.com/akotyla/ragbits/commit/877b35f7ce415c4467dbd1c5c7ca2b6d568a3b76))

* fix: not existing dir for nested gcs objects (#47) ([`9372351`](https://github.com/akotyla/ragbits/commit/937235149fee1acdf0003d58fedf096a4906db24))

### Refactoring

* refactor(prompts): Merge the dev-kit package into core (#66) ([`ec46bec`](https://github.com/akotyla/ragbits/commit/ec46bec43a8e658f218425068dc1406ea7933572))

* refactor: move vector search capabilities to core package (#39) ([`a186751`](https://github.com/akotyla/ragbits/commit/a1867514b4975aebc8b8c1f3e4cf55eb0c643792))

### Unknown

* Update ragbits-document-search version from 0.2.0 to 1.0.0 ([`b2f35f1`](https://github.com/akotyla/ragbits/commit/b2f35f114f47848594967dcc76da27e0d3e6749d))

* Update ragbits-core version from 0.1.0 to 0.2.0 ([`81b1869`](https://github.com/akotyla/ragbits/commit/81b1869fa7bb9d541d7bc32ea1b970abf8f63cb7))

* Fix script ([`63dba8f`](https://github.com/akotyla/ragbits/commit/63dba8f91f34b6707f3b18b1c3bccfade56cdd12))

* Add ragbits package handling ([`5a02337`](https://github.com/akotyla/ragbits/commit/5a02337ca3e3a558e35c8cd211e6011cac5cdafb))

* Update versions in automatic commit message ([`e6e9702`](https://github.com/akotyla/ragbits/commit/e6e9702cc4a8e1717affcefebcf57c2ae630bde3))

* Merge branch 'main' into 17-chore-add-package-version-update-action ([`9e55689`](https://github.com/akotyla/ragbits/commit/9e55689b05e6f00fb7d420616caf4f701e700c50))

*  feat(prompts): integration with promptfoo (#54) ([`0c808cd`](https://github.com/akotyla/ragbits/commit/0c808cd21683783ca3f4cafb85c4a1675de3f495))

* Add semantic release workflow ([`6055d6f`](https://github.com/akotyla/ragbits/commit/6055d6f4073ac772996199f870ba7b51b6da9163))
