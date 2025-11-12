#!/usr/bin/env python3
"""
Test trading system without TensorFlow dependencies
"""
import os
import sys

# Prevent TensorFlow from being imported
sys.modules['tensorflow'] = None
sys.modules['tf'] = None

# Add environment variables to disable TensorFlow
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    from automated_trader import main
    print("✅ Successfully started automated trader without TensorFlow!")
    main()
except Exception as e:
    print(f"❌ Error: {e}")
    print("Trying simpler approach...")
    from multi_signal_bot import run_multi_signal_bot
    run_multi_signal_bot()
