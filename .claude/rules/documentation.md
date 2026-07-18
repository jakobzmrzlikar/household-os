# Documentation Conventions

## Module Docstrings

Required on all modules. Keep minimal (1-3 sentences) without duplicating what filenames convey.

## Docstrings (API Documentation)

- **reST Sphinx style**: `:param:`, `:return:`, `:raises:` (NOT Google/NumPy)
- Imperative mood ("Calculate" not "Calculates")
- Omit `:type:` and `:rtype:` tags — type hints in signatures are sufficient
- Describe **behavior and contracts** (what it does, what it guarantees), not **implementation** (which libraries, algorithms, or data structures it uses internally). Implementation details belong in inline comments if they need explaining at all.

## Inline Comments

- Comment only when code isn't self-evident — explain WHY, not WHAT
- Include full context — no assumptions about prior knowledge or pairing
- Good use cases: race conditions, priority/fallback logic, complex regex, non-obvious business rules
