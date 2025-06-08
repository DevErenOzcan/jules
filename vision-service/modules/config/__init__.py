"""!
@file __init__.py
@brief Initializes the 'config' subpackage for the Vision Service modules.

This file makes the core configuration classes (`ConfigManager`, `GrpcConfig`)
and the logger setup function (`setup_logger`) available directly under the
`modules.config` namespace. It defines `__all__` for the public interface.
"""

from .config_manager import ConfigManager
from .grpc_config import GrpcConfig
from .logger_config import setup_logger

__all__ = ['ConfigManager', 'GrpcConfig', 'setup_logger']
