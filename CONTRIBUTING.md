# Contributing to SkyDock Panel

Thank you for your interest in contributing to SkyDock Panel! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/skydock-panel.git`
3. Create a branch: `git checkout -b feature/your-feature-name`

## Development Setup

See the [README.md](README.md) for detailed setup instructions.

## Code Style

### Python

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints where appropriate
- Maximum line length: 120 characters
- Use meaningful variable and function names

### Django

- Follow Django best practices
- Use Django's built-in features when possible
- Write docstrings for all functions and classes
- Use Django's ORM instead of raw SQL

### Frontend

- Use Tailwind CSS utility classes
- Keep JavaScript minimal (prefer Alpine.js)
- Ensure responsive design
- Test on multiple browsers

## Testing

- Write tests for new features
- Ensure all tests pass: `python manage.py test`
- Aim for good test coverage

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add SSL certificate management
fix: Resolve service restart issue
docs: Update installation instructions
refactor: Improve command execution utilities
```

## Pull Request Process

1. Update documentation if needed
2. Ensure all tests pass
3. Update CHANGELOG.md (if applicable)
4. Submit pull request with clear description
5. Respond to code review feedback

## Reporting Issues

When reporting issues, please include:

- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- System information (OS, Python version, etc.)
- Error messages or logs

## Feature Requests

Feature requests are welcome! Please:

- Check if the feature already exists
- Explain the use case
- Describe the expected behavior
- Consider implementation complexity

## Questions?

Feel free to open a discussion or issue for questions.

Thank you for contributing! 🎉

