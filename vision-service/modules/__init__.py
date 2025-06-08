"""!
@file __init__.py
@brief Initializes the 'modules' package for the Vision Service.

This file makes key classes and functions from submodules (config, vision,
network, core) directly available under the `modules` namespace.
It also defines the `__all__` variable to specify the public interface
of the package.
"""
# Alt paketlerden modülleri içe aktar
from .config import setup_logger, GrpcConfig, ConfigManager
from .vision import FaceDetector, FaceTracker, FrameProcessor
from .network import GrpcServer, ServiceClient, ResponseBuilder
from .core import VisionServiceServicer

__all__ = [
    'setup_logger', 'GrpcConfig', 'ConfigManager',
    'FaceDetector', 'FaceTracker', 'FrameProcessor', 
    'GrpcServer', 'ServiceClient', 'ResponseBuilder',
    'VisionServiceServicer'
]
