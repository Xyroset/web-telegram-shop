import argparse
import subprocess
import sys
from pathlib import Path
from typing import Literal

from prints import Prints

BASE_LANG: str = "en"
TranslationType = Literal["frontend", "backend"]


def _resolve_project_root() -> Path:
    """
    Locates the backend/project root directory by searching for manage.py
    or falling back to the parent directory hierarchy.
    """
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "manage.py").exists():
            return parent
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT: Path = _resolve_project_root()


def _resolve_backend_locales_dir() -> Path:
    """
    Resolves the backend locales directory path, handling both 'locales' and 'locale' naming.
    """
    if (PROJECT_ROOT / "locales").exists():
        return PROJECT_ROOT / "locales"
    if (PROJECT_ROOT / "locale").exists():
        return PROJECT_ROOT / "locale"
    return PROJECT_ROOT / "locales"


def _resolve_frontend_locales_dir() -> Path:
    """
    Resolves the frontend locales directory path, checking both container (/app/shop_config)
    and root monorepo locations.
    """
    possible_paths: list[Path] = [
        PROJECT_ROOT / "shop_config/frontend/locales",
        PROJECT_ROOT / "config/frontend/locales",
        PROJECT_ROOT.parent / "shop_config/frontend/locales",
        PROJECT_ROOT.parent / "config/frontend/locales",
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return PROJECT_ROOT / "shop_config/frontend/locales"


FRONTEND_LOCALES_DIR: Path = _resolve_frontend_locales_dir()
BACKEND_LOCALES_DIR: Path = _resolve_backend_locales_dir()


def get_target_languages(translation_type: TranslationType) -> list[str]:
    """
    Retrieves the list of existing target language codes based on available locale files.
    """
    if translation_type == "frontend":
        if not FRONTEND_LOCALES_DIR.exists():
            Prints.print_error(msg=f"Frontend directory not found: {FRONTEND_LOCALES_DIR}")
            return []
        json_files = list(FRONTEND_LOCALES_DIR.glob("*.json"))
        return sorted([f.stem for f in json_files if f.stem.lower() != BASE_LANG.lower()])

    if not BACKEND_LOCALES_DIR.exists():
        Prints.print_error(msg=f"Backend directory not found: {BACKEND_LOCALES_DIR}")
        return []

    target_dirs = [
        p.name
        for p in BACKEND_LOCALES_DIR.iterdir()
        if p.is_dir() and p.name.lower() != BASE_LANG.lower() and (p / "LC_MESSAGES" / "django.po").exists()
    ]
    return sorted(target_dirs)


def main() -> None:
    """
    Batch translation runner that invokes auto_translate.py for all discovered target locales.
    """
    parser = argparse.ArgumentParser(description="Batch auto-translate runner for all existing locales.")
    parser.add_argument(
        "--type",
        choices=["frontend", "backend"],
        required=True,
        help="Target environment to batch translate (frontend or backend)",
    )
    args = parser.parse_args()
    translation_type: TranslationType = args.type

    translate_script = Path(__file__).resolve().parent / "auto_translate.py"

    if not translate_script.exists():
        Prints.print_error(msg=f"Translator script not found: {translate_script}")
        sys.exit(1)

    target_langs = get_target_languages(translation_type)

    if not target_langs:
        Prints.print_warning(msg=f"No additional language files found to update for {translation_type}.")
        sys.exit(0)

    Prints.print_info(msg=f"Found {translation_type} languages to update: {', '.join(target_langs)}")
    Prints.print_lines()

    for lang in target_langs:
        Prints.print_info(msg=f"=== Starting update for '{lang}' ({translation_type}) ===")
        try:
            cmd = [sys.executable, str(translate_script), lang, "--type", translation_type]
            process = subprocess.run(cmd, check=False)

            if process.returncode != 0:
                Prints.print_error(msg=f"Failed to update {lang}. Subprocess exited with code {process.returncode}")
        except KeyboardInterrupt:
            Prints.print_warning(msg="Batch translation interrupted by user.")
            sys.exit(130)
        except Exception as exc:
            Prints.print_error(msg=f"Error executing translation for {lang}: {exc}")

        Prints.print_lines()

    Prints.print_success(msg=f"All {translation_type} translation files have been synchronized!")


if __name__ == "__main__":
    main()
