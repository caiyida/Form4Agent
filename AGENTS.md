# Form4Agent Working Instructions

## Scope and autonomy

These instructions apply to the entire repository.

- Work autonomously on implementation tasks. Inspect the codebase, choose a reasonable implementation approach, make the change, and verify it without asking the user to make routine technical decisions.
- Prefer the smallest safe change that satisfies the requirement. Avoid unrelated rewrites, cleanup, dependency upgrades, or formatting churn.
- Preserve pre-existing and unrelated worktree changes. Do not revert, overwrite, or incorporate them into the task unless necessary and explicitly in scope.
- When a command or test fails, investigate the cause, fix failures caused by the task, rerun the relevant checks, and continue iterating. Do not stop at the first failure.
- Ask the user only when genuinely blocked by a product or business decision, a missing credential, an external permission, or a requirement that cannot reasonably be inferred.
- Do not delete or overwrite user files unless the task explicitly requires it.

## Project purpose and architecture

Form4Agent is a Python MVP with one smart upload interface for preparing a Singapore Form 4 or completing a customer-signed one. Uploaded JPG, JPEG, PNG, and PDF content is classified through the OpenAI Responses API. Identity and property source files populate an unsigned customer version from a fixed `.docx` template; one recognised Form 4 enters the explicit salesperson-signing flow. A legacy CLI path also exists.

Product requirements and confirmed business behavior live in `FEATURES.md`. Read it before any task that changes user-visible behavior.

The current processing flow is:

1. `app.py` keeps uploads in memory and exposes the address override plus compact detail editor.
2. `src/json_builder.py` and `src/document_reader.py` classify the content as identity, property material, Form 4, or unknown and return only the needed structured fields.
3. Identity/property inputs are normalized and validated, then `src/form4_engine.py` fills a template copy through surgical XML-safe replacement in `src/word_helper.py`.
4. The customer version removes only the salesperson mark drawings and is converted to PDF when LibreOffice is available.
5. For a single recognised Form 4, `src/pdf_helper.py` finds the salesperson signature line from PDF text or OCR, applies the signature above that line, and applies the template initial position to every uploaded page.
6. All web artifacts remain session-scoped and in memory. The legacy CLI uses `input/` and `output/` and also requests PDF conversion.

This is currently a synchronous application. Imports in the app and source files assume `src/` is on `sys.path`; it is not an installed Python package. The web flow is session-scoped and in-memory, while the CLI retains a local-filesystem workflow.

## Important files and responsibilities

- `app.py`: Streamlit entry point, in-memory upload handling, per-session review/edit state, validation feedback, generation, download, and explicit session-data clearing.
- `FEATURES.md`: product source of truth for classification, UI, defaults, document variants, signing, delivery, and hosting behavior.
- `src/config.py`: repository paths, template/input/output locations, and creation of local input/output directories.
- `src/document_reader.py`: OpenAI client setup, identity/property/Form 4 classification, multimodal structured extraction, and safe error translation. This handles highly sensitive identity data.
- `src/form_rules.py`: Singapore-local agreement date defaults and the stepped commission calculation.
- `src/pdf_helper.py`: renders PDFs to in-memory page images, normalizes signed uploads, converts DOCX through headless LibreOffice, locates the salesperson line through text/OCR, and applies signature/initial images.
- `src/json_builder.py`: invokes smart classification, collects a property address, maps up to four identities, and supplies confirmed defaults. It also supports the legacy CLI input directory.
- `src/validator.py`: required-field policy before generation.
- `src/form_loader.py`: opens `templates/Form4_Template.docx` with `python-docx`.
- `src/word_helper.py`: XML-safe text-node placeholder discovery/replacement across body paragraphs, nested table cells, headers, and footers.
- `src/form4_engine.py`: document-generation orchestration and final `.docx` save.
- `src/main.py`: CLI pipeline, including Word-to-PDF conversion.
- `templates/Form4_Template.docx`: immutable layout source of truth unless the user explicitly requests a template change.
- `test/test_template_invariants.py`: authoritative regression checks for placeholders, sections, table geometry, signature/initial anchors, positions, and image relationships.
- `test/`: hermetic unit, Streamlit smoke, and Word template regression tests. OpenAI behavior is exercised only through fake clients.
- `requirements.txt`: pinned runtime and development dependencies.

## Setup and running the application

Use a repository-local virtual environment. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Set `OPENAI_API_KEY` in the environment or a gitignored root `.env` file. Never display, log, commit, or place the key in source code.

Run the Streamlit application from the repository root so relative `input/` paths resolve correctly:

```bash
streamlit run app.py
```

Render deploys through the repository `Dockerfile` and `render.yaml`. The image installs headless LibreOffice so the customer review PDF can be created on Linux. Keep the service in Singapore on the free plan unless the user explicitly changes the hosting decision.

Run the CLI pipeline with:

```bash
python src/main.py
```

Web PDF conversion uses headless LibreOffice and falls back to DOCX when it is unavailable. The legacy CLI still uses `docx2pdf`, which depends on a compatible local Microsoft Word installation. Word generation itself does not require PDF conversion.

## Automated tests

Run the full hermetic test suite from the repository root with:

