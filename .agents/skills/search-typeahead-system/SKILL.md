```markdown
# search-typeahead-system Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the development patterns and conventions used in the `search-typeahead-system` Python codebase. You'll learn how to structure files, write and organize code, follow commit message standards, and implement and test features in a consistent, maintainable way. This guide is ideal for contributors aiming to quickly onboard and maintain code quality.

## Coding Conventions

### File Naming
- Use **snake_case** for all file and module names.
  - Example: `search_engine.py`, `typeahead_utils.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import normalize_query
    from .models import SearchResult
    ```

### Export Style
- Use **named exports**; explicitly define what is exported from each module.
  - Example:
    ```python
    __all__ = ['TypeaheadEngine', 'SearchResult']
    ```

### Commit Messages
- Follow **Conventional Commits**.
- Prefixes: `feat` (for new features), `chore` (for maintenance).
- Keep messages concise (~51 characters on average).
  - Example:
    ```
    feat: add fuzzy matching to typeahead results
    chore: update dependencies and clean up imports
    ```

## Workflows

### Feature Development
**Trigger:** When adding a new feature or capability  
**Command:** `/feature-dev`

1. Create a new branch for your feature.
2. Implement the feature using snake_case files and relative imports.
3. Add or update tests in a corresponding `*.test.*` file.
4. Commit changes with a `feat:` prefix and descriptive message.
5. Open a pull request for review.

### Maintenance or Chores
**Trigger:** When making non-feature changes (e.g., refactoring, dependency updates)  
**Command:** `/chore`

1. Create a new branch for the maintenance task.
2. Make the necessary changes (e.g., update dependencies, refactor code).
3. Commit changes with a `chore:` prefix and concise description.
4. Open a pull request for review.

### Testing
**Trigger:** Before merging or after implementing changes  
**Command:** `/test`

1. Identify or create test files matching `*.test.*`.
2. Run all tests using the project's preferred test runner (framework not specified; check project docs or use `pytest` as a default).
3. Ensure all tests pass before merging.

## Testing Patterns

- Test files follow the pattern `*.test.*` (e.g., `search_engine.test.py`).
- The specific testing framework is not specified; use standard Python testing practices.
- Place tests alongside or near the code they test.
- Example test structure:
  ```python
  # search_engine.test.py
  from .search_engine import TypeaheadEngine

  def test_typeahead_basic():
      engine = TypeaheadEngine(["apple", "banana", "apricot"])
      results = engine.suggest("ap")
      assert "apple" in results
      assert "apricot" in results
  ```

## Commands
| Command         | Purpose                                         |
|-----------------|-------------------------------------------------|
| /feature-dev    | Start a new feature development workflow         |
| /chore          | Start a maintenance or refactoring workflow      |
| /test           | Run all tests in the codebase                    |
```