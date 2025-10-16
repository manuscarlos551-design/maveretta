# interfaces/web/helpers/mongodb.py
"""Cliente MongoDB otimizado"""
import os
from typing import List, Dict
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timedelta
import streamlit as st

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = "maveretta"

@st.cache_resource
def get_mongo_client():
    """Cliente MongoDB (singleton)"""
    try:
        return MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    except:
        return None

def get_consensus_rounds(limit: int = 50) -> List[Dict]:
    """Busca rodadas de consenso do MongoDB"""
    try:
        client = get_mongo_client()
        if not client:
            return []
        db = client[DB_NAME]
        rounds = list(db.agent_consensus.find().sort("decided_at", DESCENDING).limit(limit))
        for r in rounds:
            r['_id'] = str(r['_id'])  # Converter ObjectId para string
        return rounds
    except:
        return []

def get_agent_decisions(limit: int = 100, agent_id: str = None) -> List[Dict]:
    """Busca decisões de agentes"""
    try:
        client = get_mongo_client()
        if not client:
            return []
        db = client[DB_NAME]
        query = {"agent_id": agent_id} if agent_id else {}
        decisions = list(db.agent_decisions.find(query).sort("timestamp", DESCENDING).limit(limit))
        for d in decisions:
            d['_id'] = str(d['_id'])
        return decisions
    except:
        return []

def get_paper_trades(status: str = None) -> List[Dict]:
    """Busca paper trades"""
    try:
        client = get_mongo_client()
        if not client:
            return []
        db = client[DB_NAME]
        query = {"status": status} if status else {}
        trades = list(db.paper_trades.find(query).sort("opened_at", DESCENDING))
        for t in trades:
            t['_id'] = str(t['_id'])
        return trades
    except:
        return []

def get_live_trades(status: str = None) -> List[Dict]:
    """Busca live trades"""
    try:
        client = get_mongo_client()
        if not client:
            return []
        db = client[DB_NAME]
        query = {"status": status} if status else {}
        trades = list(db.live_trades.find(query).sort("opened_at", DESCENDING))
        for t in trades:
            t['_id'] = str(t['_id'])
        return trades
    except:
        return []
