"""MANUWORLD — Hôpital [MWL]. Diagnostic et soins fictifs de gameplay."""
from __future__ import annotations
from sqlalchemy import text
from life_world.database import AsyncSessionLocal, get_life_character

CONSULTATION_FEE = 5_000

async def ensure_hospital_schema():
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS life_hospital_visits (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                diagnosis VARCHAR(120) NOT NULL,
                severity VARCHAR(30) NOT NULL,
                consultation_fee BIGINT NOT NULL DEFAULT 5000,
                treatment_fee BIGINT NOT NULL DEFAULT 0,
                operation_fee BIGINT NOT NULL DEFAULT 0,
                consultation_paid BOOLEAN NOT NULL DEFAULT FALSE,
                treatment_paid BOOLEAN NOT NULL DEFAULT FALSE,
                operation_paid BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await session.commit()

def diagnose(health: int) -> dict:
    h=max(0,min(100,int(health)))
    if h <= 20:
        return {"diagnosis":"État nécessitant une opération","severity":"critique",
                "advice":"Une intervention est nécessaire.","treatment_fee":150_000,"operation_fee":500_000}
    if h <= 40:
        return {"diagnosis":"Blessure","severity":"grave",
                "advice":"Des soins médicaux sont nécessaires.","treatment_fee":40_000,"operation_fee":0}
    if h <= 65:
        return {"diagnosis":"Petite infection","severity":"modérée",
                "advice":"Un traitement médical est recommandé.","treatment_fee":25_000,"operation_fee":0}
    return {"diagnosis":"Fatigue passagère","severity":"légère",
            "advice":"Repos et récupération recommandés.","treatment_fee":15_000,"operation_fee":0}

async def create_visit(character_id:int):
    await ensure_hospital_schema()
    c=await get_life_character(character_id)
    if not c: return {"success":False,"message":"❌ Personnage introuvable."}
    d=diagnose(int(c.get("health") or 100))
    async with AsyncSessionLocal() as s:
        r=await s.execute(text("""
            INSERT INTO life_hospital_visits
            (character_id,diagnosis,severity,consultation_fee,treatment_fee,operation_fee)
            VALUES (:cid,:diagnosis,:severity,:consult,:treatment,:operation)
            RETURNING id
        """),{"cid":character_id,"diagnosis":d["diagnosis"],"severity":d["severity"],
              "consult":CONSULTATION_FEE,"treatment":d["treatment_fee"],"operation":d["operation_fee"]})
        visit_id=int(r.scalar_one()); await s.commit()
    return {"success":True,"id":visit_id,"consultation_fee":CONSULTATION_FEE,**d}

async def pay_part(character_id:int,visit_id:int,part:str):
    if part not in ("consultation","treatment","operation"):
        return {"success":False,"message":"❌ Paiement invalide."}
    await ensure_hospital_schema()
    async with AsyncSessionLocal() as s:
        r=await s.execute(text("""
            SELECT * FROM life_hospital_visits
            WHERE id=:vid AND character_id=:cid FOR UPDATE
        """),{"vid":visit_id,"cid":character_id})
        v=r.mappings().first()
        if not v: return {"success":False,"message":"❌ Visite introuvable."}
        if v[f"{part}_paid"]: return {"success":False,"message":"✅ Déjà payé."}
        fee=int(v[f"{part}_fee"] or 0)
        bal=(await s.execute(text("SELECT balance FROM life_characters WHERE id=:id FOR UPDATE"),
                             {"id":character_id})).scalar_one()
        if int(bal or 0)<fee:
            await s.rollback()
            return {"success":False,"message":f"❌ Solde insuffisant. À payer : {fee:,} FCFA."}
        await s.execute(text("""
            UPDATE life_characters SET balance=balance-:fee, updated_at=NOW()
            WHERE id=:id
        """),{"fee":fee,"id":character_id})
        await s.execute(text(f"""
            UPDATE life_hospital_visits SET {part}_paid=TRUE WHERE id=:vid
        """),{"vid":visit_id})
        heal=0 if part=="consultation" else (25 if part=="treatment" else 60)
        if heal:
            await s.execute(text("""
                UPDATE life_characters SET health=LEAST(100,health+:heal),updated_at=NOW()
                WHERE id=:id
            """),{"heal":heal,"id":character_id})
        await s.commit()
    return {"success":True,"message":f"✅ Paiement effectué : {fee:,} FCFA.","heal":heal}

async def get_visit(character_id:int,visit_id:int):
    await ensure_hospital_schema()
    async with AsyncSessionLocal() as s:
        r=await s.execute(text("SELECT * FROM life_hospital_visits WHERE id=:vid AND character_id=:cid"),
                           {"vid":visit_id,"cid":character_id})
        v=r.mappings().first(); return dict(v) if v else None
