import re
import secrets
import shutil
from pathlib import Path

from prints import Prints

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

KEYS_TO_GENERATE: tuple[str, ...] = (
    "DJANGO_SECRET_KEY",
    "TELEGRAM_WEBHOOK_SECRET",
    "ADMIN_WEBHOOK_SECRET",
)


def init_env_file() -> None:
    """
    Copies .env.example to .env if the target file does not exist.
    """
    env_example = ROOT_DIR / ".env.example"
    env_file = ROOT_DIR / ".env"

    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            Prints.print_success(msg="File .env created from template.")
        else:
            Prints.print_error(msg=f"Template .env.example not found at {env_example}!")
    else:
        Prints.print_warning(msg="File .env already exists, skipping.")


def init_yaml_configs() -> None:
    """
    Finds all *.example.yaml files in config/ and creates production-ready *.yaml copies.
    """
    config_dir = ROOT_DIR / "config"

    if not config_dir.exists() or not config_dir.is_dir():
        Prints.print_warning(msg=f"Directory '{config_dir}' not found, skipping YAML initialization.")
        return

    for example_file in config_dir.rglob("*.example.yaml"):
        target_name = example_file.name.replace(".example.yaml", ".yaml")
        target_file = example_file.with_name(target_name)

        if not target_file.exists():
            shutil.copy(example_file, target_file)
            Prints.print_success(msg=f"Created config file: {target_file}")
        else:
            Prints.print_warning(msg=f"Config file {target_file} already exists, skipping.")


def generate_env_secrets() -> None:
    """
    Injects cryptographically secure tokens into empty secret variables within .env.
    """
    env_file = ROOT_DIR / ".env"

    if not env_file.exists():
        return

    with open(env_file, "r", encoding="utf-8") as file:
        lines = file.readlines()

    out_lines: list[str] = []
    secrets_added = False

    for line in lines:
        updated_line = line
        for key in KEYS_TO_GENERATE:
            pattern = rf"^\s*{re.escape(key)}\s*=\s*[\"']?\s*[\"']?\s*$"
            if re.match(pattern, line):
                secure_token = secrets.token_urlsafe(40)
                updated_line = f"{key}={secure_token}\n"
                secrets_added = True
                break

        out_lines.append(updated_line)

    if secrets_added:
        with open(env_file, "w", encoding="utf-8") as file:
            file.writelines(out_lines)
        Prints.print_success(msg="Secure secrets generated and injected into .env.")
    else:
        Prints.print_info(msg="No empty secret keys found in .env. Skipping generation.")


if __name__ == "__main__":
    Prints.print_info(msg="Starting project initialization...")
    Prints.print_lines()

    init_env_file()
    init_yaml_configs()
    generate_env_secrets()

    Prints.print_lines()
    Prints.print_success(msg="Initialization complete!")
    Prints.print_info(msg="Please fill in the remaining tokens in .env and run: make start-dev")
