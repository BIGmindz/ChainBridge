import pytest
from core.module_manager import ModuleManager, Module


class ExampleModule(Module):
    VERSION = "0.0.1"

    def process(self, data):
        return {"echo": data.get("value", 0) + 1}

    def get_schema(self):
        return {"input": ["value"], "output": ["echo"]}


def test_register_and_list_modules() -> None:
    mm = ModuleManager()
    mm.register_module("Example", ExampleModule())
    assert "ExampleModule" not in mm.list_modules()  # uses registered name key
    assert "Example" in mm.list_modules()


def test_execute_module() -> None:
    mm = ModuleManager()
    mm.register_module("Example", ExampleModule())
    result = mm.execute_module("Example", {"value": 41})
    assert result["echo"] == 42


def test_execute_missing_module() -> None:
    mm = ModuleManager()
    with pytest.raises(ValueError):
        mm.execute_module("Missing", {})


def test_invalid_input_rejected() -> None:
    class BadModule(ExampleModule):
        def validate_input(self, data):  # override to force failure
            return False

    mm = ModuleManager()
    mm.register_module("Bad", BadModule())
    with pytest.raises(ValueError):
        mm.execute_module("Bad", {"value": 1})
