"""Offline evaluation of the AI Assistant's answers (Phase A1, WP2).

Runs the real service (``ai_assistant.main.create_app``) over synthetic scenarios with a fake
CLM backend and a temporary knowledge base, and scores which allowed lines an answer selected.
Everything is deterministic and local:

- scenarios: synthetic variants of the saved Garden fixtures (``scenarios``, ``variants``);
- snapshots: what each question offered the model, frozen with stable line ids (``snapshot``);
- gold labels: written by the owner/team only; the harness writes stubs (``gold``);
- models: evaluator self-test selectors and a local (literal loopback) model (``models``);
- runs, scores and reports (``runner``, ``scoring``, ``report``).

The runtime package ``ai_assistant`` never imports this package. No remote model is ever
called: a model URL that is not a literal loopback address is refused before any request.
"""
