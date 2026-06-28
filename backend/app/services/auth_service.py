"""
⚠️ DEPRECATED: Auth is now handled via Firebase ID tokens.

This module is kept as a reference for local development/testing only.
All production authentication uses Firebase token verification via
app.dependencies.get_current_user.

The bcrypt/jwt-based auth in this module is no longer used by any
import in the codebase. Tests use a mock Firebase token approach.
"""
