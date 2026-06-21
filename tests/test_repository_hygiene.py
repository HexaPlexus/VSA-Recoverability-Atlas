from __future__ import annotations

import importlib.util
import os
import tempfile
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_pyproject_public_urls_and_version() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["version"] == "0.1.0"
    for value in project["urls"].values():
        assert "<owner>" not in value
        assert "HexaPlexus/VSA-Recoverability-Atlas" in value


def test_pyproject_publication_and_dev_dependencies_present() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]
    for extra_name in ("dev", "publication"):
        assert extra_name in extras
    publication = " ".join(extras["publication"])
    dev = " ".join(extras["dev"])
    for requirement in ("Markdown", "matplotlib", "pypdf", "PyYAML"):
        assert requirement in publication
    assert "pytest" in dev
    assert "holovec" in dev
    assert "minigrid" in dev


def test_publication_scripts_do_not_use_owner_local_paths() -> None:
    for path in (
        ROOT / "scripts" / "build_manuscript.py",
        ROOT / "scripts" / "validate_manuscript_pdf.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert r"C:\Users\Thanatos" not in text


def test_workflow_covers_publication_branch_and_minimal_permissions() -> None:
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "publication/**" in workflow
    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow


def test_workflow_builds_and_validates_reviewer_pdf() -> None:
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "python scripts/build_manuscript.py --profile reviewer-preprint --skip-figure-build" in workflow
    assert "python scripts/validate_manuscript_pdf.py --release" in workflow


def test_workspace_bootstrap_files_exist() -> None:
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.14"
    devcontainer = (ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    assert "mcr.microsoft.com/devcontainers/python:1-3.14-bookworm" in devcontainer
    assert "python -m pip install -e" in devcontainer
    assert ".[dev,publication,competitors,level3]" in devcontainer


def test_gitattributes_enforces_lf_for_text_artifacts() -> None:
    gitattributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in ("*.md text eol=lf", "*.json text eol=lf", "*.yaml text eol=lf", "*.py text eol=lf"):
        assert pattern in gitattributes


def test_build_manuscript_tool_resolution_prefers_explicit_env_then_path() -> None:
    module = _load_module(ROOT / "scripts" / "build_manuscript.py", "build_manuscript")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        explicit = temp_path / "pandoc-explicit"
        explicit.write_text("", encoding="utf-8")
        assert module.resolve_tool(str(explicit), env_var="PANDOC", executable="pandoc") == explicit.resolve()

        env_tool = temp_path / "pandoc-env"
        env_tool.write_text("", encoding="utf-8")
        old_env = os.environ.get("PANDOC")
        os.environ["PANDOC"] = str(env_tool)
        try:
            assert module.resolve_tool(None, env_var="PANDOC", executable="pandoc") == env_tool.resolve()
        finally:
            if old_env is None:
                os.environ.pop("PANDOC", None)
            else:
                os.environ["PANDOC"] = old_env


def test_validate_manuscript_pdf_supports_explicit_qpdf_override() -> None:
    module = _load_module(ROOT / "scripts" / "validate_manuscript_pdf.py", "validate_manuscript_pdf")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qpdf = temp_path / "qpdf"
        qpdf.write_text("", encoding="utf-8")
        assert module.resolve_qpdf(str(qpdf)) == qpdf.resolve()
