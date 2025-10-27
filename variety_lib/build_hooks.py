from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from setuptools import Command
from setuptools.command.build import build as _build

DataFiles = List[Tuple[str, List[str]]]


def _extend_data_files(distribution, new_entries: Iterable[Tuple[str, List[str]]]) -> None:
    mapping: Dict[str, List[str]] = defaultdict(list)

    for target, files in getattr(distribution, "data_files", []) or []:
        mapping[target].extend(files)

    for target, files in new_entries:
        normalized_files = [str(path) for path in files]
        mapping[target].extend(normalized_files)

    merged: DataFiles = []
    for target in sorted(mapping.keys()):
        unique_files: List[str] = []
        seen = set()
        for file_path in mapping[target]:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)
        merged.append((target, unique_files))

    distribution.data_files = merged


def _collect_data_files(build_base: Path) -> DataFiles:
    data_root = Path("data")
    mapping: Dict[str, List[str]] = defaultdict(list)

    if data_root.exists():
        for path in sorted(data_root.rglob("*")):
            if not path.is_file():
                continue
            relative_parent = path.relative_to(data_root).parent.as_posix()
            if relative_parent == ".":
                target_dir = "share/variety"
            else:
                target_dir = f"share/variety/{relative_parent}"
            mapping[target_dir].append(str(path))

    appdata = Path("variety.appdata.xml")
    if appdata.exists():
        mapping["share/metainfo"].append(str(appdata))

    desktop = _render_desktop_file(build_base)
    if desktop is not None:
        mapping["share/applications"].append(str(desktop))

    entries: DataFiles = [(target, files) for target, files in mapping.items()]
    return entries


def _render_desktop_file(build_base: Path) -> Optional[Path]:
    source = Path("variety.desktop.in")
    if not source.exists():
        return None

    destination = build_base / "generated" / "variety.desktop"
    destination.parent.mkdir(parents=True, exist_ok=True)

    with source.open("r", encoding="utf-8") as src, destination.open("w", encoding="utf-8") as dst:
        for line in src:
            if line.startswith("_"):
                dst.write(line[1:])
            else:
                dst.write(line)

    return destination


def _compile_translation(source: Path, target: Path) -> bool:
    try:
        subprocess.run(["msgfmt", str(source), "-o", str(target)], check=True)
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return False
    return True


class BuildDataCommand(Command):
    description = "Collect Variety data files for installation."
    user_options: List[Tuple[str, str, str]] = []

    def initialize_options(self) -> None:
        self.build_base: Optional[Path] = None

    def finalize_options(self) -> None:
        build_cmd = self.get_finalized_command("build")
        self.build_base = Path(build_cmd.build_base)

    def run(self) -> None:
        build_base = self.build_base or Path("build")
        entries = _collect_data_files(build_base)
        _extend_data_files(self.distribution, entries)


class BuildTranslationsCommand(Command):
    description = "Compile gettext translation catalogs."
    user_options: List[Tuple[str, str, str]] = []

    def initialize_options(self) -> None:
        self.build_base: Optional[Path] = None

    def finalize_options(self) -> None:
        build_cmd = self.get_finalized_command("build")
        self.build_base = Path(build_cmd.build_base)

    def run(self) -> None:
        po_directory = Path("po")
        if not po_directory.exists():
            return

        build_base = self.build_base or Path("build")
        entries: DataFiles = []

        skipped_translations = []

        for po_file in sorted(po_directory.glob("*.po")):
            language = po_file.stem
            target_dir = build_base / "locale" / language / "LC_MESSAGES"
            target_dir.mkdir(parents=True, exist_ok=True)
            mo_file = target_dir / "variety.mo"
            self.announce(f"Compiling {po_file} -> {mo_file}", level=3)
            if _compile_translation(po_file, mo_file):
                entries.append((f"share/locale/{language}/LC_MESSAGES", [str(mo_file)]))
            else:
                skipped_translations.append(po_file.name)

        _extend_data_files(self.distribution, entries)

        if skipped_translations:
            skipped_list = ", ".join(sorted(skipped_translations))
            self.announce(
                "Skipping translation compilation (msgfmt missing?): " + skipped_list,
                level=2,
            )


class BuildCommand(_build):
    sub_commands = [
        ("build_data", None),
        ("build_trans", None),
        *_build.sub_commands,
    ]
