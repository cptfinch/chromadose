# Installation

## Basic Install

```bash
pip install chromadose
```

## Optional Extras

```bash
# DICOM RT Dose import (requires pydicom)
pip install chromadose[dicom]

# PyTorch GPU acceleration for neural network method
pip install chromadose[ann-gpu]

# Development tools (pytest, mypy, ruff)
pip install chromadose[dev]
```

## From Source

```bash
git clone https://github.com/cptfinch/chromadose.git
cd chromadose
pip install -e ".[dev]"
```

## Requirements

- Python >= 3.11
- numpy >= 1.24
- scipy >= 1.10
- tifffile >= 2023.1
- matplotlib >= 3.7

## Verify Installation

```python
import chromadose
print(chromadose.__version__)  # 1.0.0
```

Or from the command line:

```bash
chromadose --version
```
