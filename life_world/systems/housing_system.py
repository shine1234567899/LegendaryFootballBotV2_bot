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


def housing_catalog() -> dict:
    return HOUSING_TYPES

def format_housing_catalog() -> str:
    lines = ["🏠 **CATALOGUE DES LOGEMENTS**","━━━━━━━━━━━━━━━━━━━━",""]
    for key,h in HOUSING_TYPES.items():
        rent=f"{h['rent_daily']:,} FCFA/jour".replace(","," ")
        price = "non disponible" if h["purchase_price"] is None else f"{int(h['purchase_price']):,} FCFA".replace(","," ")
        lines += [f"{h['name']}",f"💸 Location : {rent}",f"🏷️ Achat : {price}",""]
    return "\n".join(lines)

def housing_catalog_buttons() -> list[list[tuple[str,str]]]:
    rows=[]
    for key,h in HOUSING_TYPES.items():
        rows.append([(f"lw_housing:details:{key}",h["name"])])
    return rows

def housing_action_buttons(housing_type:str) -> list[list[tuple[str,str]]]:
    h=HOUSING_TYPES.get(housing_type,{})
    rows=[[("lw_housing:roompay:yes" if housing_type=="room" else f"lw_housing:rent:{housing_type}",
           f"💰 Louer ({int(h.get('rent_daily',0)):,} FCFA/jour)".replace(","," "))]]
    if h.get("purchase_price"):
        rows.append([(f"lw_housing:buy:{housing_type}",f"🏷️ Acheter ({int(h['purchase_price']):,} FCFA)".replace(","," "))])
    return rows

def current_housing_buttons() -> list[list[tuple[str,str]]]:
    return [
        [("lw_housing:current","🏠 Mon logement")],
        [("lw_housing:catalog","🏘️ Catalogue")],
    ]

def format_current_housing(housing:dict|None) -> str:
    if not housing:
        return "🏠 **MON LOGEMENT**\n\nTu n'as actuellement aucun logement."
    h=HOUSING_TYPES.get(housing.get("home_type"),{})
    name=h.get("name",housing.get("home_type","Logement"))
    ownership="Propriétaire" if housing.get("ownership")=="owned" else "Locataire"
    return (
        "🏠 **MON LOGEMENT**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{name}\n"
        f"📌 Statut : **{ownership}**\n"
        f"💸 Loyer : **{int(housing.get('rent_daily') or 0):,} FCFA/jour**\n"
        f"📍 {housing.get('city') or 'Ville non définie'}, {housing.get('country') or 'Pays non défini'}"
    ).replace(","," ")

def parse_housing_callback(data:str) -> tuple[str,str|None]:
    parts=str(data or "").split(":")
    return (parts[1],parts[2] if len(parts)>2 else None)
