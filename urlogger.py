#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urlogger.py - Logging utilities
Part of hpclib - included for standalone operation
"""
import typing
from typing import *

import os
import sys
import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = None,
                log_file: str = None,
                level: int = logging.INFO,
                format_string: str = None) -> logging.Logger:
    """
    Setup a logger with console and file handlers
    
    Args:
        name: Logger name (default: __name__)
        log_file: Log file path (optional)
        level: Logging level
        format_string: Custom format string
        
    Returns:
        Configured logger instance
    """
    if name is None:
        name = __name__
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create log directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get or create a logger
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    if name is None:
        name = __name__
    
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set up basic config
    if not logger.handlers:
        logger = setup_logger(name)
    
    return logger


class LogContext:
    """Context manager for temporary log level changes"""
    
    def __init__(self, logger: logging.Logger, level: int):
        """
        Initialize log context
        
        Args:
            logger: Logger to modify
            level: Temporary log level
        """
        self.logger = logger
        self.new_level = level
        self.old_level = logger.level
    
    def __enter__(self):
        """Enter context"""
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        self.logger.setLevel(self.old_level)


if __name__ == '__main__':
    # Test the module
    logger = setup_logger('test', level=logging.DEBUG)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
