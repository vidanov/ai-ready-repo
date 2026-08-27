"""
ai-ready-repo: starter template for AI-ready Python repositories.

Package structure follows a layered architecture:
- domain:         Pure business logic. No framework dependencies.
- application:    Use cases. Depends on domain.
- infrastructure: External services, databases, APIs. Depends on domain + application.

Import rules (enforced by import-linter):
- domain must not import application or infrastructure
- application must not import infrastructure
"""
