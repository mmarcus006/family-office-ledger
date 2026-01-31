<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# e2e

## Purpose
End-to-end tests that verify complete user workflows across the full application stack (API + UI).

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `artifacts/` | Test artifacts - screenshots, logs, debug outputs |

## For AI Agents

### Working In This Directory
- E2E tests exercise full application stack
- Tests may use Selenium, Playwright, or similar browser automation
- Artifacts directory stores test outputs for debugging

### Testing Patterns
- Set up test database before tests
- Clean up after tests complete
- Store failure screenshots in `artifacts/`

### Testing Requirements
- Requires running API server
- May require running Streamlit UI
- Use fixtures for database setup/teardown

## Dependencies

### Internal
- Tests full application stack

### External
- `selenium` - Browser automation (optional)
- `pytest` - Test framework

<!-- MANUAL: -->
