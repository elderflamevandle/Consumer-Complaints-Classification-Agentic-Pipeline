# Pitfalls Research

**Domain:** Agentic AI complaint resolution platform for consumer finance operations
**Researched:** 2026-04-05
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Invalid fallback chain causes runtime outages

**What goes wrong:**
Fallback selection references unavailable model IDs, so retries never recover.

**Why it happens:**
Model list copied from outdated examples without provider verification.

**How to avoid:**
Hardcode validated fallback chain and unit test every branch.

**Warning signs:**
Repeated HTTP 400/404 model errors after a 429 event.

**Phase to address:**
Phase 1 (foundation and client setup)

---

### Pitfall 2: MCP integration is faked in-process

**What goes wrong:**
Remediation appears grounded but actually uses a local helper function, weakening trust.

**Why it happens:**
Teams optimize for speed and skip protocol boundary implementation.

**How to avoid:**
Run MCP as a separate server process and call tool through real client discovery.

**Warning signs:**
No MCP client initialization logs; no transport config; no tool-discovery step.

**Phase to address:**
Phase 3 (MCP-backed remediation)

---

### Pitfall 3: Auditor loop dead-ends or loops forever

**What goes wrong:**
Audit fail path is miswired, causing response never to improve or graph never to end.

**Why it happens:**
Missing loop counters or poor state mutation strategy in critique handoff.

**How to avoid:**
Track audit attempts and cap retries; append critique messages deterministically.

**Warning signs:**
Repeated identical outputs across audit cycles; no pass condition hit.

**Phase to address:**
Phase 4 (response + compliance loop)

---

### Pitfall 4: Streamlit reruns destroy graph thread context

**What goes wrong:**
Human approvals restart pipeline instead of resuming interrupted state.

**Why it happens:**
Thread config not persisted in `st.session_state`.

**How to avoid:**
Persist `thread_id` and resume tokens explicitly on every action event.

**Warning signs:**
Approval clicks restart from intake node instead of continuing from interrupt.

**Phase to address:**
Phase 5 (dashboard and HITL controls)

---

### Pitfall 5: Demo success without robustness checks

**What goes wrong:**
Golden path works once but fails under edge inputs (empty, long, ambiguous).

**Why it happens:**
Overfitting implementation to curated examples only.

**How to avoid:**
Add edge-case suite and rerun golden demos three times before freeze.

**Warning signs:**
High variance output quality and unexplained parse failures.

**Phase to address:**
Phase 6 and Phase 7 (evaluation + hardening)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| No schema validation | Faster coding | Frequent runtime parse breakage | Never |
| Single giant prompt | Fewer files | Poor observability and control | Never |
| Skip audit logging | Less plumbing | No traceability for judges/reviewers | Never |
| Hardcode UI flow logic | Quick UI progress | Fragile resume behavior | Only for temporary prototypes, not final demo |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Groq | Treat every error as retryable | Retry 429 with backoff; fail fast on model-not-found |
| MCP | Assume tool name stability | Discover tools at startup and validate required signature |
| ChromaDB | Rebuild embeddings on every app start | Seed offline and mount persistent local directory |
| Presidio | Run heavy NLP model by default | Use `en_core_web_sm` for MVP speed and stability |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Online embedding generation | Slow first-response latency | Precompute vectors offline | During demo runs and repeated sessions |
| Unbounded complaint length | Timeouts and token spikes | Enforce truncation/chunk strategy | Long narrative submissions |
| Full-agent rerun after UI interaction | Duplicate API calls and cost spikes | Resume from checkpointed state | Any HITL interaction-heavy demo |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging raw complaint text with PII | Data leakage in logs | Scrub PII before persistence and before model calls |
| Storing API keys in tracked files | Credential exposure | Use `.env`, `.env.example`, and gitignore |
| Overstated compliance claims | Legal/reputational risk | Keep language as "decision support" with human approval gates |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Opaque agent outputs | Users do not trust recommendations | Show concise rationale per stage |
| Missing approval controls | Users feel locked out | Approve/Edit/Reject controls at review gates |
| No failure messaging | Demo appears unstable | Add explicit fallback and retry status messaging |

## "Looks Done But Isn't" Checklist

- [ ] **Groq fallback:** Verified by forced 429 simulation and model-not-found test
- [ ] **MCP integration:** Verified as external call path, not local function shim
- [ ] **Auditor loop:** Verified fail->rewrite->pass path with capped retries
- [ ] **HITL resume:** Verified state continuity after Streamlit reruns
- [ ] **Fairness tab:** Verified with actual grouped metrics, not placeholder visuals

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Invalid fallback chain | LOW | Update model map, rerun client tests, redeploy |
| MCP tool failure | MEDIUM | Degrade to safe manual-review recommendation and log warning |
| Audit loop instability | MEDIUM | Introduce max attempts, capture critique history, add fail-safe exit |
| UI resume failure | HIGH | Rework session state handling and checkpoint wiring |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Invalid fallback chain | Phase 1 | Client tests pass for fallback branch selection |
| Fake MCP integration | Phase 3 | External tool call logs and deterministic SLA payload tests |
| Broken auditor loop | Phase 4 | Controlled fail/pass regression test passes |
| Streamlit state loss | Phase 5 | HITL approve/edit/reject resume tests pass |
| Demo-only overfitting | Phase 6-7 | Edge-case suite and repeated golden runs pass |

## Sources

- `f:/Agentic_Hackathon/plan2.md`
- `f:/Agentic_Hackathon/plan.md`
- `.planning/PROJECT.md`

---
*Pitfalls research for: Agentic AI complaint resolution platform for consumer finance operations*
*Researched: 2026-04-05*
