# CLAUDE.md

Dev guide for this project. Concise, actionable.

**Architecture indexes:** [`backend/CLAUDE.md`](backend/CLAUDE.md) · [`frontend/CLAUDE.md`](frontend/CLAUDE.md) · [`telegram/CLAUDE.md`](telegram/CLAUDE.md)

**Memory:** `~/.claude/projects/-Users-danielmedina-Documents-claude-projects-games-the-lantern/memory/` (see `MEMORY.md` for index)

---

## 🎯 Core Philosophy

**KISS** - Simple > complex  
**YAGNI** - Build what's needed now, not what might be needed  
**Dependency Inversion** - Depend on abstractions  
**Open/Closed** - Extend, don't modify  
**Single Responsibility** - One purpose per unit  
**Fail Fast** - Check early, raise immediately

---

## 📐 Code Limits

| Unit | Max Lines | Rule |
|------|-----------|------|
| File | 500 | Split into modules if approaching |
| Function | 50 | Single responsibility |
| Class | 100 | Single concept |
| Line length | 100 | Ruff enforced |

**venv**: Use `venv_linux` for all Python commands

---

## 🛠️ Stack & Tools

### Primary Stack (BHVR)
- **Backend**: Bun + Hono  
- **Frontend**: Vite + React  

### Package Manager
```bash
# ALWAYS use bun, NEVER npm/yarn/pnpm
bun install              # Install deps
bun run <script>         # Run scripts
bun add <package>        # Add package
bun add -d <package>     # Dev dependency
bunx <package>           # Execute package

# use the full path: ~/.bun/bin/bun run dev
```

### Python Tools (UV)
```bash
# UV for Python package management
uv venv                  # Create venv
uv sync                  # Sync deps
uv add <pkg>            # Add package (NEVER edit pyproject.toml directly)
uv add --dev <pkg>      # Dev dependency
uv run <cmd>            # Run in venv

# Common commands
uv run pytest                        # Run tests
uv run pytest --cov=src             # With coverage
uv run ruff check .                 # Lint
uv run ruff check --fix .           # Lint + fix
uv run ruff format .                # Format
uv run mypy src/                    # Type check
```

---

## 🏗️ Architecture

Vertical slice architecture. Tests next to code.

```
src/project/
    main.py
    tests/test_main.py
    conftest.py
    
    database/
        connection.py
        models.py
        tests/
            test_connection.py
            test_models.py
    
    features/
        user_management/
            handlers.py
            validators.py
            tests/
                test_handlers.py
```

---

## 📋 Style

- **PEP8** with 100 char lines
- **Type hints** on all functions/classes
- **Double quotes** for strings
- **Trailing commas** in multi-line structures
- **Google-style docstrings** for public APIs
- **Pydantic v2** for validation

### Naming
```python
snake_case       # Variables, functions
PascalCase       # Classes, type aliases
UPPER_SNAKE_CASE # Constants, enum values
_leading         # Private attributes/methods
```

### Docstring Example
```python
def calculate_discount(price: Decimal, discount_percent: float) -> Decimal:
    """Calculate discounted price.

    Args:
        price: Original price
        discount_percent: Discount % (0-100)

    Returns:
        Final price after discount

    Raises:
        ValueError: If discount_percent not 0-100
    """
```
---

### Zod Schema Validation Rule

When adding/modifying API endpoints:

1. **Backend first:** Check the Pydantic response model in `backend/src/api/routes.py`
2. **Frontend schema:** Update corresponding Zod schema in `frontend/src/api/schemas.ts`
3. **Match ALL fields:** Include every field from backend response (use `.optional()` for nullable/optional fields)
4. **Keep `.strict()`:** Do NOT remove strict mode - it catches typos and unexpected data

**Common mistake:** Backend adds `slot: str | None = None` but frontend schema has `slot: z.string()` → Runtime error

**Correct pattern:**
```typescript
// Backend: slot: str | None = None
// Frontend: slot: z.string().optional()
````
---

## 🧪 Testing (TDD)

1. Write test first
2. Watch it fail
3. Write minimal code to pass
4. Refactor
5. Repeat

```python
# Use pytest fixtures
@pytest.fixture
def sample_user():
    return User(id=123, name="Test", email="test@example.com")

# Descriptive test names
def test_user_can_update_email_when_valid(sample_user):
    sample_user.update_email("new@example.com")
    assert sample_user.email == "new@example.com"

# Test edge cases
def test_user_update_email_fails_with_invalid_format(sample_user):
    with pytest.raises(ValidationError):
        sample_user.update_email("not-an-email")
```

**Coverage**: 80%+ on critical paths

---


## 🚨 Error Handling

```python
# Custom exceptions
class PaymentError(Exception):
    """Base for payment errors."""

class InsufficientFundsError(PaymentError):
    def __init__(self, required: Decimal, available: Decimal):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient: need {required}, have {available}")

