# Project Testing Policy

PiscineForge local Project Moulinette tests may be built from:
- subject text/spec
- local fixtures
- public test behavior
- multiple public implementations
- manual reasoning about expected behavior

But tests must be:
- local
- documented
- not claimed official
- not exposing solutions
- not dependent on external services
- not copying unlicensed code
- reproducible

## Recommended method:

1. Read subject/spec.
2. Identify input/output contract.
3. Compare multiple public implementations to understand edge cases.
4. Build black-box tests from the contract.
5. Add invalid/edge/performance tests.
6. Keep tests in corrections/private resources, not workspace.
7. Add clear trace output.
8. Run tests against intentionally broken samples if available.
9. Document limitations.

## Forbidden:
- copying solution code into student workspace
- exposing hidden tests
- claiming official 42 correction
- tests that depend on external services
- tests that depend on random external repos

## Legacy Subjects (Local Reference Policy)

When integrating legacy Piscine projects (BSQ, Rush, Sastantua, etc.):
1. **Local trainer mode**: Project commands use local metadata, local submissions, and optional local reference files.
2. **Metadata Only**: External references and GitHub repositories are cataloged in `resources/legacy_subjects/references.yml` for documentation purposes only.
3. **Local References**: Subject PDFs and test materials are expected to exist locally in `resources/legacy_subjects/projects/<project>/`.
4. **Transparency**: The CLI commands `pforge project references` and `pforge project subject` must clearly report local file status and show `Remote downloads: disabled`.

### Explicit Limitations and Boundaries

- **Project Moulinette is local-only.** It is not the official 42 Moulinette.
- It does not connect to real 42 services.
- Real Vogsphere, SSH, Kerberos, and official 42 service integration are out of scope.
- Remote downloads are disabled.
- Legacy repositories were used only during one-time preparation.
- PDFs under `resources/legacy_subjects/projects/<project>/` are local reference copies only.
- Existing built-in Piscine and exam subjects remain authoritative and are not touched.
- No solutions are imported, copied, displayed, or used.
- Project support status varies by project.
