# core/runners/backtest_cache.py
"""
Maveretta Backtest Cache - Adaptação do Freqtrade para Maveretta
Sistema de cache inteligente para backtests integrado com slots
Origem: freqtrade/optimize/backtest_caching.py
"""

import logging
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import json
import pandas as pd

logger = logging.getLogger(__name__)

class MaverettaBacktestCache:
    """
    Cache inteligente para resultados de backtest
    Otimiza performance evitando recálculos desnecessários
    """
    
    def __init__(self, cache_dir: str = "./data/backtest_cache"):
        """
        Inicializa o sistema de cache
        
        Args:
            cache_dir: Diretório para armazenar cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdiretórios
        self.results_cache_dir = self.cache_dir / "results"
        self.data_cache_dir = self.cache_dir / "data"
        self.metadata_cache_dir = self.cache_dir / "metadata"
        
        for cache_subdir in [self.results_cache_dir, self.data_cache_dir, self.metadata_cache_dir]:
            cache_subdir.mkdir(exist_ok=True)
        
        # Configurações
        self.cache_ttl_hours = 24  # TTL padrão do cache
        self.max_cache_size_mb = 1000  # Tamanho máximo do cache em MB
        
        # Cache em memória para acesso rápido
        self._memory_cache: Dict[str, Any] = {}
        self._cache_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"[BACKTEST_CACHE] Initialized cache at {self.cache_dir}")
    
    def get_cache_key(
        self,
        slot_id: str,
        pair: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        strategy: str,
        config_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Gera chave única de cache baseada nos parâmetros do backtest
        
        Args:
            slot_id: ID do slot
            pair: Par de trading
            timeframe: Timeframe
            start_date: Data de início
            end_date: Data de fim
            strategy: Nome da estratégia
            config_params: Parâmetros de configuração adicionais
            
        Returns:
            String única representando a chave de cache
        """
        # Criar string de parâmetros determinística
        params_str = f"{slot_id}|{pair}|{timeframe}|{start_date.isoformat()}|{end_date.isoformat()}|{strategy}"
        
        # Adicionar parâmetros de configuração se existirem
        if config_params:
            # Ordenar para garantir consistência
            sorted_params = sorted(config_params.items())
            params_str += "|" + json.dumps(sorted_params, sort_keys=True)
        
        # Gerar hash MD5
        cache_key = hashlib.md5(params_str.encode()).hexdigest()
        
        return cache_key
    
    def is_cache_valid(
        self,
        cache_key: str,
        force_refresh: bool = False
    ) -> bool:
        """
        Verifica se entrada do cache ainda é válida
        
        Args:
            cache_key: Chave do cache
            force_refresh: Forçar refresh ignorando cache
            
        Returns:
            True se cache é válido, False caso contrário
        """
        if force_refresh:
            return False
        
        # Verificar cache em memória
        if cache_key in self._memory_cache:
            metadata = self._cache_metadata.get(cache_key, {})
            cached_time = metadata.get('cached_at')
            
            if cached_time:
                cache_age = datetime.now() - datetime.fromisoformat(cached_time)
                if cache_age.total_seconds() < (self.cache_ttl_hours * 3600):
                    return True
        
        # Verificar cache em disco
        cache_file = self.results_cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                return cache_age.total_seconds() < (self.cache_ttl_hours * 3600)
            except Exception:
                return False
        
        return False
    
    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Recupera resultado do cache
        
        Args:
            cache_key: Chave do cache
            
        Returns:
            Dados do cache se disponível, None caso contrário
        """
        try:
            # Tentar cache em memória primeiro
            if cache_key in self._memory_cache:
                logger.debug(f"[BACKTEST_CACHE] Memory cache hit for {cache_key[:8]}")
                return self._memory_cache[cache_key]
            
            # Tentar cache em disco
            cache_file = self.results_cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Carregar no cache em memória
                self._memory_cache[cache_key] = cached_data
                self._cache_metadata[cache_key] = {
                    'cached_at': datetime.now().isoformat(),
                    'file_path': str(cache_file)
                }
                
                logger.debug(f"[BACKTEST_CACHE] Disk cache hit for {cache_key[:8]}")
                return cached_data
            
            return None
            
        except Exception as e:
            logger.warning(f"[BACKTEST_CACHE] Error reading cache {cache_key[:8]}: {e}")
            return None
    
    def cache_result(
        self,
        cache_key: str,
        result_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Salva resultado no cache
        
        Args:
            cache_key: Chave do cache
            result_data: Dados do resultado
            metadata: Metadados adicionais
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            # Salvar em memória
            self._memory_cache[cache_key] = result_data
            self._cache_metadata[cache_key] = {
                'cached_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Salvar em disco
            cache_file = self.results_cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(result_data, f, indent=2)
            
            # Salvar metadados separadamente
            if metadata:
                metadata_file = self.metadata_cache_dir / f"{cache_key}_meta.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            logger.info(f"[BACKTEST_CACHE] Cached result for {cache_key[:8]}")
            
            # Verificar tamanho do cache
            self._cleanup_cache_if_needed()
            
            return True
            
        except Exception as e:
            logger.error(f"[BACKTEST_CACHE] Error caching result {cache_key[:8]}: {e}")
            return False
    
    def cache_data_snapshot(
        self,
        cache_key: str,
        dataframe: pd.DataFrame,
        snapshot_metadata: Dict[str, Any]
    ) -> bool:
        """
        Salva snapshot de dados no cache
        
        Args:
            cache_key: Chave do cache
            dataframe: DataFrame com dados
            snapshot_metadata: Metadados do snapshot
            
        Returns:
            True se salvou com sucesso
        """
        try:
            # Salvar DataFrame como pickle para eficiência
            data_file = self.data_cache_dir / f"{cache_key}_data.pkl"
            dataframe.to_pickle(data_file)
            
            # Salvar metadados
            metadata_file = self.data_cache_dir / f"{cache_key}_data_meta.json"
            snapshot_metadata['cached_at'] = datetime.now().isoformat()
            snapshot_metadata['data_shape'] = dataframe.shape
            snapshot_metadata['data_columns'] = list(dataframe.columns)
            
            with open(metadata_file, 'w') as f:
                json.dump(snapshot_metadata, f, indent=2)
            
            logger.debug(f"[BACKTEST_CACHE] Cached data snapshot for {cache_key[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"[BACKTEST_CACHE] Error caching data snapshot: {e}")
            return False
    
    def get_cached_data_snapshot(self, cache_key: str) -> Optional[Tuple[pd.DataFrame, Dict[str, Any]]]:
        """
        Recupera snapshot de dados do cache
        
        Args:
            cache_key: Chave do cache
            
        Returns:
            Tupla com (DataFrame, metadados) se disponível, None caso contrário
        """
        try:
            data_file = self.data_cache_dir / f"{cache_key}_data.pkl"
            metadata_file = self.data_cache_dir / f"{cache_key}_data_meta.json"
            
            if not data_file.exists() or not metadata_file.exists():
                return None
            
            # Verificar se não expirou
            cache_age = datetime.now() - datetime.fromtimestamp(data_file.stat().st_mtime)
            if cache_age.total_seconds() > (self.cache_ttl_hours * 3600):
                return None
            
            # Carregar dados
            df = pd.read_pickle(data_file)
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            logger.debug(f"[BACKTEST_CACHE] Retrieved data snapshot for {cache_key[:8]}")
            return df, metadata
            
        except Exception as e:
            logger.warning(f"[BACKTEST_CACHE] Error retrieving data snapshot: {e}")
            return None
    
    def invalidate_cache(self, cache_key: str) -> bool:
        """
        Invalida entrada específica do cache
        
        Args:
            cache_key: Chave do cache
            
        Returns:
            True se invalidou com sucesso
        """
        try:
            # Remover do cache em memória
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            
            if cache_key in self._cache_metadata:
                del self._cache_metadata[cache_key]
            
            # Remover arquivos do disco
            files_to_remove = [
                self.results_cache_dir / f"{cache_key}.json",
                self.metadata_cache_dir / f"{cache_key}_meta.json",
                self.data_cache_dir / f"{cache_key}_data.pkl",
                self.data_cache_dir / f"{cache_key}_data_meta.json"
            ]
            
            for file_path in files_to_remove:
                if file_path.exists():
                    file_path.unlink()
            
            logger.info(f"[BACKTEST_CACHE] Invalidated cache for {cache_key[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"[BACKTEST_CACHE] Error invalidating cache {cache_key[:8]}: {e}")
            return False
    
    def clear_cache(self, older_than_hours: Optional[int] = None) -> int:
        """
        Limpa cache baseado na idade
        
        Args:
            older_than_hours: Limpar entradas mais antigas que X horas (None = limpar tudo)
            
        Returns:
            Número de entradas removidas
        """
        removed_count = 0
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours) if older_than_hours else None
        
        try:
            # Limpar cache em memória
            if cutoff_time is None:
                removed_count += len(self._memory_cache)
                self._memory_cache.clear()
                self._cache_metadata.clear()
            else:
                keys_to_remove = []
                for key, metadata in self._cache_metadata.items():
                    cached_time = datetime.fromisoformat(metadata.get('cached_at', '1970-01-01'))
                    if cached_time < cutoff_time:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    if key in self._memory_cache:
                        del self._memory_cache[key]
                    if key in self._cache_metadata:
                        del self._cache_metadata[key]
                    removed_count += 1
            
            # Limpar arquivos do disco
            for cache_subdir in [self.results_cache_dir, self.data_cache_dir, self.metadata_cache_dir]:
                for cache_file in cache_subdir.glob("*"):
                    if cutoff_time is None:
                        cache_file.unlink()
                        removed_count += 1
                    else:
                        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                        if file_time < cutoff_time:
                            cache_file.unlink()
                            removed_count += 1
            
            logger.info(f"[BACKTEST_CACHE] Cleared {removed_count} cache entries")
            return removed_count
            
        except Exception as e:
            logger.error(f"[BACKTEST_CACHE] Error clearing cache: {e}")
            return removed_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache
        
        Returns:
            Dict com estatísticas do cache
        """
        try:
            # Contar arquivos em cada diretório
            results_count = len(list(self.results_cache_dir.glob("*.json")))
            data_count = len(list(self.data_cache_dir.glob("*.pkl")))
            metadata_count = len(list(self.metadata_cache_dir.glob("*.json")))
            
            # Calcular tamanho do cache
            cache_size_bytes = sum(
                f.stat().st_size 
                for cache_subdir in [self.results_cache_dir, self.data_cache_dir, self.metadata_cache_dir]
                for f in cache_subdir.glob("*")
            )
            cache_size_mb = cache_size_bytes / (1024 * 1024)
            
            # Estatísticas de memória
            memory_entries = len(self._memory_cache)
            
            return {
                'cache_directory': str(self.cache_dir),
                'results_cached': results_count,
                'data_snapshots': data_count,
                'metadata_files': metadata_count,
                'memory_entries': memory_entries,
                'total_size_mb': round(cache_size_mb, 2),
                'cache_ttl_hours': self.cache_ttl_hours,
                'max_cache_size_mb': self.max_cache_size_mb
            }
            
        except Exception as e:
            logger.error(f"[BACKTEST_CACHE] Error getting cache stats: {e}")
            return {}
    
    def _cleanup_cache_if_needed(self) -> None:
        """Limpa cache se exceder tamanho máximo"""
        try:
            stats = self.get_cache_stats()
            current_size_mb = stats.get('total_size_mb', 0)
            
            if current_size_mb > self.max_cache_size_mb:
                # Limpar entradas mais antigas que 12 horas
                removed = self.clear_cache(older_than_hours=12)
                
                # Se ainda muito grande, limpar mais agressivamente
                stats_after = self.get_cache_stats()
                if stats_after.get('total_size_mb', 0) > self.max_cache_size_mb:
                    removed += self.clear_cache(older_than_hours=6)
                
                logger.info(f"[BACKTEST_CACHE] Cleanup removed {removed} entries")
                
        except Exception as e:
            logger.warning(f"[BACKTEST_CACHE] Error during cleanup: {e}")

# Funções de conveniência
def get_backtest_cache_key(slot_id: str, pair: str, timeframe: str, start_date: datetime, 
                          end_date: datetime, strategy: str, **kwargs) -> str:
    """Função de conveniência para gerar chave de cache"""
    cache = MaverettaBacktestCache()
    return cache.get_cache_key(slot_id, pair, timeframe, start_date, end_date, strategy, kwargs)