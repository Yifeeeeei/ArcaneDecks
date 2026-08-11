#!/usr/bin/env python3
"""Generate the public deck index, then commit and push the deck files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DECKS_DIR = REPO_ROOT / "decks"
INDEX_FILE = REPO_ROOT / "index.json"
EXPECTED_FIELDS = {"name", "version", "deckCode"}
BASE_FILES = (".gitignore", ".nojekyll", "README.md", "publish.py", "index.json")


class PublishError(Exception):
    """An error that should be shown without a Python traceback."""


def run_git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Git 命令执行失败").strip()
        raise PublishError(detail)
    return (result.stdout or "").strip()


def git_succeeds(*args: str) -> bool:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def validate_deck(path: Path, data: object) -> dict[str, object]:
    label = path.relative_to(REPO_ROOT).as_posix()
    if not isinstance(data, dict):
        raise PublishError(f"{label}: 文件内容必须是一个 JSON 对象")

    fields = set(data)
    missing = EXPECTED_FIELDS - fields
    extra = fields - EXPECTED_FIELDS
    if missing:
        raise PublishError(f"{label}: 缺少字段 {', '.join(sorted(missing))}")
    if extra:
        raise PublishError(f"{label}: 存在不支持的字段 {', '.join(sorted(extra))}")

    name = data["name"]
    versions = data["version"]
    deck_code = data["deckCode"]
    if not isinstance(name, str) or not name.strip():
        raise PublishError(f"{label}: name 必须是非空文字")
    if (
        not isinstance(versions, list)
        or not versions
        or any(not isinstance(item, str) or not item.strip() for item in versions)
    ):
        raise PublishError(f"{label}: version 必须是包含至少一项文字的数组")
    if len(versions) != len(set(versions)):
        raise PublishError(f"{label}: version 中存在重复项")
    if not isinstance(deck_code, str) or not deck_code.strip():
        raise PublishError(f"{label}: deckCode 必须是非空文字")

    deck_id = path.relative_to(DECKS_DIR).with_suffix("").as_posix()
    return {
        "id": deck_id,
        "name": name.strip(),
        "version": [item.strip() for item in versions],
        "deckCode": deck_code.strip(),
    }


def generate_index() -> list[Path]:
    if not DECKS_DIR.is_dir():
        raise PublishError("找不到 decks 文件夹")

    deck_files = sorted(DECKS_DIR.rglob("*.json"))
    if not deck_files:
        raise PublishError("decks 文件夹中没有找到 JSON 卡组")

    decks: list[dict[str, object]] = []
    for path in deck_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            label = path.relative_to(REPO_ROOT).as_posix()
            raise PublishError(
                f"{label}: JSON 格式错误（第 {error.lineno} 行，第 {error.colno} 列）"
            ) from error
        decks.append(validate_deck(path, data))

    payload = {"decks": decks}
    INDEX_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已生成 index.json，共收录 {len(decks)} 副卡组。")
    return deck_files


def tracked_deck_json_files() -> list[Path]:
    output = run_git("ls-files", "--", "decks", capture=True)
    return [REPO_ROOT / item for item in output.splitlines() if item.endswith(".json")]


def publish(deck_files: list[Path]) -> None:
    allowed = {REPO_ROOT / name for name in BASE_FILES}
    allowed.update(deck_files)
    allowed.update(tracked_deck_json_files())
    relative_paths = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in allowed
        if path.exists() or path in tracked_deck_json_files()
    )

    run_git("add", "--", *relative_paths)
    changed = run_git("diff", "--cached", "--name-only", "--", *relative_paths, capture=True)
    if changed:
        run_git("commit", "--only", "-m", "Update decks index", "--", *relative_paths)
        print("已创建提交：Update decks index")
    else:
        print("卡组文件没有变化，不需要创建提交。")

    if git_succeeds("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"):
        run_git("push")
    else:
        branch = run_git("branch", "--show-current", capture=True)
        if not branch:
            raise PublishError("当前不在 Git 分支上，无法执行 push")
        run_git("push", "--set-upstream", "origin", branch)
    print("发布完成，Git push 已成功。")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成并发布 ArcaneDecks 索引")
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="只生成 index.json，不执行 Git commit 和 push",
    )
    args = parser.parse_args()

    try:
        deck_files = generate_index()
        if not args.generate_only:
            publish(deck_files)
    except PublishError as error:
        print(f"发布失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
