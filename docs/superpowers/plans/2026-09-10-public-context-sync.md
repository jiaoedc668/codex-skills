# Boss IP Public Context Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only, whitelist-based synchronizer that publishes safe local Boss IP state into the four `chat-context/` snapshots.

**Architecture:** Keep `history_manager.py` as the business-state reader and add `sync_public_context.py` as an isolated projection writer. The synchronizer reads all inputs before writing, constructs four fixed schemas, rejects unsafe values, then atomically replaces the destination snapshots as one prepared batch.

**Tech Stack:** Python standard library, `unittest`, JSONL readers already provided by `history_manager.py`, atomic temporary-directory replacement.

**Spec:** `docs/superpowers/specs/2026-09-10-public-context-sync-design.md`

## Global Constraints

- `SKILL.md` remains the only business-rule source.
- Local business inputs are read-only and never copied into the repository.
- Public snapshots must exclude `user_quote`, internal paths, complete scripts, research bodies, credentials, and identifiable private data.
- Unknown fields are rejected or dropped through explicit per-snapshot allowlists.
- Python changes require targeted tests, full unittest, compileall, and `git diff --check`.
- This compatible feature release uses version `1.2.0` and tag `boss-ip-v1.2.0`.

---

### Task 1: Define failing public projection tests

**Files:**
- Create: `boss-ip-video-script-writer/tests/test_public_context_sync.py`
- Read: `boss-ip-video-script-writer/scripts/history_manager.py`

**Interfaces:**
- Tests import `sync_public_context.build_public_snapshots`, `sync_public_context.sync_public_context`, and `sync_public_context.main`.
- The expected result is a mapping from the four output filenames to JSON-compatible dictionaries.

- [ ] **Step 1: Write tests for safe projection behavior**

Add tests that create temporary persona, feedback, topic, and shared ledgers containing both allowed data and forbidden fields. Assert that:

```python
snapshots = build_public_snapshots(persona_path, feedback_path, topic_path, shared_path)
assert "user_quote" not in json.dumps(snapshots, ensure_ascii=False)
assert "research_evidence" not in snapshots["recent-topics.json"]["items"][0]
assert "script" not in json.dumps(snapshots["recent-topics.json"], ensure_ascii=False)
assert "C:\\private" not in json.dumps(snapshots, ensure_ascii=False)
```

Also assert the allowed IDs, categories, evaluations, preferences, and public persona fields remain present.

- [ ] **Step 2: Write tests for source immutability and atomic failure**

Record bytes for every input file, run a successful sync, and assert all bytes are unchanged. Seed output files, provide an unsafe input, assert the sync raises a safety error, and assert every seeded output byte is unchanged.

- [ ] **Step 3: Write tests for successful CLI output**

Run `main()` or a subprocess with explicit `--persona`, `--feedback-ledger`, `--topic-ledger`, `--shared-ledger`, and `--output-dir` paths. Assert four files exist, each is valid JSON, and each reports `snapshot_status == "current"`.

- [ ] **Step 4: Run the targeted test file**

Run:

```powershell
python -m unittest boss-ip-video-script-writer/tests/test_public_context_sync.py -v
```

Expected: FAIL because `sync_public_context.py` does not yet exist.

### Task 2: Implement the minimal safe synchronizer

**Files:**
- Create: `boss-ip-video-script-writer/scripts/sync_public_context.py`
- Modify: none in `history_manager.py` unless a narrowly tested reusable summary helper is required

**Interfaces:**
- `build_public_snapshots(persona_path: Path, feedback_path: Path, topic_path: Path, shared_path: Path, now: str | None = None) -> dict[str, dict[str, Any]]`
- `sync_public_context(persona_path: Path, feedback_path: Path, topic_path: Path, shared_path: Path, output_dir: Path) -> dict[str, Path]`
- CLI options: `--persona`, `--feedback-ledger`, `--topic-ledger`, `--shared-ledger`, `--output-dir`.

