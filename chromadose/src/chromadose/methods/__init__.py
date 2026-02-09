"""Dose solving methods for chromadose."""

from chromadose.methods.base import DoseSolver
from chromadose.methods.mayer import MayerSolver
from chromadose.methods.micke import MickeSolver
from chromadose.methods.multigaussian import MultigaussianCalibration, MultigaussianSolver

__all__ = [
    "DoseSolver",
    "MayerSolver",
    "MickeSolver",
    "MultigaussianCalibration",
    "MultigaussianSolver",
    "get_solver",
]

_SOLVERS: dict[str, type] = {
    "micke": MickeSolver,
    "mayer": MayerSolver,
}


def get_solver(method: str) -> type:
    """Get a dose solver class by method name.

    Parameters:
        method: One of "micke", "mayer", "multigaussian".

    Returns:
        The solver class (not an instance).
    """
    method = method.lower()
    if method not in _SOLVERS:
        available = ", ".join(sorted(_SOLVERS.keys()))
        raise ValueError(f"Unknown method '{method}'. Available: {available}")
    return _SOLVERS[method]
