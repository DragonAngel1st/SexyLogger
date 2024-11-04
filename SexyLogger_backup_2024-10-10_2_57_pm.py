# sexy_logger.py

import logging
from pathlib import Path
from datetime import datetime
import random
import inspect

class SexyLogger(logging.Logger):
    _instance = None  # Class-level attribute to hold the single instance

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of the logger if it doesn't exist.
        Return the existing instance if already created.
        """
        if cls._instance is None:
            cls._instance = super(SexyLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, name, log_dir="debug_logs", log_file_name="debug_logs", file_logging=True, console_logging=True, default_box_width=120):
        """
        Initialize the SexyLogger class as a subclass of logging.Logger.
        :param name: The name of the logger.
        :param log_dir: Directory where log files will be stored.
        :param log_file_name: The name of the log file.
        :param file_logging: Enable/disable file logging.
        :param console_logging: Enable/disable console logging.
        """
        if not hasattr(self, '_initialized'):  # Prevent re-initialization
            super().__init__(name)  # Call the parent constructor
            
            self.file_logging = file_logging
            self.console_logging = console_logging

            self.default_box_width = default_box_width  # Set the default box width

            # Set the base log level to INFO
            self.setLevel(logging.INFO)

            # Setup file logging if enabled
            self.file_handler = self.setup_file_handler(log_dir, log_file_name)

            # Setup console logging if enabled
            self.console_handler = self.setup_console_handler()
            
            # Prevent log messages from propagating to other handlers
            self.propagate = False

            self._initialized = True  # Mark as initialized to avoid re-initialization
            
    @classmethod
    def reset_logger(cls):
        """
        Resets the singleton instance of SexyLogger, allowing it to be deallocated
        when there are no more references to it.
        """
        cls._instance = None

    def setup_file_handler(self, log_dir, log_filename):
        """
        Set up the file handler for logging without ANSI codes.
        :param log_dir: Directory where log files will be stored.
        :param log_file_name: Name of the log file.
        """
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)

        # Create a timestamped log filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = log_dir_path / f"{log_filename}_{timestamp}.log"

        # Setup file handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(message)s')  # Simple message, no ANSI codes
        file_handler.setFormatter(file_formatter)

        # Add the file handler to the logger
        self.addHandler(file_handler)

        # Log the start of the log file
        self.info(f"Log started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}")

        return file_handler

    def setup_console_handler(self):
        """
        Set up the console handler for logging with ANSI codes.
        """
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')  # Normal formatter with color support
        console_handler.setFormatter(console_formatter)

        # Add the console handler to the logger
        self.addHandler(console_handler)

        return console_handler

    def log_with_box(self, log_message, func_name=None, box_width=None, log_to_console=None, log_to_file=None, color=None):
        """
        Logs a message inside a box with the calling function's name printed above.
        Supports both console (colored) and file (non-colored) logging.
        :param log_message: The log message to display inside the box.
        :param func_name: The name of the function (defaults to the calling function).
        :param box_width: The fixed width of the box (default is 50 characters).
        :param log_to_console: Boolean flag to log to the console (overrides self.console_logging if set).
        :param log_to_file: Boolean flag to log to the file (overrides self.file_logging if set).
        :return: None
        """
        if box_width is None:
            box_width = self.default_box_width  # Use class default if not provided

        # Use the function caller's name if func_name is not provided
        if func_name is None:
            func_name = inspect.stack()[1].function

        # Set the logging flags to self defaults if not overridden
        if log_to_console is None:
            log_to_console = self.console_logging  # Use the instance's default for console logging
        if log_to_file is None:
            log_to_file = self.file_logging  # Use the instance's default for file logging

        # Ensure box_width is an integer
        box_width = int(box_width)

        # Define a list of ANSI escape codes for colors (only for console)
        colors = {
            "yellow": "\033[93m",
            "green": "\033[92m",
            "blue": "\033[94m",
            "red": "\033[91m",
            "magenta": "\033[95m",
            "purple_lilac": "\033[35m"
        }
        if color is None:
            # Randomly choose a color for console logging
            color_code = random.choice(list(colors.values()))
        else:
            color_code = colors[color]
        bold = "\033[1m"
        reset = "\033[0m"

        # Ensure box width accounts for padding and borders
        box_width = max(box_width, len(f"Function: {func_name}") + 4)

        # Box contour characters
        top_left = "╔"
        top_right = "╗"
        bottom_left = "╚"
        bottom_right = "╝"
        horizontal = "═"
        vertical = "║"

        # Create the top and bottom borders of the box
        top_border = f"{top_left}{horizontal * (box_width - 2)}{top_right}"
        bottom_border = f"{bottom_left}{horizontal * (box_width - 2)}{bottom_right}"

        # Split log message into multiple lines if too long
        lines = [log_message[i:i + (box_width - 4)] for i in range(0, len(log_message), box_width - 4)]
        padded_log_messages = [f"{vertical} {line.ljust(box_width - 4)} {vertical}\n" for line in lines]

        # Log to console (with colors)
        if log_to_console and self.console_handler:
            console_message = (
                f"{bold}Function: {func_name}{reset}\n"
                f"{color_code}{top_border}{reset}\n"
                f"{color_code}{''.join([f'{line}' for line in padded_log_messages])}\n{reset}"
                f"{color_code}{bottom_border}{reset}\n"
            )
            # Use self.console_handler directly
            self.console_handler.handle(logging.makeLogRecord({"msg": console_message, "level": logging.INFO}))

        # Log to file (without colors)
        if log_to_file and self.file_handler:
            file_message = (
                f"Function: {func_name}\n"
                f"{top_border}\n"
                + '\n'.join(padded_log_messages) + "\n"
                f"{bottom_border}\n"
            )
            # Use self.file_handler directly
            self.file_handler.handle(logging.makeLogRecord({"msg": file_message, "level": logging.INFO}))


    @classmethod
    def self_test_logger(cls):
        """
        Class method to perform a self-test, printing 5 logs to the console and log file.
        After the test, the logger instance will be deallocated if there are no more references.
        :return: None
        """
        # Create an instance of the SexyLogger (or return the existing one)
        logger = cls(name="self_test_logger", log_dir=".", file_logging=True, console_logging=True)

        # Inform the user
        logger.info("Performing self-test with 5 log messages...")

        # Generate 5 test logs
        for i in range(1, 6):
            logger.log_with_box(f"This is test log number {i}.", func_name="self_test_logger " + str(i))

        # Inform the user that the test is complete
        logger.info("Self-test complete. Check the 'self_test_logger.log' file for details.")

        # Reset the logger after the test to allow deallocation
        cls.reset_logger()
        # If the user still holds a reference (e.g., sexyOne), they can still use that reference
