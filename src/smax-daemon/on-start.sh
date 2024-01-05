#!/bin/bash
source $HOME/.bashrc
micromamba activate compressor # change to your conda environment's name
# -u: unbuffered output
python -u $HOME/.config/systemd/user/compressor-smax-daemon/compressor-smax-daemon.py
