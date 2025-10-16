#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Gateway Package
REST API para controle do bot, backtesting, analytics e monitoramento.
"""

__version__ = "1.0.0"
__author__ = "Bot AI Team"

from .slot_context import (
    bind_slot,
    labels_for_metrics,
    get_current_slot,
    update_slot_stage,
    create_child_slot,
    propagate_slot_headers
)

__all__ = [
    "bind_slot",
    "labels_for_metrics",
    "get_current_slot",
    "update_slot_stage",
    "create_child_slot",
    "propagate_slot_headers",
]
