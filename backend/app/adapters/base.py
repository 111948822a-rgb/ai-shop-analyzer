"""适配器层：把各电商平台原始数据清洗为 Standard* DTO。

未来接入新平台（快手、京东…）只需新增一个 Adapter 子类并注册即可，
上层服务（预处理 / AI 引擎）完全不感知平台差异。
"""
from __future__ import annotations

import abc
from typing import Iterable

from app.models.standard import (
    Platform,
    StandardInfluencerDTO,
    StandardOrderDTO,
    StandardProductDTO,
)


class BaseAdapter(abc.ABC):
    """所有平台适配器的抽象基类。"""

    platform: Platform

    @abc.abstractmethod
    def pull_orders(self, **kwargs) -> Iterable[StandardOrderDTO]:
        """从平台 API 拉取订单并归一化为 StandardOrderDTO。"""

    @abc.abstractmethod
    def pull_products(self, **kwargs) -> Iterable[StandardProductDTO]:
        """拉取商品并归一化为 StandardProductDTO。"""

    def pull_influencers(self, **kwargs) -> Iterable[StandardInfluencerDTO]:
        """默认空实现；平台不支持达人数据时无需重写。"""
        return []


class AdapterRegistry:
    """适配器注册表：按平台名路由到具体实现。"""

    _adapters: dict[Platform, BaseAdapter] = {}

    @classmethod
    def register(cls, adapter: BaseAdapter) -> None:
        cls._adapters[adapter.platform] = adapter

    @classmethod
    def get(cls, platform: Platform) -> BaseAdapter:
        try:
            return cls._adapters[platform]
        except KeyError:
            raise KeyError(f"未注册平台适配器: {platform}")

    @classmethod
    def available(cls) -> list[str]:
        return [p.value for p in cls._adapters]


# ---- 适配器注册 ----
# 具体适配器在各自模块内 self-register（见 app/adapters/douyin.py 底部）。
# 导入 app.adapters 包即触发所有适配器注册；淘宝同理，另建 TaobaoAdapter 后再：
#   AdapterRegistry.register(TaobaoAdapter())
