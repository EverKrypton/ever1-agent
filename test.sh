#!/bin/bash
# Test sed command
sed 's/BOLD = /DIM = \x27\\033[2m\x27\n    BOLD = /' /home/ubuntu/ai-agent/client.py | head -40