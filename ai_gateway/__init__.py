#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Gateway Package
Sistema de gateway para APIs de IA
"""

__version__ = "1.0.0"
__author__ = "Maveretta Bot Team"

# Exportar componentes principais
from . import auth
from . import models
from . import middleware

__all__ = ["auth", "models", "middleware"]
