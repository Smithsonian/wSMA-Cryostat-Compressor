#!/bin/bash
CONDA_PREFIX='/opt/mamba';
CONDA_ENV='compressor_smax_daemon';

eval "$CONDA_PREFIX/envs/$CONDA_ENV/bin/python compressor_smax_daemon.py";
