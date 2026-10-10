# Repository maintenance

Runtime source, tests, reviewed documentation, dependency locks, and deliberately selected example assets belong in Git. Local agent state, credentials, caches, build output, browser traces, and test reports belong in ignored local files. Removing a path from the Git index does not require deleting its local copy.

`python scripts/check_repository_hygiene.py` checks the current Git index. CI rejects tracked private/configuration artifacts and blobs larger than 5 MiB unless their exact Git content hash is reviewed in `.repository-hygiene.json`. Existing large examples or research artifacts are listed explicitly; the list does not permit arbitrary replacements or new large files.

Use platform secrets or ignored local environment files for credentials. Template files must contain placeholders. Run Gitleaks locally with redaction before sharing diagnostic output. A clean scanner result is evidence for its covered rules, not a guarantee that every kind of private information has been detected.

Internal `.agent/` records are local working material. Old planning documents may mention these paths as historical implementation records; that does not make the logs part of the published software or its runtime contract.

Large imported examples retain their documented purpose and original paths. Prefer shallow clones for browsing (`git clone --depth 1 ...`). Moving assets to LFS or rewriting history is a separate, deliberate migration, not a routine cleanup command.