- [ ] **Step 1: Add fixed allowlist projectors**

Use `history_manager.read_json`, `read_feedback`, `read_ledger`, `read_shared_preferences`, and `feedback_context`. Construct each output from named fields only. For persona, keep only public identity, production frame, authorized behavior descriptions/limits, expression patterns/avoid text, active viewpoint choices/exceptions/cost, and public weaknesses. For feedback, copy safe scalar/list fields only and omit the raw quote. For topics, read topic status rows and emit only current topic IDs, titles, categories, and statuses. For shared preferences, emit only source Skill, preference, and occurred time.

- [ ] **Step 2: Add safety validation and atomic writes**

Reject any projected string containing absolute Windows/Unix paths, credential-like keys, raw quote keys, complete-script keys, or research-body keys. Build all four snapshots in memory, write them to a temporary directory under the output parent, validate JSON, and replace each destination only after all four files are ready. Do not touch input files.

- [ ] **Step 3: Add CLI and error behavior**

Parse explicit paths, use one timestamp for the batch, print the four written paths as JSON, and return a nonzero error without changing existing outputs if any input or safety check fails.

- [ ] **Step 4: Run the targeted tests**

Run the same unittest command from Task 1 and expect all new tests to pass.

### Task 3: Update contracts and release metadata

**Files:**
- Modify: `boss-ip-video-script-writer/CHATGPT.md`
- Modify: `boss-ip-video-script-writer/AGENTS.md`
- Modify: `boss-ip-video-script-writer/CHANGELOG.md`
- Modify: `boss-ip-video-script-writer/SKILL.md`
- Modify: `README.md`

- [ ] **Step 1: Document the explicit sync command and boundaries**

Document the command shape:

```powershell
python <skill-dir>/scripts/sync_public_context.py --persona <business-root>/人物设定.json --feedback-ledger <business-root>/反馈台账.jsonl --topic-ledger <business-root>/选题台账.jsonl --shared-ledger <shared-root>/shared-creative-preferences.jsonl --output-dir <skill-dir>/chat-context
```

State that it is an explicit local operation, reads business state only, and publishes allowlisted projections.

- [ ] **Step 2: Bump version and changelog**

Change `metadata.version` to `1.2.0`, add the dated changelog entry with compatibility and verification notes, and retain the 1.1.0 history.

### Task 4: Run release verification and publish

**Files:**
- Modify: only reviewed files under `README.md` and `boss-ip-video-script-writer/`

- [ ] **Step 1: Run targeted tests and inspect output snapshots**

Run the new test file, inspect generated JSON keys, and confirm the business input hashes are unchanged.

- [ ] **Step 2: Run full checks**

```powershell
python -m unittest discover -s boss-ip-video-script-writer/tests -p "test_*.py" -q
python -m compileall -q boss-ip-video-script-writer/scripts
python -m json.tool boss-ip-video-script-writer/chat-context/persona-current.json > $null
python -m json.tool boss-ip-video-script-writer/chat-context/recent-feedback.json > $null
python -m json.tool boss-ip-video-script-writer/chat-context/recent-topics.json > $null
python -m json.tool boss-ip-video-script-writer/chat-context/shared-preferences.json > $null
git diff --check
```

- [ ] **Step 3: Stage only the reviewed scope**

Run `git add -- README.md boss-ip-video-script-writer`, inspect `git diff --cached --stat` and `git diff --cached --check`, and confirm `product-video-script-writer/` is not staged.

- [ ] **Step 4: Commit, tag, push, and verify remote state**

```powershell
git commit -m "feat(boss-ip): sync public chat context from local state"
git tag -a boss-ip-v1.2.0 -m "Boss IP Skill v1.2.0"
git push origin main
git push origin boss-ip-v1.2.0
```

Verify local HEAD, remote `main`, and the remote tag resolve to the published commit.
