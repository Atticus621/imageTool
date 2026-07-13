"""Generic core modules — reusable across any domain.

Import from here to get the domain-agnostic parts:
    from core.generic import NodeBase, EventEmitter, PipelineNodeInfo
"""

# Node framework
from core.node_base.node import NodeBase, NodeMeta, NodeState, ParamType, ParamDefinition, ParamOption
from core.node_base.port import Port, PortDefinition, PortType, PortDirection
from core.node_base.port_config import PortConfig
from core.node_base.registry import NodeRegistry, node_registry

# Event system
from core.events import EventEmitter

# Pipeline
from core.pipeline import PipelineNodeInfo

# System infrastructure
from systems.base import ISystem
from systems.registry import SystemRegistry

__all__ = [
    # Node framework
    "NodeBase", "NodeMeta", "NodeState", "ParamType", "ParamDefinition", "ParamOption",
    "Port", "PortDefinition", "PortType", "PortDirection", "PortConfig",
    "NodeRegistry", "node_registry",
    # Events
    "EventEmitter",
    # Pipeline
    "PipelineNodeInfo",
    # Systems
    "ISystem", "SystemRegistry",
]
