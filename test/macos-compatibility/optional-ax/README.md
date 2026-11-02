# Historical AX experiment archive

The current implementation is the dedicated AccessibilityText module and real
selection setter documented in ../AX-AUTOMATION-WORK.md. Do not apply the old
snapshot experiment over the current product.

The superseded snapshot.patch and *.snapshot files are retained locally but
excluded from the Git source distribution. They are historical recovery inputs,
not dependencies of the current build or tests. Earlier reports may reference
this local archive; those references do not imply the patch is shipped or that
old acceptance results describe the current implementation.

The historical experiment modified Screen/StringMap directly. The current
module isolates mapping and leaves those files unchanged. Do not confuse either
with upstream src/terminal/snapshot/, which is unrelated serialization code.
