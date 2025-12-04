#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linuxutils.py - Linux system utilities
Part of hpclib - included for standalone operation
"""
import typing
from typing import *

import os
import sys
import pwd
import grp
import socket
import platform
from pathlib import Path
from datetime import datetime


def get_username() -> str:
    """Get current username"""
    return os.getenv('USER') or os.getenv('USERNAME') or pwd.getpwuid(os.getuid()).pw_name


def get_hostname() -> str:
    """Get system hostname"""
    return socket.gethostname()


def get_fqdn() -> str:
    """Get fully qualified domain name"""
    return socket.getfqdn()


def get_uid() -> int:
    """Get user ID"""
    return os.getuid()


def get_gid() -> int:
    """Get group ID"""
    return os.getgid()


def get_groups() -> list:
    """Get list of group names user belongs to"""
    groups = os.getgroups()
    return [grp.getgrgid(gid).gr_name for gid in groups]


def get_home_dir() -> str:
    """Get user's home directory"""
    return str(Path.home())


def get_temp_dir() -> str:
    """Get system temporary directory"""
    return os.getenv('TMPDIR') or '/tmp'


def is_root() -> bool:
    """Check if running as root"""
    return os.getuid() == 0


def get_system_info() -> dict:
    """Get system information"""
    return {
        'hostname': get_hostname(),
        'fqdn': get_fqdn(),
        'username': get_username(),
        'uid': get_uid(),
        'gid': get_gid(),
        'groups': get_groups(),
        'home': get_home_dir(),
        'is_root': is_root(),
        'platform': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
    }


def file_age(filepath: str) -> float:
    """
    Get age of file in seconds
    
    Args:
        filepath: Path to file
        
    Returns:
        Age in seconds
    """
    stat = Path(filepath).stat()
    return datetime.now().timestamp() - stat.st_mtime


def file_size(filepath: str) -> int:
    """
    Get file size in bytes
    
    Args:
        filepath: Path to file
        
    Returns:
        Size in bytes
    """
    return Path(filepath).stat().st_size


def disk_usage(path: str = '/') -> dict:
    """
    Get disk usage statistics
    
    Args:
        path: Path to check
        
    Returns:
        Dictionary with total, used, free space in bytes
    """
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bfree * stat.f_frsize
    used = total - free
    
    return {
        'total': total,
        'used': used,
        'free': free,
        'percent_used': (used / total * 100) if total > 0 else 0
    }


def is_executable(filepath: str) -> bool:
    """Check if file is executable"""
    return os.access(filepath, os.X_OK)


def make_executable(filepath: str):
    """Make file executable"""
    current_mode = os.stat(filepath).st_mode
    os.chmod(filepath, current_mode | 0o111)


def ensure_dir(dirpath: str):
    """Ensure directory exists, create if needed"""
    Path(dirpath).mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    # Test the module
    info = get_system_info()
    print("System Information:")
    for key, value in info.items():
        print(f"  {key}: {value}")
