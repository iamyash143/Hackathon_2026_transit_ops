# 00_COMMON_CONTEXT

## Purpose of This Folder

This folder is the **single source of truth** for anything that applies across the entire TransitOps project. Before writing a single line of code, every developer (human or AI) must read this folder first. Every other phase folder (`PHASE_01_FOUNDATION` through `PHASE_06_TESTING`) assumes the reader already knows the contents of `00_COMMON_CONTEXT`.

If a rule, naming convention, schema definition, or workflow described in a later phase document ever conflicts with something in this folder, **this folder wins**. Open an issue / raise it in the team channel immediately rather than silently picking one.

## Who Must Read This Folder

- Every human developer on the team, before their first commit.
- Every AI coding assistant (Claude, Gemini, ChatGPT, Copilot, etc.), as system/context input before generating any code for this project.
- Anyone reviewing a Pull Request, as the baseline against which the PR is judged.

## Documents in This Folder

| # | File | What It Covers | Read Before |
|---|------|-----------------|--------------|
| 1 | `PROJECT_OVERVIEW.md` | Business context, target users, roles, functional requirements, mandatory business rules, deliverables, bonus features, success criteria | Anything |
| 2 | `DEVELOPMENT_RULES.md` | Django coding conventions, architecture rules, naming standards, security rules, testing rules | Writing any code |
| 3 | `PROJECT_STRUCTURE.md` | The exact Django project/app folder layout, settings structure, static/template structure | Creating any file or app |
| 4 | `DATABASE_SCHEMA.md` | Full entity-relationship schema, field types, constraints, indexes, relationships | Writing any model |
| 5 | `SHARED_CONSTANTS.md` | Status choices, role names, permission codenames, thresholds, formulas used everywhere | Writing any model, view, or business logic |
| 6 | `TEAM_WORKFLOW.md` | Git branching strategy, hour-by-hour hackathon execution plan, task ownership, communication rules | Starting any work session |
| 7 | `AI_GUIDELINES.md` | How to prompt AI coding assistants correctly for this codebase, what AI must and must not do | Using any AI assistant |
| 8 | `MERGE_CHECKLIST.md` | The checklist every PR must satisfy before merging into `main` | Opening any Pull Request |

## How to Use This Documentation Set

1. **Read in order.** `PROJECT_OVERVIEW.md` → `DEVELOPMENT_RULES.md` → `PROJECT_STRUCTURE.md` → `DATABASE_SCHEMA.md` → `SHARED_CONSTANTS.md`. `TEAM_WORKFLOW.md`, `AI_GUIDELINES.md`, and `MERGE_CHECKLIST.md` can be read in any order after the first five.
2. **Do not duplicate content.** If you need a status choice, a role name, or a formula, reference `SHARED_CONSTANTS.md` — do not redefine it in a feature document or in code comments.
3. **Feature documents in later phases must not contradict this folder.** Every `PHASE_0X` document references entities and constants defined here by name (e.g. `Vehicle.status`, `TRIP_STATUS_CHOICES`).
4. **When in doubt, this folder is authoritative.** If a later phase document is ambiguous, the definitions here take precedence.

## Project Snapshot

- **Project Name:** TransitOps — Smart Transport Operations Platform
- **Format:** 8-hour hackathon build, structured as a production-quality MVP
- **Backend:** Django 5.x, PostgreSQL
- **Frontend:** Django templates + HTMX + Tailwind CSS v4 + Flowbite, minimal custom JavaScript
- **Core Pattern:** Server-rendered UI with HTMX partial swaps, Finite State Machine–governed business logic (`django-fsm-2`), Role-Based Access Control via Django Groups
- **Roles:** Fleet Manager, Driver, Safety Officer, Financial Analyst
- **Core Entities:** User, Vehicle, Driver, Trip, MaintenanceLog, FuelLog, ExpenseLog

## Document Maintenance Rules

- Any change to a model field, status choice, role permission, or folder structure **must** be reflected in this folder in the same Pull Request that makes the change.
- Do not leave this folder stale. A stale `00_COMMON_CONTEXT` is worse than no documentation, because it actively misleads developers and AI assistants.
- The person who changes shared behavior owns updating the shared docs. This is not optional and is checked in `MERGE_CHECKLIST.md`.
