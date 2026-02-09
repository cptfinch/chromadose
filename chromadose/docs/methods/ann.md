# Neural Network Method (ANN)

!!! info "Reference"
    Chang L-Y, et al. "GANN: a generalized artificial neural network for multichannel radiochromic film dosimetry." *Phys. Med. Biol.* 2025.

## Theory

A feedforward neural network that learns the nonlinear mapping from RGB pixel values to dose directly from calibration data. Key advantages:

- No rational function assumption
- Can potentially generalize across film batches
- Uncertainty from ensemble of networks

**Architecture:**

```
Input: [R, G, B] (3 neurons)
  → Hidden 1: 32 neurons, ReLU
  → Hidden 2: 32 neurons, ReLU
  → Output: dose (1 neuron, ReLU)
```

## Usage

```python
from chromadose.methods import ANNCalibration, ANNSolver

# Train on calibration data
ann_cal = ANNCalibration(n_hidden=32, n_ensemble=5)
ann_cal.fit(pixels, doses)  # (N, 3), (N,)

# Solve
solver = ANNSolver(ann_cal)
dose_map = solver.solve(film, calibration)
```

## Implementation Details

- Pure numpy/scipy — **no PyTorch dependency** for the core implementation
- L-BFGS-B optimization with He initialization
- Bootstrap sampling for ensemble diversity
- Uncertainty from standard deviation across ensemble members

## Performance

- Training: depends on data size and `max_iter`
- Inference on 550x500: **~1s** (forward pass through ensemble)
