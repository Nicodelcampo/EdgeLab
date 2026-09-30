# aVolClusterPOI v0.4 — immutable incoming source

- Raw SHA-256: `3420519de9b4a1456f812040b62af419b0c323486281424a84aaaab126100c98`
- Prepared SHA-256: `33028abd28b706191b5a455e47989252e0ff33035fa75bc23e1dc0f6ec94ec1c`
- Raw bytes: `54577`
- Prepared bytes: `42782`
- Class: `aVolClusterPOI`
- Status: `STATIC_PREPARED_NOT_COMPILED`

The deterministic gzip+base64 artifact reconstructs the immutable raw attachment byte-for-byte. `tools/prepare_nt8_candidate.py` removes only the generated NinjaScript tail and normalizes CRLF. The prepared candidate is not canonical until a real NT8 compile and NT8↔Python parity succeed. Its embedded target/stop evaluator is excluded from the initial target-free kernel.
