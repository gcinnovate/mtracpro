#!/usr/bin/env python3
"""Lightweight import smoke test for Python 3 runtime entrypoints."""

import importlib
import os
import sys

import web


class DummyDB:
    """Minimal DB stub to let controller module globals initialize."""

    def query(self, *args, **kwargs):
        return []

    def select(self, *args, **kwargs):
        return []

    def insert(self, *args, **kwargs):
        return None

    def update(self, *args, **kwargs):
        return 0

    def delete(self, *args, **kwargs):
        return 0


def _stub_web_database():
    web.database = lambda *args, **kwargs: DummyDB()


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    _stub_web_database()

    main_module = importlib.import_module("webapp.main")
    celery_module = importlib.import_module("webapp.celery_app")

    assert hasattr(main_module, "application"), "webapp.main missing application object"
    assert hasattr(celery_module, "app"), "webapp.celery_app missing Celery app object"
    print("Smoke imports passed: webapp.main and webapp.celery_app")


if __name__ == "__main__":
    main()
