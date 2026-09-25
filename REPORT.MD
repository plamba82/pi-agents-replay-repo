
### Summary

This REPORT.md provides:

1. **Architecture**: Clear system design with diagrams, key decisions, and trade-offs
2. **Artifact Schema**: Detailed schema design with rationale for every field
3. **Determinism & Error Handling**: Three-tier error taxonomy (business outcomes, recoverable, hard failures) with detection strategies
4. **Heterogeneity & Multi-Tenant**: Concrete designs for legacy web, desktop, and multi-tenant reuse
5. **Escalation & Handoff**: Real stuck detection and control transfer mechanism (with production design)
6. **Safety**: Guardrails, PII redaction, secrets management, and acknowledged limits
7. **Cuts**: Honest assessment of what was left out and prioritized next steps


### Computer-Use Automation System

A production-grade system for automating legacy applications using LLM-driven discovery and deterministic replay.

### Overview

This system enables AI agents to operate legacy banking applications by:
1. **Discovery**: LLM observes UI, decides actions, accomplishes goals
2. **Recording**: Successful runs become typed, versioned capability artifacts
3. **Replay**: Deterministic execution without LLM, with robust error handling
4. **Escalation**: Human-in-the-loop when automation gets stuck
5. **Safety**: Guardrails, allowlists, and PII redaction throughout

## Architecture

    
                ┌────────────────────────────────────────────────────────┐
                │                     AI Agent Layer                     │
                │              (calls capabilities by name)              │
                └───────────────────┬────────────────────────────────────┘
                                    │
                ┌───────────────────▼────────────────────────────────────┐
                │              Capability Artifacts                      │
                │     (typed, versioned, reusable automations)           │
                └───────────────────┬────────────────────────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                ┌────────▼─────────┐   ┌────────▼──────────┐
                │  Discovery Agent │   │  Replay Engine    │
                │  (LLM-driven)    │   │  (deterministic)  │
                └────────┬─────────┘   └────────┬──────────┘
                        │                       │
                        └───────────┬───────────┘
                                    │
                ┌────────────────────▼────────────────────────────────────┐
                │              Surface Abstraction                        │
                │     (Web, Desktop, Accessibility APIs)                  │
                └────────────────────┬────────────────────────────────────┘
                                     │
                ┌────────────────────▼────────────────────────────────────┐
                │         Target Application (Legacy Banking)             │
                └─────────────────────────────────────────────────────────┘

### Architecture & Technology Choices
Language & Runtime: Python 3.11+ 
LLM Provider: Anthropic Claude 3.5 Sonnet 
Automation Framework: Playwright (cross-browser, accessibility tree access, screenshot support, works with legacy DOM)
Target Application: A local Flask demo app simulating a legacy banking interface (table-based layout, no test IDs, multi-step flows)

### Key Design Decisions:

Multi-strategy locators - Combine accessibility tree, visual landmarks, and DOM fallbacks for robustness
Typed artifact schema - JSON Schema validated, versioned capabilities with clear contracts
Three-tier error taxonomy - Business outcomes, recoverable conditions, hard failures
Session-based handoff - WebSocket control transfer for human intervention
Surface abstraction layer - Protocol-based design supporting web/desktop/accessibility surfaces

### Project Structure:

