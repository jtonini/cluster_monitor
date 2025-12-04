#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dorunrun.py - Command execution wrapper
Part of hpclib - included for standalone operation
"""
import typing
from typing import *

import os
import sys
import subprocess
import shlex
from collections import namedtuple

# Result tuple for command execution
ExitCode = namedtuple('ExitCode', ['OK', 'exit_code', 'value', 'stdout', 'stderr'])


def dorunrun(command: str, 
             timeout: int = None,
             return_datatype: type = str,
             input_data: str = None,
             **kwargs) -> ExitCode:
    """
    Execute a shell command and return structured results.
    
    Args:
        command: Shell command to execute
        timeout: Command timeout in seconds
        return_datatype: Type to return (str, bytes, list, etc.)
        input_data: Data to send to stdin
        **kwargs: Additional arguments passed to subprocess.run
        
    Returns:
        ExitCode namedtuple with:
            - OK: True if exit_code == 0
            - exit_code: Command exit code
            - value: stdout content (converted to return_datatype)
            - stdout: Raw stdout
            - stderr: Raw stderr
    """
    try:
        # Handle string vs list command
        if isinstance(command, str):
            # Use shell=True for string commands
            shell = True
            cmd = command
        else:
            # Use shell=False for list commands
            shell = False
            cmd = command
        
        # Execute command
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_data,
            **kwargs
        )
        
        # Convert output to requested datatype
        if return_datatype == str:
            value = result.stdout
        elif return_datatype == bytes:
            value = result.stdout.encode() if isinstance(result.stdout, str) else result.stdout
        elif return_datatype == list:
            value = result.stdout.splitlines() if result.stdout else []
        elif return_datatype == int:
            try:
                value = int(result.stdout.strip()) if result.stdout.strip() else 0
            except ValueError:
                value = 0
        elif return_datatype == float:
            try:
                value = float(result.stdout.strip()) if result.stdout.strip() else 0.0
            except ValueError:
                value = 0.0
        else:
            value = result.stdout
        
        return ExitCode(
            OK=(result.returncode == 0),
            exit_code=result.returncode,
            value=value,
            stdout=result.stdout,
            stderr=result.stderr
        )
    
    except subprocess.TimeoutExpired as e:
        return ExitCode(
            OK=False,
            exit_code=-1,
            value=None,
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=f"Command timed out after {timeout} seconds"
        )
    
    except Exception as e:
        return ExitCode(
            OK=False,
            exit_code=-1,
            value=None,
            stdout="",
            stderr=str(e)
        )


def run_command(command: str, **kwargs) -> ExitCode:
    """Alias for dorunrun for compatibility"""
    return dorunrun(command, **kwargs)


if __name__ == '__main__':
    # Test the module
    result = dorunrun("echo 'Hello, World!'")
    print(f"OK: {result.OK}")
    print(f"Exit Code: {result.exit_code}")
    print(f"Output: {result.value}")
