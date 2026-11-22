# IBM Bob Workflow — Screenshot Checklist

> ⏰ **DEADLINE: Drop all 3 screenshots in this folder before 1:30 PM**
>
> These screenshots are referenced in the judge-facing `README.md` and validate the
> "How We Engineered This With IBM Bob" section of our Track 01 submission.

---

## Checklist

- [ ] **Screenshot 1** — `01_bob_plan_mode.png`
- [ ] **Screenshot 2** — `02_bob_agent_generating_code.png`
- [ ] **Screenshot 3** — `03_pytest_passing.png`

---

## Screenshot 1 — IBM Bob Plan Mode Output

**Filename:** `01_bob_plan_mode.png`

**What to capture:**
- IBM Bob running in **Plan mode** with the AGENTS.md context loaded
- The chat output showing Bob decomposing the backend requirements into the 8 ordered sub-tasks
- Ideally visible: the sub-task list with Intent / Expected Outcomes / Todo List structure
- The [`backend-plan.md`](../../backend-plan.md) file being written, or the Plan mode task breakdown visible in the chat panel

**How to get it:**
1. Open IBM Bob in Plan mode in this repo
2. Scroll up in the conversation to the planning response
3. Take a full-window screenshot showing the sub-task breakdown
4. Save as `01_bob_plan_mode.png` in this folder

---

## Screenshot 2 — IBM Bob Agent Mode Generating Code

**Filename:** `02_bob_agent_generating_code.png`

**What to capture:**
- IBM Bob running in **Agent mode** actively generating `backend/agents.py` or the policy pack JSON files
- Ideally shows: the tool call panel on the left (write_file / apply_diff) + the code being written on the right
- Must clearly show the IBM Bob interface — not just a code editor

**Ideal moment to capture:**
- When Bob is writing the 4-agent pipeline in `agents.py` (the most visually impressive output)
- OR when Bob writes `policy_pack_ekhata.json` / `policy_pack_sakala_sla.json`
- OR when Bob runs the geo.py validation and shows `ward_mismatch: True` in the terminal output

**How to get it:**
1. Run the agent mode task for the backend pipeline
2. When Bob is mid-generation (tool call visible), take a screenshot
3. Save as `02_bob_agent_generating_code.png` in this folder

---

## Screenshot 3 — Passing pytest Terminal Output

**Filename:** `03_pytest_passing.png`

**What to capture:**
- Terminal window showing `pytest backend/tests/test_agents.py -v` running and **passing all 4 tests**
- Must show: green `PASSED` lines for all 4 test names:
  - `test_ekhata_name_mismatch_caught`
  - `test_gruha_jyothi_tenant_check`
  - `test_sakala_sla_breach_escalation`
  - `test_hot_register_new_policy`
- Final line: `4 passed` in green

**How to get it:**
```bash
# From repo root with venv activated
pytest backend/tests/test_agents.py -v
```
Take a screenshot when all 4 show PASSED.

> If tests haven't been written yet — this is the trigger to run them.
> Tests must pass **without any LLM API key** (all deterministic fallbacks).

---

## File Naming Convention

| File | Used in README as |
|---|---|
| `01_bob_plan_mode.png` | `![Bob Plan Mode](docs/ibm-bob-workflow/01_bob_plan_mode.png)` |
| `02_bob_agent_generating_code.png` | `![Bob Agent Mode](docs/ibm-bob-workflow/02_bob_agent_generating_code.png)` |
| `03_pytest_passing.png` | `![Pytest Passing](docs/ibm-bob-workflow/03_pytest_passing.png)` |

All three are referenced in the **"How We Engineered This With IBM Bob"** section of [`README.md`](../../README.md).

---

## Quick Screenshot Tips

- **macOS**: `Cmd + Shift + 4` → drag to select area → saves to Desktop
- **Windows**: `Win + Shift + S` → Snip & Sketch
- Rename the file to match the exact filenames above before dropping here
- Minimum resolution: 1200px wide so the IBM Bob interface is readable by judges
