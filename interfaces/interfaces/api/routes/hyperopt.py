# interfaces/api/routes/hyperopt.py
# -- coding: utf-8 --

from typing import Any, Dict, Optional, List
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

# Importes do core — sem instanciar nada no import-time
try:
    from core.runners import MaverettaHyperoptRunner, optimize_slot_strategy  # type: ignore
except Exception as e:
    # Mantém o import error visível no log, mas deixa o módulo carregar
    MaverettaHyperoptRunner = None  # type: ignore
    optimize_slot_strategy = None   # type: ignore
    import logging
    logging.getLogger(_name_).error("Erro importando core.runners: %s", e)

router = APIRouter(prefix="/hyperopt", tags=["hyperopt"])

# ------- Modelos Pydantic (compatível com Pydantic v2) -------

class ParamBound(BaseModel):
    min: float = Field(..., description="Valor mínimo do parâmetro")
    max: float = Field(..., description="Valor máximo do parâmetro")
    step: Optional[float] = Field(None, description="Passo (quando aplicável)")

class ParamSpaceModel(BaseModel):
    """
    Espaço de parâmetros no formato:
    {
      "rsi_length": {"min": 5, "max": 30, "step": 1},
      "ema_fast": {"min": 5, "max": 50, "step": 1},
      ...
    }
    """
    _root_: Dict[str, ParamBound]

    # Pydantic v2: se preferir evitar _root_, pode usar:
    # params: Dict[str, ParamBound]
    # e ajustar o restante do código.

class HyperoptRequest(BaseModel):
    symbol: str = Field(..., examples=["BTC/USDT"])
    timeframe: str = Field(..., examples=["1m", "5m", "15m"])
    strategy_name: str = Field(..., examples=["rsi_ema_scalp"])
    # Se optar por evitar _root_, troque para: param_space: Dict[str, ParamBound]
    param_space: ParamSpaceModel
    max_evals: int = Field(50, ge=1, le=1000)
    seed: Optional[int] = Field(None)

class HyperoptResult(BaseModel):
    best_params: Dict[str, Any]
    best_score: float
    trials: int
    runtime_sec: float


# ------- Rotas -------

@router.post("/run", response_model=HyperoptResult)
def run_hyperopt(
    payload: HyperoptRequest = Body(..., description="Configuração do Hyperopt")
):
    """
    Executa Hyperopt para uma estratégia/slot sem instanciar nada no import-time.
    Os objetos do core são criados aqui, com os parâmetros do request.
    """

    if MaverettaHyperoptRunner is None:
        raise HTTPException(
            status_code=500,
            detail="Módulos core.runners não carregados — verifique build/instalação."
        )

    # Extrai param_space do _root_ (se manteve o RootModel)
    if isinstance(payload.param_space, ParamSpaceModel):
        param_space_dict: Dict[str, Any] = payload.param_space._root_
    else:
        # Caso você tenha trocado para um campo 'params' ao invés de _root_
        param_space_dict = dict(payload.param_space)  # fallback

    try:
        runner = MaverettaHyperoptRunner(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            strategy_name=payload.strategy_name,
            param_space=param_space_dict,
            max_evals=payload.max_evals,
            seed=payload.seed,
        )
    except TypeError as te:
        # Se a assinatura do _init_ do Runner for diferente, expõe erro claro
        raise HTTPException(
            status_code=500,
            detail=f"Assinatura inesperada em MaverettaHyperoptRunner._init_: {te}"
        )

    try:
        result = runner.run()
        # Espera-se que result traga chaves compatíveis com o schema HyperoptResult
        # Adapte aqui caso o runner retorne outro formato
        best_params = result.get("best_params", {})
        best_score = float(result.get("best_score", 0.0))
        trials = int(result.get("trials", payload.max_evals))
        runtime_sec = float(result.get("runtime_sec", 0.0))

        return HyperoptResult(
            best_params=best_params,
            best_score=best_score,
            trials=trials,
            runtime_sec=runtime_sec,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha na execução do hyperopt: {e}")


@router.post("/optimize-slot", response_model=HyperoptResult)
def optimize_slot(
    symbol: str = Body(..., embed=True),
    timeframe: str = Body(..., embed=True),
    strategy_name: str = Body(..., embed=True),
    param_space: Dict[str, Any] = Body(..., embed=True),
    max_evals: int = Body(50, embed=True),
):
    """
    Variante alternativa que delega para função utilitária (se existir).
    Não instancia objetos no import-time.
    """
    if optimize_slot_strategy is None:
        raise HTTPException(
            status_code=500,
            detail="Função optimize_slot_strategy indisponível em core.runners."
        )

    try:
        out = optimize_slot_strategy(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            param_space=param_space,
            max_evals=max_evals,
        )

        return HyperoptResult(
            best_params=out.get("best_params", {}),
            best_score=float(out.get("best_score", 0.0)),
            trials=int(out.get("trials", max_evals)),
            runtime_sec=float(out.get("runtime_sec", 0.0)),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha na otimização do slot: {e}")