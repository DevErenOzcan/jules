"""!
@file __init__.py
@brief Initializes the 'vision' subpackage for the Vision Service modules.

This file makes vision processing classes (`FaceDetector`, `FaceTracker`,
`FrameProcessor`) available directly under the `modules.vision` namespace.
It defines `__all__` for the public interface of this subpackage.
"""

from .face_detector import FaceDetector
from .face_tracker import FaceTracker
from .frame_processor import FrameProcessor

__all__ = ['FaceDetector', 'FaceTracker', 'FrameProcessor']
