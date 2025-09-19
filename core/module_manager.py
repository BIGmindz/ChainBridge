"""
Module Manager for Benson Core System

This module provides the plug-and-play interface for loading and managing
different modules in the Benson architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import importlib
import inspect


class Module(ABC):
    """Base class for all Benson modules."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self.version = getattr(self, "VERSION", "1.0.0")

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results."""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the input/output schema for this module."""
        pass

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data against module schema."""
        # Basic validation - can be extended
        return isinstance(data, dict)


class ModuleManager:
    """Manages the loading and execution of modules."""

    def __init__(self):
        self.modules: Dict[str, Module] = {}
        self.module_configs: Dict[str, Dict[str, Any]] = {}

    def register_module(self, name: str, module: Module) -> None:
        """Register a module instance."""
        self.modules[name] = module

    def load_module(self, module_path: str, config: Dict[str, Any] = None) -> str:
        """
        Dynamically load a module from a path.
        Returns the module name for future reference.
        """
        try:
            # Import the module
            module_parts = module_path.split(".")
            _module_name = module_parts[-1]

            imported_module = importlib.import_module(module_path)

            # Find the Module class in the imported module
            module_class = None
            for name, obj in inspect.getmembers(imported_module):
                if inspect.isclass(obj) and issubclass(obj, Module) and obj != Module:
                    module_class = obj
                    break

            if not module_class:
                raise ValueError(f"No Module class found in {module_path}")

            # Create instance
            module_instance = module_class(config)
            # Use the class name as the module name for consistency
            class_name = module_class.__name__
            self.register_module(class_name, module_instance)

            return class_name

        except Exception as e:
            raise ImportError(f"Failed to load module {module_path}: {str(e)}")

    def get_module(self, name: str) -> Optional[Module]:
        """Get a registered module by name."""
        return self.modules.get(name)

    def execute_module(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a module with the given data."""
        module = self.get_module(name)
        if not module:
            raise ValueError(f"Module {name} not found")

        if not module.validate_input(data):
            raise ValueError(f"Invalid input data for module {name}")

        return module.process(data)

    def list_modules(self) -> List[str]:
        """List all registered modules."""
        return list(self.modules.keys())

    def get_module_info(self, name: str) -> Dict[str, Any]:
        """Get information about a module."""
        module = self.get_module(name)
        if not module:
            return {}

        return {
            "name": module.name,
            "version": module.version,
            "schema": module.get_schema(),
            "config": module.config,
        }