```bash
python -m unittest discover -s test -v
```

Run only the Word template regression suite with:

```bash
python -m unittest discover -s test -p 'test_template_invariants.py' -v
```

The same commands may be run as `.venv/bin/python ...` when the virtual environment is not activated. Do not use `python -m unittest test.test_template_invariants`: `test/` is not currently a Python package.

For future behavior changes, add focused automated tests that mock the OpenAI client and use synthetic/non-sensitive fixtures. Automated tests must never make real OpenAI API calls.

## Known technical risks

- `python-docx` paragraph/run mutation can silently rewrite WordprocessingML and remove or alter floating drawings. Keep replacement limited to existing text nodes and rely on the invariant suite to detect regressions.
- Placeholder text may be split across Word runs. Replacement must preserve styling and layout-critical XML while handling split placeholders, repeated placeholders, and replacement strings of different lengths.
- Values containing placeholder-like `{{...}}` text are rejected by the generator as unresolved output; do not silently strip intentional user text without a product decision.
- Uploads, PDF page images, generated Word/PDF files, and extracted fields contain identity information. The web flow processes files in memory, but the legacy CLI still uses disk-backed `input/`, `temp/`, and `output/` paths that can retain data between operations.
- OpenAI extraction uses typed Structured Outputs, but document interpretation remains probabilistic and requires user review.
- The unused legacy path-based PDF helper writes page images to `temp/` without lifecycle cleanup; do not reintroduce it into the web flow.
- Model names, API behavior, and third-party library behavior can change. Keep external calls behind mockable boundaries and do not make network-dependent assertions in automated tests.
- PDF conversion is platform-dependent, and relative-path assumptions make execution outside the repository root unreliable.
- Final PDF signing depends on finding the salesperson label through embedded PDF text or Tesseract OCR. Fail closed if the content-relative signature line cannot be found; never substitute a page-fixed guessed signature position merely to return a file.

## Word document generation rules

- `templates/Form4_Template.docx` is the layout source of truth.
- Do not modify the Word template unless the user explicitly requests a template change.
- Preserve the existing page layout and signature position.
- Preserve all seven initial positions.
- Preserve drawing anchors, image relationships, sections, tables, headers, footers, and all other layout-critical XML.
- Missing values must become blank strings, never placeholder characters or substitute glyphs.
- Generated documents must not contain unresolved `{{...}}` placeholders anywhere in the document package.
- Treat placeholder replacement as a surgical XML-sensitive operation. Avoid reconstructing whole paragraphs, tables, sections, or documents when a targeted edit is possible.
- Run the template invariant regression tests after any change that could affect template loading, field mapping, placeholder replacement, document saving, or Word/PDF generation.
- Never weaken, delete, skip, or change regression-test expectations or baselines merely to make tests pass. Baseline changes are allowed only for an explicitly requested template/layout change and must reflect the reviewed source-of-truth template.
- For a document-generation change, inspect a generated `.docx` as needed to confirm all placeholders are resolved and the requested values appear. Use synthetic test values, not real customer identity data.

## Privacy and data handling

- Treat uploaded documents, rendered PDF pages, extracted names, passport numbers, NRICs, FINs, addresses, and generated customer documents as sensitive personal data.
- Never expose API keys. Do not print environment variables, authorization headers, full client objects, or credential fragments.
- Do not print or unnecessarily retain passport, NRIC, FIN, or other identity-document information in logs, exceptions, test output, screenshots, telemetry, or debug artifacts. Redact identifiers if diagnostic context is essential.
- Minimize collection and retention. Read only the files required for the task, avoid copying sensitive fixtures, and clean up task-created temporary identity artifacts when safe and in scope.
- Do not inspect real identity documents merely to test unrelated behavior. Prefer synthetic fixtures and mocked extraction responses.
- Do not commit `.env` files, secrets, identity documents, uploaded customer data, generated customer `.docx`/`.pdf` files, rendered document images, temporary Office lock files such as `~$*.docx`, or other sensitive artifacts.
- Before adding files to Git or reporting a diff, check that no sensitive or generated artifact was accidentally included.
- Do not send identity data to any external service except the explicitly configured extraction service in the user-requested application flow. Automated tests must remain offline from that service.

## Definition of done

A development task is not complete merely because code was written. Before declaring completion:

1. Confirm the requested user-facing behavior works through the relevant UI, CLI, or focused integration path.
2. Add or update automated tests whenever behavior changes, using mocks and non-sensitive fixtures for external/API paths.
3. Run the relevant automated tests. For document-generation changes, always run the full template invariant suite.
4. Investigate every failure, determine whether it is caused or exposed by the change, fix applicable defects, and rerun until the relevant suite passes. Do not hide failures by skipping tests or altering baselines.
5. Check adjacent behavior for regressions, including error handling, missing/blank values, unresolved placeholders, and privacy-sensitive output.
6. Review `git diff` and `git status` for unintended edits, deleted user files, secrets, identity data, generated documents, temporary Office files, and unrelated formatting changes.
7. Report concisely what changed, what exact checks were run and their results, and any genuine remaining risks or blockers. Clearly distinguish pre-existing failures from new failures, but do not use a pre-existing defect to excuse a regression.
