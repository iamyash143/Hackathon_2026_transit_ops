# MERGE_CHECKLIST.md

Every Pull Request into `main` must satisfy this checklist before merge. The PR author self-checks before requesting review; the reviewer re-verifies before approving. Do not skip items under time pressure — a broken `main` costs the whole team more time than a careful merge.

## 1. General

- [ ] The PR description states what changed and which document (in `00_COMMON_CONTEXT` or a `PHASE_0X` folder) it implements.
- [ ] The branch is up to date with `main` (rebased or merged recently) and has no unresolved conflicts.
- [ ] No commented-out code blocks, no `print()` debug statements left in, no `TODO`/`FIXME`/placeholder logic.
- [ ] No secrets (API keys, passwords, tokens) committed anywhere, including in test fixtures or `.env` files.

## 2. Schema and Constants Consistency

- [ ] Any new or changed model field matches `DATABASE_SCHEMA.md` exactly — if it doesn't, `DATABASE_SCHEMA.md` was updated in this same PR.
- [ ] Any new or changed status choice, role name, permission, or threshold matches `SHARED_CONSTANTS.md` exactly — if it doesn't, `SHARED_CONSTANTS.md` was updated in this same PR.
- [ ] No status string, role name, or threshold is hardcoded inline anywhere it should instead reference a `choices.py`/`constants.py` value.

## 3. Django Conventions

- [ ] New files are located per `PROJECT_STRUCTURE.md` (correct app, correct subfolder).
- [ ] Migrations are included for every model change, have been run locally against a fresh database, and were reviewed (not blindly accepted from `makemigrations` auto-output).
- [ ] `DecimalField` is used for all money/weight/capacity fields — no `FloatField` in the diff for these.
- [ ] Every `ForeignKey` has an explicit `on_delete` matching the rule in `DATABASE_SCHEMA.md` Section 10.
- [ ] Every model has `Meta.ordering` set.

## 4. Business Logic and FSM

- [ ] Any state-changing operation goes through a `django-fsm-2` `@transition` method — no direct `.status = ...` assignment outside the model file.
- [ ] Every business rule from `PROJECT_OVERVIEW.md` Section 7 touched by this PR is enforced at the model/FSM layer, not only in a form or template.
- [ ] Multi-model side effects (e.g. dispatch changing Trip + Vehicle + Driver) are wrapped in `transaction.atomic()`.
- [ ] Illegal transitions are proven to fail — not just legal transitions proven to succeed.

## 5. Views, Forms, and Templates

- [ ] Every non-login view is protected by `@login_required`/`LoginRequiredMixin`.
- [ ] Every view that should be role-restricted uses `@permission_required`/`PermissionRequiredMixin` matching the matrix in `SHARED_CONSTANTS.md` Section 3.
- [ ] Standard CRUD forms use `ModelForm` + `django-crispy-forms`; no raw hand-written `<form>` HTML for these.
- [ ] HTMX partial views return only the fragment needed, targeting the correct DOM ID per `SHARED_CONSTANTS.md` Section 8.
- [ ] Templates extend `base.html` and use Tailwind utility classes consistent with existing pages; dark mode (`dark:` variants) is not broken by new markup.

## 6. Testing

- [ ] New/changed models with FSM transitions have tests for both the legal path and at least one illegal path.
- [ ] New/changed business rules have a corresponding test per `DEVELOPMENT_RULES.md` Section 6.
- [ ] `python manage.py test` passes locally with no failures or errors before opening the PR.
- [ ] No test was skipped or commented out to make the suite pass.

## 7. Code Style

- [ ] Code has been run through `black` and `isort`.
- [ ] No PEP 8 violations reported by the project's linter configuration.
- [ ] Every model class and every FSM transition method has a docstring.

## 8. AI-Generated Code (if applicable)

- [ ] AI-generated code was reviewed against `AI_GUIDELINES.md` Section 6 before inclusion.
- [ ] No fabricated/nonexistent library APIs are present (spot-checked against the actual installed package version).
- [ ] AI did not introduce scope creep beyond the task's stated requirements.

## 9. Security

- [ ] CSRF protection is intact on all forms and HTMX POST/PUT/DELETE requests.
- [ ] Any file upload handling (vehicle documents) validates file type and size server-side.
- [ ] No sensitive data is written to logs.

## 10. Documentation

- [ ] If this PR changes shared behavior (models, constants, structure, workflow), the corresponding file in `00_COMMON_CONTEXT` was updated in the same PR — not left for a "follow-up."
- [ ] If this PR implements a feature described in a `PHASE_0X` document, that document's acceptance criteria are actually met.

## 11. Final Sanity Check Before Merge

- [ ] Pulled the branch fresh, ran migrations from scratch, and clicked through the affected feature manually in the browser.
- [ ] No console errors in the browser dev tools on the affected pages.
- [ ] The specific example workflow step(s) from `PROJECT_OVERVIEW.md` Section 8 relevant to this PR still work end-to-end.

**If any box cannot be checked, the PR does not merge until it can — including in the final hour of the hackathon.** A visibly broken `main` during the demo is worse than a feature that ships ten minutes later.
