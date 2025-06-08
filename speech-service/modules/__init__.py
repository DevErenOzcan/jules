"""!
@file __init__.py
@brief Initializes the 'modules' package for the Speech Detection Service.

This file marks the directory as a Python package and makes key classes
and functions from its submodules available directly under the `modules` namespace.
It defines `__all__` to specify the public interface of this package,
including components like `SpeechDetector`, `SpeechDetectionServicer`,
`Config`, and `setup_logging`.
"""

# Alt modüllerin dışa aktarılması
from .speech_detector import SpeechDetector
from .service import SpeechDetectionServicer
from .config import Config
from .utils import setup_logging

__all__ = [
    'SpeechDetector',
    'SpeechDetectionServicer',
    'Config',
    'setup_logging'
]
