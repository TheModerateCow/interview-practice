# Test sets
- `rate-limiter-py`: Python codebase round, 2 phases (sliding-window limiter; part 2 adds `remaining`/`reset`), run_entry `main.py`.
- `mini-go` (merge intervals), `mini-java` (Roman numerals): single-phase tdd sets with run_entry + 1 testcase.
- Gate (needs the docker proxy on 127.0.0.1:23750): `DOCKER_HOST=tcp://127.0.0.1:23750 python3 backend/gate.py tests/sets/<name>`
- Pack: `python3 tools/pack.py tests/sets/<name> tests/sets/_zips/<name>.zip`
- `_zips/invalid-bad-manifest.zip` and `_zips/evil-zipslip.zip` are hand-made negative fixtures for the importer.
