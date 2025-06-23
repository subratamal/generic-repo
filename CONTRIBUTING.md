# Contributing to Generic DynamoDB Repository

Thank you for your interest in contributing to the Generic DynamoDB Repository! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- AWS account (for integration testing)

### Development Setup

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/subratamal/generic-repo.git
   cd generic-repo
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Development Dependencies**
   ```bash
   pip install -e .[dev]
   ```

4. **Set up Pre-commit Hooks (Optional but Recommended)**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## 🧪 Running Tests

### Unit Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=generic_repo --cov-report=html

# Run specific test file
pytest tests/test_generic_repo.py

# Run tests matching a pattern
pytest -k "test_save"
```

### Integration Tests
```bash
# Run integration tests (requires AWS credentials)
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Test Coverage
We aim for at least 80% test coverage. Check coverage with:
```bash
pytest --cov=generic_repo --cov-report=html
open htmlcov/index.html  # View coverage report
```

## 🎨 Code Style

This project follows strict code quality standards:

### Formatting and Linting
```bash
# Format code with Ruff
ruff format .

# Check for linting issues
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Type Checking
```bash
# Run type checking (when mypy is added)
mypy generic_repo/
```

### Security Checks
```bash
# Run security linting
bandit -r generic_repo/
```

## 📝 Development Workflow

### 1. Create a Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Write your code following the existing patterns
- Add comprehensive docstrings
- Include type hints
- Write tests for new functionality
- Update documentation if needed

### 3. Test Your Changes
```bash
# Run the full test suite
pytest

# Check code quality
ruff check .
ruff format --check .
```

### 4. Commit Your Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for adding tests
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear Description**: What you expected vs. what happened
2. **Reproduction Steps**: Minimal code to reproduce the issue
3. **Environment**: Python version, OS, package version
4. **Error Messages**: Full stack traces if applicable

**Bug Report Template:**
```markdown
## Bug Description
Brief description of the bug.

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- Python version:
- Package version:
- OS:
- AWS region (if applicable):

## Additional Context
Any other relevant information.
```

## 💡 Feature Requests

For feature requests, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** clearly
3. **Explain the expected behavior**
4. **Consider backward compatibility**

**Feature Request Template:**
```markdown
## Feature Description
Brief description of the proposed feature.

## Use Case
Explain why this feature would be useful.

## Proposed Solution
Your ideas on how to implement this.

## Alternatives Considered
Other approaches you've considered.

## Additional Context
Any other relevant information.
```

## 🔄 Pull Request Guidelines

### Before Submitting
- [ ] Tests pass locally (`pytest`)
- [ ] Code is formatted (`ruff format .`)
- [ ] No linting errors (`ruff check .`)
- [ ] Documentation is updated (if applicable)
- [ ] CHANGELOG.md is updated (for significant changes)

### Pull Request Description
Include:
- **Summary** of changes
- **Related issue** (if applicable)
- **Testing** information
- **Breaking changes** (if any)

**PR Template:**
```markdown
## Summary
Brief description of the changes.

## Related Issue
Closes #issue_number

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed

## Breaking Changes
None / List any breaking changes

## Additional Notes
Any additional information for reviewers.
```

## 📋 Code Review Process

1. **Automated Checks**: All CI checks must pass
2. **Code Review**: At least one maintainer review required
3. **Testing**: Comprehensive test coverage expected
4. **Documentation**: Must be clear and complete

### Review Criteria
- Code quality and maintainability
- Test coverage and quality
- Documentation completeness
- Performance considerations
- Security implications
- Backward compatibility

## 🚀 Release Process

### Versioning
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a GitHub release
4. Package is automatically published to PyPI

## 📚 Documentation

### Code Documentation
- Use comprehensive docstrings for all public methods
- Follow Google-style docstring format
- Include type hints for all function parameters and return values
- Add usage examples where helpful

### README Updates
- Keep examples current
- Update feature lists
- Maintain accurate installation instructions

## 🤝 Community Guidelines

### Be Respectful
- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Be Collaborative
- Help others learn and grow
- Share knowledge and resources
- Support fellow contributors
- Celebrate successes together

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: 06.subrat@gmail.com for private matters

## 🙏 Recognition

Contributors will be recognized in:
- README.md acknowledgments
- Release notes
- GitHub contributors list

Thank you for contributing to Generic DynamoDB Repository! 🎉 