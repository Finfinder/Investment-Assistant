"""Orchestration layer - use-case orchestrators above domain modules.

This layer coordinates the independent domain modules in app.modules.*
and is allowed to import from them (no import-linter contract forbids it).
It must not be imported by core or api in a way that breaks boundaries.
"""