pi-agents-exercise/
├── REQUIREMENTS.md
├── APPROACH.md
├── README.md
├── REPORT.md
├── requirements.txt
├── .env.example
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Configuration & guardrails
│   ├── models/
│   │   ├── __init__.py
│   │   ├── artifact.py            # Capability artifact schema
│   │   ├── execution.py           # Execution result types
│   │   └── session.py             # Session state management
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── discovery.py           # LLM-driven discovery loop
│   │   ├── replay.py              # Deterministic replay engine
│   │   └── prompts.py             # LLM prompt templates
│   ├── surfaces/
│   │   ├── __init__.py
│   │   ├── base.py                # Surface abstraction protocol
│   │   ├── web.py                 # Playwright web surface
│   │   └── locator.py             # Multi-strategy locator engine
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── guardrails.py          # Allowlist & action validation
│   │   └── redaction.py           # PII/secret redaction
│   ├── escalation/
│   │   ├── __init__.py
│   │   ├── detector.py            # Stuck state detection
│   │   ├── handoff.py             # Session control transfer
│   │   └── operator.py            # Mock operator interface
│   └── observability/
│       ├── __init__.py
│       ├── logger.py              # Structured logging
│       └── evidence.py            # Screenshot/trace capture
├── demo_app/
│   ├── app.py                     # Flask legacy banking demo
│   ├── templates/
│   │   ├── index.html
│   │   ├── search.html
│   │   └── member_detail.html
│   └── static/
│       └── style.css
├── evidence/
│   ├── discovery_run_001.json
│   ├── replay_success_001.json
│   ├── replay_error_001.json
│   └── screenshots/
├── artifacts/
│   └── lookup_member_balance.json
└── tests/
    ├── __init__.py
    ├── test_artifact.py
    ├── test_replay.py
    └── test_guardrails.py




### Key Architectural Decisions

**1. Surface Abstraction Layer**

The `Surface` interface ([base.py](src/surfaces/base.py)) decouples automation logic from the underlying UI technology. This enables:
- **Heterogeneity support**: Same artifact schema works across web, desktop, and legacy surfaces
- **Technology swapping**: Can replace Playwright with Selenium, Appium, or OS-level automation without changing artifacts
- **Testing**: Mock surfaces for unit testing without browser overhead

**Trade-off**: Abstraction adds indirection, but the payoff is multi-surface support and testability. The interface is deliberately minimal (navigate, click, type, extract, wait) to avoid leaking surface-specific details.

**2. Artifact-Centric Design**

The `CapabilityArtifact` ([artifact.py](src/models/artifact.py)) is the system's contract between discovery and replay. It's:
- **Typed and versioned**: JSON schema with explicit input/output contracts
- **Reviewable**: Human-readable, can be audited before production use
- **Parameterized**: Supports variable substitution (e.g., member IDs)
- **Self-contained**: Includes all metadata needed for replay (locators, checkpoints, error handling)

**Trade-off**: Richer schema means more upfront design, but it enables multi-tenant reuse and safe production deployment.

**3. Multi-Strategy Locator System**

Each step uses a `Locator` with multiple strategies:
- **Primary**: Accessibility tree (role + name) - most stable across UI changes
- **Fallbacks**: Visual landmarks, text content, DOM selectors
- **Strategy enum**: `ACCESSIBILITY`, `VISUAL`, `DOM`, `TEXT`, `COMPOSITE`

**Trade-off**: Accessibility-first approach works well for modern apps but requires fallbacks for legacy surfaces. The composite strategy adds complexity but dramatically improves replay reliability.

**4. Synchronous CLI + Async Core**

The CLI ([main.py](src/main.py)) is synchronous for simplicity, but the core engine is async (Playwright requires it). This hybrid approach:
- **Simplifies user experience**: Standard CLI patterns, no async/await in user code
- **Enables concurrency**: Replay engine can parallelize steps in the future
- **Matches Playwright**: Native async API usage, no sync wrappers

**Trade-off**: Mixing sync/async adds cognitive load, but it's the right model for browser automation.

**5. Evidence-First Observability**

Every run produces:
- **Structured logs**: JSON-formatted with PII redaction ([logger.py](src/observability/logger.py))
- **Screenshots**: Captured at each step ([evidence.py](src/observability/evidence.py))
- **Execution results**: Typed outcome objects with error details

**Trade-off**: Storage overhead for screenshots, but essential for debugging production failures and auditing compliance.

---

## 2. Artifact Schema

### Schema Design

The artifact schema ([artifact.py](src/models/artifact.py)) is the most critical design decision. It balances **expressiveness** (what can be automated) with **simplicity** (what can be reviewed and maintained).

