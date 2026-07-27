"""Packaged JSON Schema documents.

This package exists so that the schema files can be located through
:mod:`importlib.resources` rather than by filesystem path, which keeps them
readable from a wheel and independent of the current working directory.

Load them through :mod:`eo_claim_lint.schema` rather than reading the files
directly.
"""
