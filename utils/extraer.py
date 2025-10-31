# utils/extraer_commit.py
# -*- coding: utf-8 -*-
"""
Funciones para obtener el hash y la rama del commit actual.
Prioriza variables de entorno (CI/CD), luego `git`, y finalmente lectura de .git.
Uso:
    from utils.extraer_commit import get_git_info
    commit_hash, branch = get_git_info(short=True)
"""

from __future__ import annotations
import os
import subprocess
from typing import Tuple


def _from_env() -> Tuple[str | None, str | None]:
    # Hash
    for k in ("GIT_COMMIT", "GITHUB_SHA", "VERCEL_GIT_COMMIT_SHA", "SOURCE_VERSION"):
        v = os.environ.get(k)
        if v:
            commit = v.strip()
            break
    else:
        commit = None

    # Rama
    branch = (
        os.environ.get("GIT_BRANCH")
        or os.environ.get("GITHUB_REF_NAME")   # GitHub Actions
        or os.environ.get("VERCEL_GIT_COMMIT_REF")
        or None
    )

    return commit, branch


def _run_git(cmd: list[str]) -> str | None:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return out or None
    except Exception:
        return None


def _from_git_cli() -> Tuple[str | None, str | None]:
    commit = _run_git(["git", "rev-parse", "HEAD"])
    # `git rev-parse --abbrev-ref HEAD` devuelve 'HEAD' si está detached
    branch = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch == "HEAD":
        branch = None
    return commit, branch


def _read_file(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def _from_git_dir() -> Tuple[str | None, str | None]:
    """Lee .git/HEAD y refs. Maneja refs empacadas."""
    head = _read_file(".git/HEAD")
    if not head:
        return None, None

    # HEAD puede ser:
    #  - "ref: refs/heads/main"
    #  - "<commit_hash>" (detached)
    if head.startswith("ref:"):
        ref_path = head.split(" ", 1)[-1].strip()  # "refs/heads/main"
        branch = ref_path.split("/")[-1] if "/" in ref_path else ref_path

        # Intentar leer el archivo de la ref directa
        commit = _read_file(os.path.join(".git", ref_path))
        if commit:
            return commit, branch

        # Fallback: buscar en packed-refs
        packed = _read_file(".git/packed-refs")
        if packed:
            for line in packed.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                # formato: "<hash> refs/heads/main"
                parts = line.split(" ")
                if len(parts) == 2 and parts[1].strip() == ref_path:
                    return parts[0].strip(), branch

        return None, branch  # sin hash pero con rama
    else:
        # detached HEAD: head ya es el hash
        commit = head
        branch = None
        return commit, branch


def get_git_info(short: bool = True) -> Tuple[str, str]:
    """
    Devuelve (commit_hash, branch). Si no se puede determinar, retorna "unknown".
    short=True => hash de 7 caracteres.
    """
    # 1) Entorno
    c, b = _from_env()
    # 2) CLI git
    if not c:
        c2, b2 = _from_git_cli()
        c = c or c2
        b = b or b2
    # 3) Archivos .git
    if not c or not b:
        c3, b3 = _from_git_dir()
        c = c or c3
        b = b or b3

    if not c:
        c = "unknown"
    if not b:
        b = "unknown"

    if short and c != "unknown":
        c = c[:7]

    return c, b
