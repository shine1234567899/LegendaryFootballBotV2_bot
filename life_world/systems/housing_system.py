"""
MANUWORLD V3 — HOUSING
PostgreSQL-first housing with rent/buy/leave and automatic overdue calculation.
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import text
from life_world.database import AsyncSessionLocal

HOUSING_TYPES={
 "room":{"name":"🛏️ Chambre","rent_daily":2000,"purchase_price":None,"requires_id":False},
 "studio":{"name":"🏢 Studio","rent_daily":5000,"purchase_price":2500000,"requires_id":True},
 "apartment":{"name":"🏠 Appartement","rent_daily":10000,"purchase_price":6000000,"requires_id":True},
 "villa":{"name":"🏡 Villa","rent_daily":25000,"purchase_price":15000000,"requires_id":True},
 "mansion":{"name":"🏰 Manoir","rent_daily":60000,"purchase_price":40000000,"requires_id":True},
}

def normalize_username(username:str)->str:return str(username).lstrip("@").strip().lower()
def get_connection(): raise RuntimeError("MANUWORLD V3 utilise PostgreSQL.")
async def setup_housing_database(): return None

async def _ensure():
    async with AsyncSessionLocal() as s:
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS mwl_housing(
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                home_type VARCHAR(40) NOT NULL,
                ownership VARCHAR(20) NOT NULL DEFAULT 'rent',
                rent_daily BIGINT NOT NULL DEFAULT 0,
                purchase_price BIGINT NOT NULL DEFAULT 0,
                country VARCHAR(80) DEFAULT '',
                city VARCHAR(80) DEFAULT '',
                rented_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_rent_paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(character_id)
            )
        """));await s.commit()

async def get_housing_type(key:str): return HOUSING_TYPES.get(str(key).lower())
async def has_identity_card(character_id:int)->bool:
    async with AsyncSessionLocal() as s:
        return (await s.execute(text("""
            SELECT 1 FROM life_documents WHERE character_id=:id AND document_type ILIKE '%ident%' AND status='valid' LIMIT 1
        """),{"id":int(character_id)})).first() is not None

async def get_current_housing(character_id:int):
    await _ensure()
    async with AsyncSessionLocal() as s:
        r=(await s.execute(text("SELECT * FROM mwl_housing WHERE character_id=:id"),{"id":int(character_id)})).mappings().first()
    return dict(r) if r else None

async def can_get_housing(character_id:int,home_type:str,ownership:str="rent")->tuple[bool,str]:
    h=HOUSING_TYPES.get(home_type)
    if not h:return False,"❌ Type de logement invalide."
    if await get_current_housing(character_id):return False,"❌ Tu as déjà un logement."
    if ownership=="buy" and h["requires_id"] and not await has_identity_card(character_id):
        return False,"❌ Une carte d'identité valide est nécessaire pour acheter ce logement."
    return True,""

async def rent_housing(character_id:int,home_type:str,country:str="",city:str=""):
    await _ensure(); ok,msg=await can_get_housing(character_id,home_type,"rent")
    if not ok:return {"success":False,"message":msg}
    h=HOUSING_TYPES[home_type]
    async with AsyncSessionLocal() as s:
        bal=int((await s.execute(text("SELECT balance FROM life_characters WHERE id=:id FOR UPDATE"),{"id":int(character_id)})).scalar() or 0)
        if bal<h["rent_daily"]: return {"success":False,"message":"❌ Solde insuffisant pour le premier loyer."}
        await s.execute(text("UPDATE life_characters SET balance=balance-:amount,updated_at=NOW() WHERE id=:id"),{"amount":h["rent_daily"],"id":int(character_id)})
        await s.execute(text("INSERT INTO mwl_housing(character_id,home_type,ownership,rent_daily,country,city) VALUES(:id,:type,'rent',:rent,:country,:city)"),{"id":int(character_id),"type":home_type,"rent":h["rent_daily"],"country":country,"city":city})
        await s.commit()
    return {"success":True,"message":f"🏠 Logement loué : {h['name']}\n💸 Premier loyer : {h['rent_daily']:,} FCFA".replace(","," ")}

async def buy_housing(character_id:int,home_type:str,country:str="",city:str=""):
    await _ensure(); ok,msg=await can_get_housing(character_id,home_type,"buy")
    if not ok:return {"success":False,"message":msg}
    h=HOUSING_TYPES[home_type]; price=h["purchase_price"]
    if price is None:return {"success":False,"message":"❌ Ce logement ne peut pas être acheté."}
    async with AsyncSessionLocal() as s:
        bal=int((await s.execute(text("SELECT balance FROM life_characters WHERE id=:id FOR UPDATE"),{"id":int(character_id)})).scalar() or 0)
        if bal<price:return {"success":False,"message":"❌ Solde insuffisant."}
        await s.execute(text("UPDATE life_characters SET balance=balance-:price,updated_at=NOW() WHERE id=:id"),{"price":price,"id":int(character_id)})
        await s.execute(text("INSERT INTO mwl_housing(character_id,home_type,ownership,rent_daily,purchase_price,country,city) VALUES(:id,:type,'owned',0,:price,:country,:city)"),{"id":int(character_id),"type":home_type,"price":price,"country":country,"city":city})
        await s.commit()
    return {"success":True,"message":f"🏡 Achat effectué : {h['name']}\n💰 Prix : {price:,} FCFA".replace(","," ")}

async def get_rent_due(character_id:int)->int:
    h=await get_current_housing(character_id)
    if not h or h["ownership"]!="rent":return 0
    last=h["last_rent_paid_at"];now=datetime.now(timezone.utc)
    if last.tzinfo is None:last=last.replace(tzinfo=timezone.utc)
    days=max(0,(now-last).days)
    return days*int(h["rent_daily"] or 0)

async def calculate_days_since_payment(character_id:int)->int:
    h=await get_current_housing(character_id)
    if not h:return 0
    last=h["last_rent_paid_at"];now=datetime.now(timezone.utc)
    if last.tzinfo is None:last=last.replace(tzinfo=timezone.utc)
    return max(0,(now-last).days)

async def calculate_rent_charge(character_id:int)->int:return await get_rent_due(character_id)
