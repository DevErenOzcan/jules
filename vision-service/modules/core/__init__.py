"""!
@file __init__.py
@brief Initializes the 'core' subpackage for the Vision Service modules.

This file makes the main gRPC service implementation class, `VisionServiceServicer`,
available directly under the `modules.core` namespace. It defines `__all__`
for the public interface of this subpackage.
"""

from .vision_service import VisionServiceServicer

__all__ = ['VisionServiceServicer']
