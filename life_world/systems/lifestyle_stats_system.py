"""
MANUWORLD V3 — LIFESTYLE STATS
Canonical PostgreSQL implementation. No local SQLite state.
"""
from __future__ import annotations
from typing import Any
from sqlalchemy import text
from life_world.database import AsyncSessionLocal

STAT_LIMITS={"health":(0,100),"joy":(0,100),"karma":(-100,100),"reputation":(0,100)}
STAT_LABELS={"health":"❤️ Santé","joy":"😊 Joie","karma":"😇 Karma","reputation":"⭐ Réputation"}

def clamp_stat(stat_name:str,value:int)->int:
    low,high=STAT_LIMITS[stat_name];return max(low,min(high,int(value)))

async def setup_lifestyle_database(): return None

async def ensure_player_stats(character_id:int):
    async with AsyncSessionLocal() as s:
        # Stats live on the character when columns exist; create a companion row for joy/karma/reputation.
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS mwl_lifestyle_stats(
                character_id BIGINT PRIMARY KEY REFERENCES life_characters(id) ON DELETE CASCADE,
                joy INTEGER NOT NULL DEFAULT 50,
                karma INTEGER NOT NULL DEFAULT 0,
                reputation INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await s.execute(text("""
            INSERT INTO mwl_lifestyle_stats(character_id)
            VALUES(:id) ON CONFLICT(character_id) DO NOTHING
        """),{"id":int(character_id)})
        await s.commit()

async def get_stats(character_id:int)->dict[str,int]:
    await ensure_player_stats(character_id)
    async with AsyncSessionLocal() as s:
        row=(await s.execute(text("""
            SELECT c.id,
                   COALESCE(c.health,100) AS health,
                   COALESCE(c.energy,100) AS energy,
                   COALESCE(c.happiness,100) AS happiness,
                   COALESCE(c.reputation,0) AS character_reputation,
                   s.joy,s.karma,s.reputation
            FROM life_characters c JOIN mwl_lifestyle_stats s ON s.character_id=c.id
            WHERE c.id=:id
        """),{"id":int(character_id)})).mappings().first()
    if not row:
        return {k:0 for k in STAT_LIMITS} | {"happiness":0,"energy":0,"social":0,"finance":0,"education":0,"career":0}
    return {
        "health":int(row["health"] or 0),
        "energy":int(row["energy"] or 0),
        "happiness":int(row["happiness"] or row["joy"] or 0),
        "joy":int(row["joy"] or 0),
        "karma":int(row["karma"] or 0),
        "reputation":int(row["character_reputation"] or row["reputation"] or 0),
        "social":int(row["character_reputation"] or 0),
        "finance":0,
        "education":0,
        "career":0,
    }

async def get_lifestyle_stats(character_id:int): return await get_stats(character_id)
async def get_stat(character_id:int,stat_name:str)->int: return (await get_stats(character_id)).get(stat_name,0)

async def modify_stat(character_id:int,stat_name:str,amount:int)->int:
    if stat_name not in STAT_LIMITS: raise ValueError("Statistique inconnue.")
    await ensure_player_stats(character_id)
    async with AsyncSessionLocal() as s:
        row=(await s.execute(text("SELECT joy,karma,reputation FROM mwl_lifestyle_stats WHERE character_id=:id FOR UPDATE"),{"id":int(character_id)})).mappings().first()
        current=int(row[stat_name] or 0) if row and stat_name!="health" else (await s.execute(text("SELECT COALESCE(health,100) FROM life_characters WHERE id=:id FOR UPDATE"),{"id":int(character_id)})).scalar_one()
        new=clamp_stat(stat_name,current+int(amount))
        if stat_name=="health":
            await s.execute(text("UPDATE life_characters SET health=:v,updated_at=NOW() WHERE id=:id"),{"v":new,"id":int(character_id)})
        else:
            await s.execute(text(f"UPDATE mwl_lifestyle_stats SET {stat_name}=:v,updated_at=NOW() WHERE character_id=:id"),{"v":new,"id":int(character_id)})
            if stat_name=="joy":
                await s.execute(text("UPDATE life_characters SET happiness=:v,updated_at=NOW() WHERE id=:id"),{"v":new,"id":int(character_id)})
        await s.commit()
    return new

async def set_stat(character_id:int,stat_name:str,value:int)->int:
    if stat_name not in STAT_LIMITS: raise ValueError("Statistique inconnue.")
    await ensure_player_stats(character_id)
    async with AsyncSessionLocal() as s:
        v=clamp_stat(stat_name,value)
        if stat_name=="health":
            await s.execute(text("UPDATE life_characters SET health=:v,updated_at=NOW() WHERE id=:id"),{"v":v,"id":int(character_id)})
        else:
            await s.execute(text(f"UPDATE mwl_lifestyle_stats SET {stat_name}=:v,updated_at=NOW() WHERE character_id=:id"),{"v":v,"id":int(character_id)})
        await s.commit()
    return v

async def modify_stats(character_id:int,changes:dict[str,int])->dict[str,int]:
    for k,v in changes.items(): await modify_stat(character_id,k,v)
    return await get_stats(character_id)

def validate_stat_name(stat_name:str)->str:
    s=str(stat_name).lower().strip()
    if s not in STAT_LIMITS: raise ValueError("Statistique inconnue.")
    return s

def progress_bar(value:int,minimum:int=0,maximum:int=100,size:int=10)->str:
    ratio=(value-minimum)/max(1,maximum-minimum);filled=max(0,min(size,round(ratio*size)))
    return "█"*filled+"░"*(size-filled)

def format_stat_line(name:str,value:int)->str:
    return f"{STAT_LABELS.get(name,name)} : {value}/{100 if name!='karma' else 100}"

def normalize_username(username:str)->str:return str(username).lstrip("@").strip().lower()
def get_connection(): raise RuntimeError("MANUWORLD V3 utilise PostgreSQL via AsyncSessionLocal; get_connection() n'est plus utilisé.")