{
  "artifact_id": "cap_http:__127.0.0.1:5000_search_3",
  "version": "1.0.0",
  "created_at": "2026-09-25T02:12:21.792278",
  "name": "Look up member 12345 and read their savings balance",
  "description": "Automated capability: Look up member 12345...",
  "entry_point": "http://127.0.0.1:5000/search",
  
  "parameters": [
    {
      "name": "member_id",
      "type": "string",
      "description": "Input parameter: member_id",
      "required": true,
      "validation_pattern": null
    }
  ],
  
  "outputs": [
    {
      "name": "savings_balance",
      "type": "string",
      "description": "Output field: savings_balance",
      "extraction_path": "$.savings_balance"
    }
  ],
  
  "steps": [
    {
      "step_id": 1,
      "action": "click",
      "locator": {
        "strategy": "accessibility",
        "primary": "textbox:Member ID",
        "fallbacks": [],
        "description": "Member ID input field"
      },
      "timeout_ms": 30000,
      "retry_count": 3,
      "on_error": "fail"
    },
    {
      "step_id": 2,
      "action": "type",
      "locator": { "strategy": "accessibility", "primary": "textbox:Member ID" },
      "value": null,
      "parameter_ref": "member_id",
      "timeout_ms": 30000
    },
    {
      "step_id": 3,
      "action": "click",
      "locator": { "strategy": "accessibility", "primary": "button:Search Member" },
      "timeout_ms": 30000
    }
  ],
  
  "final_checkpoint": {
    "description": "Goal achieved",
    "locator": { "strategy": "accessibility", "primary": "text:Savings Balance" },
    "expected_state": "visible"
  }
}

### Design Rationale"
1. Typed I/O Contract

The parameters and outputs arrays define the capability's interface:

Parameters: What the caller must provide (e.g., member_id)
Outputs: What the capability returns (e.g., savings_balance)
Validation: Optional regex patterns for input validation
Why: This makes artifacts callable by AI agents. An agent can discover capabilities, understand their contracts, and invoke them with typed arguments.

2. Multi-Strategy Locators

Each Locator has:

Strategy: Primary approach (accessibility, visual, DOM, text)
Primary selector: The main identifier (e.g., "textbox:Member ID")
Fallbacks: Alternative selectors if primary fails
Description: Human-readable explanation
Why: Accessibility-first targeting is most stable (roles/labels change less than DOM structure), but fallbacks handle legacy apps without semantic markup.

3. Error Handling Metadata

Each step includes:

on_error: "fail", "retry", "skip", or "escalate"
expected_errors: Known business outcomes (e.g., ["Member not found"])
retry_count: How many times to retry transient failures
Why: Distinguishes expected business outcomes (e.g., "no such member") from hard failures (e.g., network timeout). This is critical for production reliability.

4. Final Checkpoint

The final_checkpoint verifies goal completion:

Locator: Element that proves success (e.g., "Savings Balance" text)
Expected state: What to verify (e.g., "visible", "contains:$5,432.10")
Why: Prevents false positives. Without checkpoints, a click that silently fails would appear successful.

5. Versioning and Metadata

version: Semantic versioning for schema evolution
created_at: Timestamp for audit trails
tenant_id: (Optional) Multi-tenant support
base_artifact_id: (Optional) Inheritance for tenant-specific overrides
Why: Enables artifact evolution, tenant-specific customization, and compliance auditing.

Schema Trade-offs
Expressiveness vs. Simplicity: The schema is deliberately minimal. It doesn't support:

Conditional logic (if/else)
Loops (for/while)
Complex data transformations
Rationale: These features would make artifacts Turing-complete, which:

Makes review harder (security/compliance risk)
Increases replay complexity (debugging, error handling)
Reduces determinism (more edge cases)
For complex workflows, the solution is composition: chain multiple simple artifacts rather than building one complex artifact.

### Determinism & Error Handling
Deterministic replay means same inputs → same outputs, with no LLM in the loop. The replay engine (replay.py) achieves this through:

Error Taxonomy — 3 classes:

