"""Hosted runtime for the existing AI Assistant (Stage A: private and model-free).

This package sits beside ``ai_assistant`` and never changes it. Keeping it outside means the
qualification basis and the synthetic boundary vocabulary, which are derived from
``ai_assistant``, stay the same as on a development machine.
"""
