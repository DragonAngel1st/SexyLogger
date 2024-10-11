# sexy_logger.py

'''      
                              _|_|_     
 _     _     _     _          (o o)       _     _     _     _     _     _     _     _     _     _   
/ \___/ \___/ \___/ \___--ooO--(_)--Ooo--/ \___/ \___/ \___/ \___/ \___/ \___/ \___/ \___/ \___/ \_
#                                                                                                 #
#  ____       _        _      _      __  __ _                                                     #
# |  _ \ __ _| |_ _ __(_) ___| | __ |  \/  (_)_ __ ___  _ __                                      #
# | |_) / _` | __| '__| |/ __| |/ / | |\/| | | '__/ _ \| '_ \                                     #
# |  __/ (_| | |_| |  | | (__|   <  | |  | | | | | (_) | | | |                                    #
# |_|   \__,_|\__|_|  |_|\___|_|\_\ |_|  |_|_|_|  \___/|_| |_|                                    #
#                                                                                                 # 
#  Date Created  : 2024-02-21                                                                     #
#  Last Updated  : 2024-10-10 11:03:AM                                                            #
#                                                                                                 #
#  Project: SexyLogger                                                                            #
#                                                                                                 #
#  Description:                                                                                   #
#  --------------------------------------------------------------------------------------------   #
#  SexyLogger is a simple logging class that logs to the console and file with a box around the   #
#  logged message.                                                                               #
#                                                                                                 # 
#  License:                                                                                       #
#  --------------------------------------------------------------------------------------------   #
#  This work was done for Nextria Inc. All rights reserved.                                       #
#                                                                                                 #
#  References / Links:                                                                            #
#  --------------------------------------------------------------------------------------------   #
#  - Package Repo:                #
#  - Dependencies: logging, pathlib, datetime, random, inspect, os                                #
#                                                                                                 #
###################################################################################################
'''

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
from datetime import datetime
import random
import inspect
import os

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

    def __init__(self, name: str, log_dir: str = "debug_logs", log_file_name: str = "debug_logs", file_logging: bool = True, console_logging: bool = True, forced_box_width: int = 80) -> None:
        """
        Initialize the SexyLogger class, which is a subclass of logging.Logger.

        :param name: str - The name of the logger.
        :param log_dir: str - The directory where log files will be stored.
        :param log_file_name: str - The name of the log file.
        :param file_logging: bool - Enable or disable logging to a file.
        :param console_logging: bool - Enable or disable logging to the console.
        :param desired_box_width: int - The desired width for log message boxes.
        """
        if not hasattr(self, '_initialized'):  # Prevent re-initialization
            super().__init__(name)  # Call the parent constructor
            
            self.file_logging: bool = file_logging
            self.console_logging: bool = console_logging

            # Determine maximum box width based on console size, else just keep current value
            try:
                self.terminal_window_width: int = os.get_terminal_size().columns
            except OSError:
                self.terminal_window_width = 80  # set terminal_window_width to 80 if there is an error

            # Set max_box_width based on forced_box_width or terminal_window_width
            self.max_box_width = forced_box_width if forced_box_width and forced_box_width >= 60 else self.terminal_window_width
    
            # Set the base log level to INFO
            self.setLevel(logging.INFO)

            # Setup file logging if enabled
            self.file_handler: logging.FileHandler = self.setup_file_handler(log_dir, log_file_name)

            # Setup console logging if enabled
            self.console_handler: logging.StreamHandler = self.setup_console_handler()
            
            # Prevent log messages from propagating to other handlers
            self.propagate: bool = False

            self.log_message_collection: Dict[str, List[str]] = {}  # Collection to store log messages

            self._initialized: bool = True  # Mark as initialized to avoid re-initialization
            
    @classmethod
    def reset_logger(cls) -> None:
        """
        Resets the singleton instance of SexyLogger, allowing it to be deallocated
        when there are no more references to it.
        """
        cls._instance = None

    def setup_file_handler(self, log_dir: str, log_filename: str) -> logging.FileHandler:
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

    def setup_console_handler(self) -> logging.StreamHandler:
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

    def add_log_message(self, message: str, box_group_name: str = None) -> None:
        """
        Adds a message to the log_messages collection.
        :param message: The message to be added.
        :param box_group_name: The group name of the key from the log_message_collection so we can save the message to the correct message list.
        :return: None
        """
        # Set box_group_name to the calling function's name if it is None
        if box_group_name is None:
            box_group_name = inspect.stack()[1].function
        
        # Use setdefault to ensure the key exists with a default empty list
        self.log_message_collection.setdefault(box_group_name, [])

        # Now you can safely append to the list associated with the key
        self.log_message_collection[box_group_name].append(message)

    def log_group_to_box(self, add_to_group: str = None, box_width: int = None, log_to_console: bool = None, log_to_file: bool = None, color: str = None) -> None:
        """
        Logs the messages from the specified group using log_with_box.
        :param add_to_group: The group of messages to log.
        :param box_width: The width of the box for logging.
        :param log_to_console: Whether to log to console.
        :param log_to_file: Whether to log to file.
        :param color: The color to use for logging.
        :return: None
        """
        if add_to_group is None:
            add_to_group = inspect.stack()[1].function
        
        if add_to_group in self.log_message_collection:
            self.log_with_box(self.log_message_collection[add_to_group], add_to_group, box_width, log_to_console, log_to_file, color)
            del self.log_message_collection[add_to_group]
        else:
            self.warning(f"No messages found for group: {add_to_group}")
      

    def log_with_box(self, messages: List[str], func_name: str = None, box_width: int = None, log_to_console: bool = None, log_to_file: bool = None, color: str = None) -> None:
        """
        Logs accumulated messages inside a box with the calling function's name printed above.
        Supports both console (colored) and file (non-colored) logging.
        :param func_name: The name of the function (defaults to the calling function).
        :param box_width: The fixed width of the box (default is 50 characters).
        :param log_to_console: Boolean flag to log to the console (overrides self.console_logging if set).
        :param log_to_file: Boolean flag to log to the file (overrides self.file_logging if set).
        :return: None
        """
        if box_width is None:
            box_width = self.max_box_width  # Use class default if not provided

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


        # Ensure box width accounts for padding and borders
        # Split individual log message into multiple lines if too long
        lines = []
        
        # Comment out the following line if you don't want to show the box width in the log and for production
        lines.append(f"This box is: {box_width} wide.")
        
        for message in messages:
            lines.extend([message[i:i + (box_width - 4)] for i in range(0, len(message), box_width - 4)])
        padded_log_messages = [f"{vertical} {line.ljust(box_width - 4)} {vertical}\n" for line in lines]


        # Log to console (with colors)
        if log_to_console and self.console_handler:
            console_message = (
                f"{bold}Function: {func_name}{reset}\n"
                f"{color_code}{top_border}{reset}\n"
                f"{color_code}{''.join(padded_log_messages)}{reset}"
                f"{color_code}{bottom_border}{reset}\n"
            )
            # Use self.console_handler directly
            self.console_handler.handle(logging.makeLogRecord({"msg": console_message, "level": logging.INFO}))

        # Log to file (without colors)
        if log_to_file and self.file_handler:
            file_message = (
                f"Function: {func_name}\n"
                f"{top_border}\n"
                + ''.join(padded_log_messages)
                + f"{bottom_border}\n"
            )
            # Use self.file_handler directly
            self.file_handler.handle(logging.makeLogRecord({"msg": file_message, "level": logging.INFO}))
        self.log_messages = []  # Clear messages after logging

    @classmethod
    def self_test_logger(cls) -> None:
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
            logger.add_log_message(f"This is test log number {i}.")
        logger.log_group_to_box()

        # Inform the user that the test is complete
        logger.info("Self-test complete. Check the 'self_test_logger.log' file for details.")

        # Reset the logger after the test to allow deallocation
        cls.reset_logger()
        # If the user still holds a reference (e.g., sexyOne), they can still use that reference
        
        
if __name__ == "__main__":
    SexyLogger.self_test_logger()