Expected Business Outcomes ("Member not found", "Insufficient balance") — not failures, just legitimate results. Detected via step.expected_errors text/element matching, returned as BUSINESS_OUTCOME with structured data.
Recoverable Conditions (transient network errors, slow loads, unexpected dialogs) — handled via retry w/ exponential backoff, dismissing known interstitials, waiting for element stability.
Hard Failures (element not found after retries, timeout, permission denied, session expired) — stop immediately, return HARD_FAILURE with failed step ID, expected vs. observed state, screenshot, and full trace. Continuing risks data corruption.

Error Detection:

Checkpoint verification — after each step, confirm expected state; fail hard if not met
Text-based detection — scan page content against known error-indicator strings → classify as business outcome
Stuck detection — StuckDetector hashes state (URL + DOM) and escalates after N repeats (default 5), preventing infinite loops

UI Drift Handling:

Locator fallbacks — primary locator has an ordered fallback chain (alt accessibility label → text match → XPath → CSS ID)
Artifact versioning — semver bumps on UI changes, old versions kept for rollback
Confidence scoring (future) — track per-artifact success rate; flag/re-discover if it drops below threshold (e.g. 80%)


### Heterogeneity
Surface Abstraction - The Surface interface (base.py) is the seam between "how we perceive/act" and "the recorded flow":
Extending to Legacy Web Apps - Challenge: Legacy apps have:
1. Server-rendered HTML (no React/Vue)
2. Framesets and nested iframes
3. Table-based layouts
4. No test IDs or semantic markup

Solution:
1. Visual Locators -  For apps without accessibility markup, use visual landmarks
2. Text-Based Locators - For table-based layouts, use visible text
3. Composite Strategies - Combine multiple strategies with priority
4. Extending to Desktop Apps, Challenge: Desktop apps (Windows, macOS) have no DOM. Accessibility API Surface

### Multi-Tenant Reuse
Challenge: Hundreds of tenants run the same vendor app (e.g., "CoreBanking v5.2") with:
For example: 
Different branding (logos, colors, labels)
Different configurations (enabled features)
Different versions (5.2.1 vs. 5.2.3)
Solution:
1. Base Artifacts + Tenant Overrides - // Base artifact (shared across tenants) & // Tenant-specific override (Tenant A)

// Base artifact (shared across tenants)
{
  "artifact_id": "cap_corebanking_member_lookup",
  "version": "1.0.0",
  "tenant_id": null,
  "steps": [
    {
      "step_id": 1,
      "action": "click",
      "locator": {
        "strategy": "accessibility",
        "primary": "textbox:Member ID"
      }
    }
  ]
}

// Tenant-specific override (Tenant A)
{
  "artifact_id": "cap_corebanking_member_lookup_tenant_a",
  "version": "1.0.0",
  "tenant_id": "tenant_a",
  "base_artifact_id": "cap_corebanking_member_lookup",
  "overrides": {
    "steps": {
      "1": {
        "locator": {
          "primary": "textbox:Member Number"
        }
      }
    }
  }
}

2. Parameterized Locators - Use templates for tenant-specific values
3. Drift Detection - Track replay success rate per tenant
4. Version Pinning - Artifacts specify compatible app versions:

###  Escalation & Handoff
1. Stuck Detection - The StuckDetector (detector.py) identifies when automation cannot proceed
2. State Loop Detection - Tracks state hashes (URL + DOM snapshot):
3. Timeout Detection - If a step exceeds timeout_ms, escalate:
4. Unrecoverable Errors - If all retries fail and error is not in expected_errors, escalate
5. Handoff Mechanism - The HandoffManager (handoff.py) implements the control transfer,1. Pause Automation 2. Expose Live Session The browser session remains open and accessible. 3. Capture Human Actions Record what the human did 4. Resume Automation - After handoff, resume from next step

1. Pause Automation
### Control Transfer Model
┌──────────────┐
│  AUTOMATED   │ ◀─┐
└──────┬───────┘   │
       │           │
       │ (stuck)   │ (resume)
       ▼           │
