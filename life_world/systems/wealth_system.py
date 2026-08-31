"""
MANUWORLD V3 — WEALTH
Patrimoine calculé exclusivement depuis PostgreSQL.
"""
from __future__ import annotations
from sqlalchemy import text
from life_world.database import AsyncSessionLocal
ITEM_VALUES={"basic_phone":25000,"smartphone":100000,"premium_phone":300000,"luxury_phone":1000000,"watch":50000,"laptop":400000,"headphones":75000,"camera":250000,"gold_watch":500000}

def normalize_username(username:str)->str:return str(username).lstrip("@").strip().lower()
def get_connection(): raise RuntimeError("MANUWORLD V3 utilise PostgreSQL.")

async def get_cash_balance(character_id:int)->int:
    async with AsyncSessionLocal() as s:
        return int((await s.execute(text("SELECT COALESCE(balance,0) FROM life_characters WHERE id=:id"),{"id":int(character_id)})).scalar() or 0)

async def get_property_value(character_id:int)->int:
    async with AsyncSessionLocal() as s:
        return int((await s.execute(text("SELECT COALESCE(SUM(value),0) FROM life_homes WHERE owner_character_id=:id"),{"id":int(character_id)})).scalar() or 0)

async def get_inventory_value(character_id:int)->int:
    async with AsyncSessionLocal() as s:
        rows=(await s.execute(text("SELECT item_name,quantity,item_data FROM life_inventory WHERE character_id=:id"),{"id":int(character_id)})).mappings().all()
    total=0
    for r in rows:
        data=r["item_data"] or {}
        total += int(r["quantity"] or 0)*int(data.get("value",ITEM_VALUES.get(str(r["item_name"]),0)) or 0)
    return total

async def get_credit_exposure(character_id:int)->int:
    async with AsyncSessionLocal() as s:
        try:
            return int((await s.execute(text("SELECT COALESCE(SUM(principal_remaining+interest_remaining),0) FROM life_loans WHERE character_id=:id AND status IN ('active','overdue')"),{"id":int(character_id)})).scalar() or 0)
        except Exception:
            await s.rollback(); return 0

async def calculate_wealth(character_id:int)->dict:
    cash=await get_cash_balance(character_id); props=await get_property_value(character_id); inv=await get_inventory_value(character_id); debt=await get_credit_exposure(character_id)
    return {"cash":cash,"properties":props,"inventory":inv,"debt":debt,"total":max(0,cash+props+inv-debt)}

def wealth_level(total:int)->str:
    return "Débutant" if total<100000 else "Confortable" if total<1000000 else "Riche" if total<10000000 else "Très riche" if total<100000000 else "Magnat"

async def format_wealth(character_id:int)->str:
    w=await calculate_wealth(character_id)
    return f"💰 **PATRIMOINE**\n\n💵 Liquidités : {w['cash']:,} FCFA\n🏠 Immobilier : {w['properties']:,} FCFA\n🎒 Inventaire : {w['inventory']:,} FCFA\n📉 Dettes : {w['debt']:,} FCFA\n\n👑 **Total : {w['total']:,} FCFA**\n🏷️ Niveau : **{wealth_level(w['total'])}**".replace(","," ")

async def compare_wealth(a:int,b:int)->dict:
    wa,wb=await calculate_wealth(a),await calculate_wealth(b);return {"first":wa,"second":wb,"difference":wa["total"]-wb["total"]}

def format_wealth_comparison(data:dict)->str:
    return f"💰 {data['first']['total']:,} FCFA vs {data['second']['total']:,} FCFA\n📊 Écart : {data['difference']:,} FCFA".replace(","," ")
