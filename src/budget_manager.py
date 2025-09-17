"""
This module re-exports the BudgetManager class from the root module
for compatibility with the new path structure
"""

import sys
import os
import importlib.util

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try to import from the parent directory
    from budget_manager import BudgetManager
except ImportError:
    print("⚠️ Couldn't import BudgetManager directly, creating reference")
    
    # If that fails, try to load it dynamically
    try:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        spec = importlib.util.spec_from_file_location(
            "budget_manager", 
            os.path.join(parent_dir, "budget_manager.py")
        )
        budget_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(budget_module)
        BudgetManager = budget_module.BudgetManager
    except Exception as e:
        print(f"❌ Failed to load BudgetManager: {e}")
        
        # Provide a simple implementation as fallback
        class BudgetManager:
            def __init__(self, initial_capital=10000.0):
                self.initial_capital = initial_capital
                self.current_capital = initial_capital
                self.available_capital = initial_capital
                self.risk_parameters = {
                    'max_risk_per_trade': 0.02,
                    'max_positions': 5,
                    'position_size_method': 'kelly'
                }
                print(f"💰 Simple Budget Manager initialized with ${initial_capital:,.2f}")

# Make it clear what's being exported
__all__ = ['BudgetManager']