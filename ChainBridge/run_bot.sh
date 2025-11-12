#!/bin/bash
# Enterprise-grade mutex suppression wrapper

# 1. Suppress TensorFlow and CUDA at environment level
export TF_CPP_MIN_LOG_LEVEL=3
export CUDA_VISIBLE_DEVICES=""
export TF_ENABLE_ONEDNN_OPTS=0
export TF_FORCE_GPU_ALLOW_GROWTH=false

# 2. File descriptor redirection to suppress C++ mutex messages
exec 3>&2 # Save stderr
exec 2> >(grep -v "RAW: Lock blocking" >&3) # Filter mutex messages

# 3. Add current directory to Python path
export PYTHONPATH=.

# 4. Run bot with all suppressions active
python3 multi_signal_bot.py "$@"

# 5. Restore stderr
exec 2>&3
