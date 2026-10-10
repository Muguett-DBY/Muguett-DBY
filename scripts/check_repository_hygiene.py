"""Check the Git index for local artifacts and unreviewed large files."""
import json
from pathlib import PurePosixPath, Path
import re
import subprocess
import sys

policy = json.loads(Path(".repository-hygiene.json").read_text(encoding="utf-8"))
entries = subprocess.check_output(["git", "ls-files", "--stage"], text=True, encoding="utf-8").splitlines()
roots = {".agent", ".open-next", ".next", ".wrangler", ".venv", "node_modules", ".playwright-cli", "playwright-report", "test-results", "output", "__pycache__"}
errors = []
objects = []
for entry in entries:
    metadata, path = entry.split("\t", 1)
    mode, sha, stage = metadata.split()
    if stage != "0":
        errors.append(path + ": unresolved merge entry")
        continue
    name = PurePosixPath(path).name
    root = path.split("/", 1)[0]
    template = name.endswith((".example", ".sample", ".template"))
    if root in roots or "__pycache__" in PurePosixPath(path).parts:
        errors.append(path + ": local or generated artifact is tracked")
    if (name.startswith((".env", ".dev.vars")) and not template) or name in {"config.txt", "TOKEN.txt", "TOKEN.md", "STRATZ_API.txt"} or name.endswith((".pem", ".key", ".p12", ".pyc", ".tsbuildinfo")):
        errors.append(path + ": local configuration or private artifact is tracked")
    if mode != "160000":
        objects.append((sha, path))
sizes = subprocess.run(["git", "cat-file", "--batch-check=%(objectname) %(objectsize)"], input="\n".join(sha for sha, _ in objects)+"\n", capture_output=True, text=True, check=True).stdout.splitlines()
for (sha, path), result in zip(objects, sizes):
    fields = result.split()
    if len(fields) != 2 or not fields[1].isdigit():
        errors.append(path + ": Git object is unavailable")
        continue
    if int(fields[1]) > policy["max_blob_bytes"] and policy["allowed_large_blobs"].get(path) != sha:
        errors.append(path + ": large file requires an explicit content-hash review")
if errors:
    print("Repository hygiene failed:\n" + "\n".join(errors))
    sys.exit(1)
print(f"Repository hygiene passed: {len(entries)} tracked files checked.")
