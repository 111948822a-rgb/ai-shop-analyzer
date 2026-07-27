from app.adapters.base import AdapterRegistry, BaseAdapter
from app.adapters import douyin  # noqa: F401  触发抖店适配器自注册

__all__ = ["AdapterRegistry", "BaseAdapter", "douyin"]
