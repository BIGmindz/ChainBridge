#!/bin/bash
# ChainBridge Python Environment Sanity Check

echo "Python:" $(which python)
echo "Python3:" $(which python3)
echo "Python version:" $(python -V)
echo "Sys.executable:" $(python - << 'EOF'
import sys; print(sys.executable)
EOF
)
