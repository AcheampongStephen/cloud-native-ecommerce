# Engineering observations

- A missing response does not prove that a remote side effect failed. Persist
  intent and reuse stable operation IDs during recovery.
- Publish-confirm then database commit can duplicate delivery; acknowledge-after-
  inbox-commit plus deduplication makes that safe.
- Test concurrent stock updates against the actual database backend, not only mocks.
- Shared Docker image tags should be built once, not exported concurrently by
  multiple service builds.
- Dependency pins can contain known vulnerabilities. Audit and retest updates;
  pinning alone is not a security control sufficient for release.
- A functioning demo differs from validated production operations. Document
  limitations and evidence precisely.
