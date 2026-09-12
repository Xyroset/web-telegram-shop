import shutil
from typing import Final


class Prints:
    """
    Console text formatter and colored logger for CLI tools and scripts.
    """

    COLOR_GREEN: Final[str] = "\033[92m"
    COLOR_YELLOW: Final[str] = "\033[93m"
    COLOR_RED: Final[str] = "\033[91m"
    COLOR_CYAN: Final[str] = "\033[96m"
    COLOR_RESET: Final[str] = "\033[0m"
    SYMBOL_LINES: Final[str] = "-"

    @staticmethod
    def print_success(msg: str) -> None:
        """Prints a success message in green."""
        print(f"{Prints.COLOR_GREEN}[SUCCESS] {msg}{Prints.COLOR_RESET}")

    @staticmethod
    def print_warning(msg: str) -> None:
        """Prints a warning message in yellow."""
        print(f"{Prints.COLOR_YELLOW}[WARNING] {msg}{Prints.COLOR_RESET}")

    @staticmethod
    def print_error(msg: str) -> None:
        """Prints an error message in red."""
        print(f"{Prints.COLOR_RED}[ERROR] {msg}{Prints.COLOR_RESET}")

    @staticmethod
    def print_info(msg: str) -> None:
        """Prints an informational message in cyan."""
        print(f"{Prints.COLOR_CYAN}[INFO] {msg}{Prints.COLOR_RESET}")

    @staticmethod
    def print_lines(length: int | None = None) -> None:
        """
        Prints a separator line matched to terminal width.
        Safely falls back to 80 columns if running in a non-interactive environment (CI/CD).
        """
        if length is not None:
            width = length
        else:
            width = shutil.get_terminal_size(fallback=(80, 20)).columns

        print(Prints.SYMBOL_LINES * width)
