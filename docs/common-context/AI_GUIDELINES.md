# AI_GUIDELINES.md

TransitOps is built with heavy assistance from AI coding tools (Claude, Gemini, ChatGPT, GitHub Copilot, or equivalents). This document defines how to prompt those tools correctly and what standards their output must meet before it can be merged. It applies equally whether a human is pasting a prompt into a chat interface or an autonomous coding agent is operating directly on the repository.

## 1. Core Principle

**An AI assistant's output is a first draft, not a merge-ready artifact.** The human developer who requested the AI-generated code is responsible for verifying it against this documentation set before opening a PR. "The AI wrote it" is never an acceptable justification for code that violates `DEVELOPMENT_RULES.md` or `DATABASE_SCHEMA.md`.

## 2. Required Context for Every AI Prompt

Every prompt given to an AI assistant for TransitOps work should include, or reference, the following — do not ask an AI to generate model, view, or business-logic code from the feature description alone:

1. The relevant section(s) of `PROJECT_OVERVIEW.md` (business rules and functional requirements being implemented).
2. The exact model/field definitions from `DATABASE_SCHEMA.md` for any entity being touched.
3. The exact status choices and constants from `SHARED_CONSTANTS.md` — never let the AI invent its own status strings or thresholds.
4. The relevant conventions from `DEVELOPMENT_RULES.md` (e.g. "use `django-fsm-2` transitions, not raw status assignment"; "use `DecimalField` for money").
5. The exact file path from `PROJECT_STRUCTURE.md` where the output belongs.
6. The specific feature document from the relevant `PHASE_0X` folder, if one already exists for this feature — those documents include a ready-to-use AI implementation prompt at the end; prefer using that prompt verbatim over writing a new one.

## 3. Standard Prompt Template

When no phase-specific prompt exists yet, use this template:

```
Context: TransitOps Django project. [paste or summarize relevant PROJECT_OVERVIEW.md section]

Model schema (authoritative — do not deviate): [paste relevant DATABASE_SCHEMA.md section]

Constants to use (do not invent new values): [paste relevant SHARED_CONSTANTS.md section]

Conventions to follow:
- Business rules enforced in the model layer via django-fsm-2 transitions, not in views or templates.
- DecimalField for all money/weight values, never FloatField.
- Every view wrapped with login_required / LoginRequiredMixin and the correct permission_required.
- No placeholder code, no TODOs, no hardcoded stand-in data.
- Follow PEP 8, add docstrings to every model and transition method.

Task: [specific, narrow task — e.g. "Implement the Trip.dispatch() FSM transition, including the cargo weight guard and the atomic side effect of setting Vehicle and Driver status to ON_TRIP."]

File location: apps/trips/models.py

Output format: complete, runnable code for this file only. No explanation prose mixed into the code block.
```

## 4. What AI Assistants Must Always Do

- Reference the exact status/constant values from `SHARED_CONSTANTS.md` — e.g. `VehicleStatus.AVAILABLE`, never the raw string `"available"` inline in business logic.
- Implement business rule validation inside FSM transition guards or model `clean()` methods, not solely inside a view or a form's `clean_<field>()`.
- Use `django.db.transaction.atomic()` for any operation that changes more than one model instance together (e.g. dispatching a trip changes Trip, Vehicle, and Driver).
- Write complete, runnable code — no `# ... rest of implementation` truncation, no `pass` stubs standing in for real logic.
- Include docstrings and inline comments explaining *why* a business rule exists when the reason isn't obvious from the code alone.
- Match the exact file paths and app boundaries from `PROJECT_STRUCTURE.md`.

## 5. What AI Assistants Must Never Do

- Never invent a new status value, role name, or threshold not already defined in `SHARED_CONSTANTS.md`. If a new one seems genuinely necessary, flag it to the human rather than silently adding it.
- Never bypass the FSM by writing code that assigns directly to a `status` field (e.g. `vehicle.status = "on_trip"; vehicle.save()`).
- Never use `FloatField` for money, cargo weight, or load capacity.
- Never generate a raw HTML `<form>` for standard CRUD — use Django `ModelForm` + `django-crispy-forms`.
- Never hardcode API keys, database credentials, or other secrets into generated code — always reference `settings` values sourced from environment variables.
- Never generate a full new app structure that doesn't match `PROJECT_STRUCTURE.md` without being explicitly asked to propose a structural change.
- Never silently "fix" a business rule the human's prompt got wrong relative to `PROJECT_OVERVIEW.md` — flag the discrepancy instead of picking one interpretation.

## 6. Reviewing AI-Generated Code

Before including AI-generated code in a commit, the developer must verify:

1. **Correctness against the schema.** Field names, types, and constraints match `DATABASE_SCHEMA.md` exactly.
2. **Correctness against business rules.** Every rule in `PROJECT_OVERVIEW.md` Section 7 that's relevant to this code is actually enforced, and enforced at the model/FSM layer.
3. **No fabricated APIs.** AI assistants sometimes invent plausible-looking but nonexistent Django/library methods (e.g. a `django-fsm-2` API that doesn't exist in the pinned version). Check generated code against the actual installed package version's documentation.
4. **No silent scope creep.** The AI should not have added fields, views, or features beyond what was asked for and beyond what `DATABASE_SCHEMA.md` defines.
5. **Style compliance.** Runs cleanly through `black` and `isort`; no PEP 8 violations.
6. **Tests exist.** If the AI generated model or business logic code, it should also have been asked to generate the corresponding test(s) per `DEVELOPMENT_RULES.md` Section 6 — verify these were actually requested and included.

## 7. Using AI for Documentation

The same discipline applies when using AI to draft or update documentation in `docs/`:
- Provide the AI with the existing `00_COMMON_CONTEXT` files as context so new documents stay consistent in terminology, formatting, and cross-references.
- AI-drafted documentation must still follow the "no placeholders" rule — a documentation file with a `[fill in later]` marker is not acceptable output.
- Any AI-drafted change to `DATABASE_SCHEMA.md` or `SHARED_CONSTANTS.md` must be reviewed by a human before being treated as authoritative, since other developers' AI prompts will directly depend on it.

## 8. Escalation

If an AI assistant repeatedly produces output that violates these guidelines for a given task (e.g. keeps trying to bypass the FSM, keeps inventing constants), stop prompting variations and instead write that specific piece of logic by hand, or pair with a teammate. Do not spend hackathon time fighting an AI tool into compliance past a second or third attempt.
