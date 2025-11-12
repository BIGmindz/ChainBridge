#!/usr/bin/env python3

"""
Test the logistics signal module by running it directly
"""

import os
import traceback


def test_logistics():
    print("\n🧪 TESTING LOGISTICS MODULE DIRECTLY")
    print("=" * 60)

    # First, check the file structure
    module_path = "modules/logistics_signal_module.py"
    if not os.path.exists(module_path):
        print(f"ERROR: Module file {module_path} not found!")
        return

    print(f"Module file exists: {module_path}")

    # Import manually with exec to isolate errors
    try:
        # Create the directory for cache if it doesn't exist
        os.makedirs("cache", exist_ok=True)

        # Try to run the module directly
        print("\n🚀 Running the logistics module...")
        os.system(f"python3 {module_path}")

    except Exception as e:
        print(f"ERROR executing module: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_logistics()
