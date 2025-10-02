#!/bin/bash
# ========================================
# ENTERPRISE TENSORFLOW SILENCE WRAPPER
# System-level stderr suppression for C++ mutex messages
# ========================================

# Export environment variables at shell level (highest priority)
export TF_CPP_MIN_LOG_LEVEL=3
export CUDA_VISIBLE_DEVICES=""
export TF_ENABLE_ONEDNN_OPTS=0
export TF_FORCE_GPU_ALLOW_GROWTH=false
export PYTHONPATH=.

# Suppress TensorFlow internal logging
export TF_CPP_VMODULE=""
export TF_CPP_VLOG_LEVEL=0

# Run Python with stderr filtered to remove mutex messages
python3 multi_signal_bot.py "$@" 2>&1 | grep -v "RAW: Lock blocking" | grep -v "mutex.cc"
