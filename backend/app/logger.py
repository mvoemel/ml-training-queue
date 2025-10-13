from enum import Enum

class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"

class Logger:
    COLORS = {
        "reset": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "orange": "\033[33m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m"
    }

    default_color = "white"

    @classmethod
    def log(cls, message: str, level, color=None):
        # Level can be enum or str
        if isinstance(level, LogLevel):
            label = level.value
        else:
            label = str(level).upper()

        color_code = cls.COLORS.get(color or cls.default_color, cls.COLORS["white"])
        print(f"# {color_code}{label}{cls.COLORS['reset']}:  {message}")

    @classmethod
    def info(cls, message: str, color=None):
        cls.log(message, LogLevel.INFO, color or "green")

    @classmethod
    def warning(cls, message: str, color=None):
        cls.log(message, LogLevel.WARNING, color or "orange")

    @classmethod
    def error(cls, message: str, color=None):
        cls.log(message, LogLevel.ERROR, color or "red")

    @classmethod
    def debug(cls, message: str, color=None):
        cls.log(message, LogLevel.DEBUG, color or "blue")

    @classmethod
    def custom(cls, message: str, level: str, color=None):
        cls.log(message, level, color or "cyan")
