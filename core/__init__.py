"""
Benson Core System

This module contains the shared core architecture components for Benson,
the multi-signal decision bot. It provides the foundation for data ingestion,
normalization, ML pipelines, and module management.
"""

from .data_processor import DataProcessor
from .module_manager import ModuleManager
from .pipeline import Pipeline

__all__ = ["ModuleManager", "DataProcessor", "Pipeline"]