┌──────────────┐   │
│  ESCALATED   │───┘
└──────┬───────┘
       │
       │ (timeout/abort)
       ▼
┌──────────────┐
│   FAILED     │
└──────────────┘

# Session Ownership:
Automated: System controls browser
Escalated: Human controls browser, system waits
Failed: Session closed, execution aborted

# Evidence Preservation:
Screenshot before escalation
Screenshot after human intervention
Diff of DOM changes
Human action log

# Production Handoff Design For production, the handoff would use:
1. Operator Console (Web UI)
Real-time view of browser session (VNC/RDP)
Intervention queue (prioritized by SLA)
Action recording (clicks, types, navigation)
2. Session Sharing (Technical)
Playwright CDP: Share Chrome DevTools Protocol connection
VNC: Remote desktop to automation server
Browser extension: Inject control panel into live page
3. Workflow
Automation detects stuck state
Creates intervention request in queue
Operator claims request
Operator sees live browser + context (artifact, step, error)
Operator completes step manually
Operator clicks "Resume" → automation continues

### Safety
1. Guardrail Model: The GuardrailEngine (guardrails.py) enforces safety policies: 
        a. Domain Allowlist Only permit navigation to approved domains:
        b. Route allowlist Permit only specific URL patterns:
        c. Action Classification - Classify actions by risk:
        d. Risky Action Handling = For risky actions, require human confirmation
        e. PII Redaction - The Redactor (redaction.py) removes sensitive data
        f. Artifact Redaction - Before saving artifacts, redact PII
        g. Log Redaction Redact logs before writing
        h. Secrets Management - Never Persist Secrets Credentials are never stored in artifacts,Secrets come from environment

### Limits - Current guardrails do NOT protect against:
1. Malicious artifacts: A hand-crafted artifact could bypass allowlists. Mitigation: Artifact review/approval workflow before production.
2. Privilege escalation: If the automation account has admin access, guardrails can't prevent misuse. 3. Data exfiltration: An artifact could extract sensitive data and send it to an external URL. 
4. Replay timing attacks: Carefully timed replays could exploit race conditions. 

### Cuts - What Was Deliberately Left Out
1. Operator Console – handoff mechanism works; needs WebSocket streaming + React dashboard UI
2. Desktop Surface – abstraction/schema ready; needs OS-specific accessibility API code (pyobjc/pywinauto/pyatspi2)
3. Multi-Tenant Artifacts – schema ready; needs Postgres registry + Celery jobs for drift detection
4. Visual Locators – schema ready; needs OpenCV template matching for the long-tail cases accessibility locators miss
5. Test Suite – currently manual-only; needs pytest coverage + CI/CD
6. Artifact Approval Workflow – versioning exists; needs approval states, success-rate tracking, auto re-discovery

####  What Would Be Built Next

Priority 1: Production Hardening
Error recovery: Retry logic for transient failures, circuit breakers
Monitoring: Prometheus metrics, Grafana dashboards
Alerting: PagerDuty integration for stuck/failed runs
Audit logging: Immutable audit trail for compliance
LLM optimization: Prompt caching, keywords optimization, Context store.

Priority 2: Operator Experience

Operator console: Real-time session sharing, intervention queue
Action recording: Capture human actions during handoff
Playback: Replay human actions for training/debugging
Priority 3: Multi-Tenant Scale

Artifact registry: PostgreSQL database for artifacts
Tenant config: API for tenant-specific overrides
Drift detection: Background jobs to detect UI changes
Auto-remediation: Re-run discovery when drift detected
Priority 4: Advanced Locators

Visual locators: OpenCV template matching
AI-powered locators: Use vision models to find elements
Self-healing: Automatically update locators when UI changes
Priority 5: Developer Experience

Artifact IDE: Visual editor for creating/editing artifacts
Test harness: Replay artifacts against mock surfaces
Code generation: Generate Playwright/Selenium code from artifacts