"""chromadose — Modern multichannel radiochromic film dosimetry.

RESEARCH USE ONLY — NOT A MEDICAL DEVICE.

chromadose is open-source software for academic research and method
development in radiochromic film dosimetry. It is NOT intended for
diagnosis, treatment planning, or clinical decision-making, and has
not been evaluated by the FDA, MHRA, or any Notified Body under EU MDR.
Clinical use is the sole responsibility of a qualified medical physicist
operating under their institution's QA programme. See DISCLAIMER.md.
"""

from chromadose.calibration import Calibration
from chromadose.core.types import CalibrationData, DoseMap, FilmScan

__version__ = "0.9.1"
__all__ = ["Calibration", "CalibrationData", "DoseMap", "FilmScan"]
