#!/usr/bin/env python3
"""
Gateway App - Expõe a aplicação FastAPI do interfaces.api.main
Solução para problema de imports no container Docker
"""

import sys
import os
from pathlib import Path

# Garantir que o diretório raiz está no sys.path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Importar a aplicação
from interfaces.api.main import app

# Expor a aplicação para uvicorn
__all__ = ['app']
