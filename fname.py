#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fname.py - Filename utilities
Part of hpclib - included for standalone operation
"""
import typing
from typing import *

import os
import sys
from pathlib import Path


class Fname:
    """Filename and path utilities"""
    
    def __init__(self, filepath: str):
        """
        Initialize with a file path
        
        Args:
            filepath: Path to file (usually __file__)
        """
        self.path = Path(filepath).resolve()
        self.fullpath = str(self.path)
        self.directory = str(self.path.parent)
        self.filename = self.path.name
        self.basename = self.path.stem
        self.extension = self.path.suffix
    
    def __str__(self):
        """String representation"""
        return self.basename
    
    def __repr__(self):
        """Repr representation"""
        return f"Fname('{self.fullpath}')"
    
    @property
    def parent(self):
        """Get parent directory"""
        return str(self.path.parent)
    
    @property
    def name(self):
        """Get filename without extension"""
        return self.basename
    
    @property
    def exists(self):
        """Check if file exists"""
        return self.path.exists()
    
    def with_extension(self, ext: str):
        """Get filename with different extension"""
        if not ext.startswith('.'):
            ext = '.' + ext
        return str(self.path.with_suffix(ext))
    
    def with_suffix(self, suffix: str):
        """Add suffix before extension"""
        return str(self.path.with_name(f"{self.basename}{suffix}{self.extension}"))
    
    def sibling(self, name: str):
        """Get sibling file in same directory"""
        return str(self.path.parent / name)


def get_script_name(filepath: str = None) -> str:
    """
    Get the name of the calling script
    
    Args:
        filepath: Path to script (usually __file__)
        
    Returns:
        Script name without extension
    """
    if filepath is None:
        import inspect
        frame = inspect.currentframe().f_back
        filepath = frame.f_code.co_filename
    
    return Path(filepath).stem


def get_script_dir(filepath: str = None) -> str:
    """
    Get the directory of the calling script
    
    Args:
        filepath: Path to script (usually __file__)
        
    Returns:
        Directory path
    """
    if filepath is None:
        import inspect
        frame = inspect.currentframe().f_back
        filepath = frame.f_code.co_filename
    
    return str(Path(filepath).parent.resolve())


if __name__ == '__main__':
    # Test the module
    f = Fname(__file__)
    print(f"Fullpath: {f.fullpath}")
    print(f"Directory: {f.directory}")
    print(f"Filename: {f.filename}")
    print(f"Basename: {f.basename}")
    print(f"Extension: {f.extension}")
    print(f"String: {f}")