# Specific handling
try:
    process_payment(amount)
except InsufficientFundsError as e:
    logger.warning(f"Payment failed: {e}")
    return PaymentResult(success=False, reason="insufficient_funds")

# Context managers for resources
@contextmanager
def database_transaction():
    conn = get_connection()
    trans = conn.begin_transaction()
    try:
        yield conn
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()
```

---

## 🔧 Configuration

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "MyApp"
    debug: bool = False
    database_url: str
    api_key: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---


## 🔄 Git Workflow

### Branches
- `main` - Production
- `develop` - Integration
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation
- `refactor/*` - Refactoring
- `test/*` - Tests

### Commits
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, test, chore

**NEVER mention Claude Code in commits**

---

## 🤖 Agent Orchestration

**YOU ARE AN ORCHESTRATOR FIRST, CODER SECOND**

### Core Principle: Context Injection

Agents do NOT read project docs themselves. The orchestrator:
1. Reads relevant files
2. Extracts the specific context each agent needs
3. Provides it in the launch prompt
4. Receives structured results back

Agents never write to STATUS.md. The orchestrator maintains it at session end.

### Available Agents

| Agent | Use When |
|-------|----------|
| **planner** | Create implementation-ready PRPs for new features |
| **dependency-manager** | Install packages, configure env vars |
| **fastapi-specialist** | Build Python REST APIs with FastAPI |
| **react-vite-specialist** | Build React components with Vite/Tailwind |
| **nextjs-specialist** | Build Next.js App Router pages |
| **typescript-architect** | Design type systems, domain models |
| **validation-gates** | Run tests, linting, type checking, builds |
| **code-reviewer** | Deep review: security, architecture, logic |
| **refactoring-specialist** | Execute refactoring identified by code-reviewer |
| **debugger** | Root cause analysis for complex bugs |
| **codebase-researcher** | Find existing patterns for new features |
| **documentation-manager** | Update README, CHANGELOG, API docs |
| **devops-engineer** | Docker, CI/CD, deployment |

### Adaptive Pipeline Depth

Not every change needs 6 agents:

| Change Type | Pipeline |
|-------------|----------|
| Bug fix | Orchestrator directly, or debugger |
| Small feature | tech-specialist → validation-gates |
| Large feature | /research-plan → tech-specialists → validation-gates |
| Refactor | code-reviewer → refactoring-specialist → validation-gates |
| Full-stack | [fastapi-specialist ∥ react-vite-specialist] → validation-gates |

### Anti-Patterns

- ❌ Telling agents to read STATUS.md/PLANNING.md (orchestrator provides context)
- ❌ Fixed 6-step pipeline for every change
- ❌ Running agents sequentially when parallel possible
- ❌ Implementing yourself when agent specializes

---

## 📚 Context7 MCP

**Use BEFORE implementing important files** to get context and best practices.

```python
# Resolve library ID first
mcp__context7__resolve_library_id(
    libraryName="fastapi",
    query="user authentication"
)

# Then query docs
mcp__context7__query_docs(
    libraryId="/tiangolo/fastapi",
    query="JWT authentication with OAuth2"
)
```

---

## 🚀 Quick Reference

### Daily Workflow
```bash
git checkout main && git pull origin main
git checkout -b feature/new-feature
# Make changes + tests
git push origin feature/new-feature
# Create PR → Review → Merge
```

### When to Orchestrate vs. Do Directly

**Orchestrate (use agents)**:
- Multiple files/domains
- Matches agent specialty
- Needs testing/validation
- Needs documentation
- Part of larger feature

**Do directly**:
- Single-line fixes
- Typos
- Quick questions
- Simple git ops
- Explain existing code

---

## 📊 Performance

- Profile before optimizing (`cProfile`, `py-spy`)
- Use `lru_cache` for expensive computations
- Prefer generators for large datasets
- `asyncio` for I/O-bound ops
- `multiprocessing` for CPU-bound

---

## 🛡️ Security

- No secrets in commits (use env vars)
- Validate input with Pydantic
- Parameterized DB queries
- Rate limiting on APIs
- Keep deps updated
- HTTPS for external comms
- Proper auth/authz

---

## ⚠️ Critical Rules

1. **NEVER ASSUME OR GUESS** - Ask for clarification
2. **Verify file paths/module names** before use
3. **Test your code** - No feature complete without tests
4. **Use agents proactively** - You're an orchestrator
5. **NEVER edit pyproject.toml directly** - Use `uv add`
6. **NEVER use npm/yarn/pnpm** - Use `bun`
7. **Run `eslint` and `tsc` before committing** - Catch errors before pre-commit hooks block you
8. **NEVER change config values without asking** - Model defaults, API keys, ports, env vars — always confirm first

---

_Living document. Update as project evolves._
