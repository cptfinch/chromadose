"""Dose solving methods for chromadose."""

from chromadose.methods.base import DoseSolver
from chromadose.methods.micke import MickeSolver

__all__ = ["DoseSolver", "MickeSolver", "get_solver"]

_SOLVERS: dict[str, type[DoseSolver]] = {
    "micke": MickeSolver,
}


def get_solver(method: str) -> type[DoseSolver]:
    """Get a dose solver class by method name.

    Parameters:
        method: One of "micke", "mayer", "multigaussian", "ann".

    Returns:
        The solver class (not an instance).
    """
    method = method.lower()
    if method not in _SOLVERS:
        available = ", ".join(sorted(_SOLVERS.keys()))
        raise ValueError(f"Unknown method '{method}'. Available: {available}")
    return _SOLVERS[method]
