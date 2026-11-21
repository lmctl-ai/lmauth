# AGENTS.md — lmauth (public)

This public repository holds lmauth's release policy, qualification tests and operator documentation. The Go source is private (lmctlhq/lmauth).

Read durable-memory/index.md first. It lists what earlier work learned that the docs alone do not say. When you finish work another agent would need to know about, add a note in durable-memory/ and a line in the index in the same commit.

- Operator docs: docs/operator-quickstart.md, docs/npm-publish.md, docs/releasing.md, docs/release-pipeline.md.
- Published documentation: https://lmctl.com/tools/lmauth/ (source in lmctl-ai/lmctl, tools/lmauth/; publish with the deploy-static workflow, which runs only by dispatch).
- Tests: `PYTHONPATH=scripts:tests python3 -m unittest discover -s tests -p 'test_*.py'`.
