"""MANUWORLD — Politique [MWL]."""
from datetime import datetime,timezone,timedelta
from sqlalchemy import text
from life_world.database import AsyncSessionLocal,get_life_character
MEETING_COST=2_000

async def ensure_politics_schema():
    async with AsyncSessionLocal() as s:
        await s.execute(text("""
        CREATE TABLE IF NOT EXISTS life_political_parties(
          id BIGSERIAL PRIMARY KEY,name VARCHAR(100) UNIQUE NOT NULL,
          abbreviation VARCHAR(20) NOT NULL,platform TEXT NOT NULL,
          leader_character_id BIGINT REFERENCES life_characters(id) ON DELETE SET NULL,
          treasury BIGINT NOT NULL DEFAULT 0,active BOOLEAN NOT NULL DEFAULT TRUE);
        CREATE TABLE IF NOT EXISTS life_elections(
          id BIGSERIAL PRIMARY KEY,title VARCHAR(150) NOT NULL,office VARCHAR(100) NOT NULL,
          starts_at TIMESTAMPTZ NOT NULL,ends_at TIMESTAMPTZ NOT NULL,
          status VARCHAR(30) NOT NULL DEFAULT 'open',
          winner_character_id BIGINT REFERENCES life_characters(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS life_candidates(
          id BIGSERIAL PRIMARY KEY,election_id BIGINT NOT NULL REFERENCES life_elections(id) ON DELETE CASCADE,
          character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
          party_id BIGINT REFERENCES life_political_parties(id) ON DELETE SET NULL,
          manifesto TEXT,meetings INTEGER NOT NULL DEFAULT 0,votes INTEGER NOT NULL DEFAULT 0,
          UNIQUE(election_id,character_id));
        CREATE TABLE IF NOT EXISTS life_political_votes(
          id BIGSERIAL PRIMARY KEY,election_id BIGINT NOT NULL REFERENCES life_elections(id) ON DELETE CASCADE,
          voter_character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
          candidate_id BIGINT NOT NULL REFERENCES life_candidates(id) ON DELETE CASCADE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),UNIQUE(election_id,voter_character_id));
        CREATE TABLE IF NOT EXISTS life_political_offices(
          id BIGSERIAL PRIMARY KEY,name VARCHAR(100) UNIQUE NOT NULL,
          holder_character_id BIGINT REFERENCES life_characters(id) ON DELETE SET NULL,
          salary BIGINT NOT NULL DEFAULT 0,prestige INTEGER NOT NULL DEFAULT 0,description TEXT NOT NULL);
        """))
        parties=[("Parti de l'Avenir","PA","Développement, éducation et innovation."),
                 ("Mouvement Citoyen","MC","Services publics et proximité."),
                 ("Alliance Nationale","AN","Économie et infrastructures.")]
        for n,a,p in parties:
            await s.execute(text("""INSERT INTO life_political_parties(name,abbreviation,platform)
                                    VALUES(:n,:a,:p) ON CONFLICT(name) DO NOTHING"""),{"n":n,"a":a,"p":p})
        offices=[("Conseiller municipal",75000,10),("Maire",200000,25),("Député",300000,35),
                 ("Gouverneur",500000,50),("Président",1000000,100)]
        for n,sal,pre in offices:
            await s.execute(text("""INSERT INTO life_political_offices(name,salary,prestige,description)
                                    VALUES(:n,:s,:p,:d) ON CONFLICT(name) DO NOTHING"""),
                            {"n":n,"s":sal,"p":pre,"d":f"Poste politique : {n}."})
        await s.commit()

async def ensure_open_election():
    await ensure_politics_schema()
    async with AsyncSessionLocal() as s:
        r=await s.execute(text("SELECT * FROM life_elections WHERE status='open' AND ends_at>NOW() ORDER BY id DESC LIMIT 1"))
        e=r.mappings().first()
        if e:return dict(e)
        now=datetime.now(timezone.utc)
        r=await s.execute(text("""INSERT INTO life_elections(title,office,starts_at,ends_at)
                                  VALUES('Élection — Maire','Maire',:a,:b) RETURNING *"""),
                          {"a":now,"b":now+timedelta(days=7)})
        e=dict(r.mappings().first());await s.commit();return e

async def get_parties():
    await ensure_politics_schema()
    async with AsyncSessionLocal() as s:
        r=await s.execute(text("SELECT * FROM life_political_parties WHERE active=TRUE ORDER BY id"))
        return [dict(x) for x in r.mappings().all()]

async def candidates(eid):
    async with AsyncSessionLocal() as s:
        r=await s.execute(text("""SELECT c.*,ch.username,ch.first_name,p.abbreviation party_abbr
                                  FROM life_candidates c JOIN life_characters ch ON ch.id=c.character_id
                                  LEFT JOIN life_political_parties p ON p.id=c.party_id
                                  WHERE c.election_id=:e ORDER BY c.votes DESC,c.id"""),{"e":eid})
        return [dict(x) for x in r.mappings().all()]

async def run_for(eid,cid):
    await ensure_politics_schema()
    async with AsyncSessionLocal() as s:
        await s.execute(text("""INSERT INTO life_candidates(election_id,character_id,manifesto)
                                VALUES(:e,:c,'Programme personnel MANUWORLD.')
                                ON CONFLICT(election_id,character_id) DO NOTHING"""),{"e":eid,"c":cid})
        await s.commit()

async def meeting(eid,cid):
    async with AsyncSessionLocal() as s:
        r=await s.execute(text("SELECT id FROM life_candidates WHERE election_id=:e AND character_id=:c"),
                          {"e":eid,"c":cid})
        if not r.first(): return {"message":"❌ Tu n'es pas candidat."}
        bal=await s.execute(text("SELECT balance FROM life_characters WHERE id=:c FOR UPDATE"),{"c":cid})
        if int(bal.scalar_one() or 0)<MEETING_COST:return {"message":"❌ Solde insuffisant pour le meeting."}
        await s.execute(text("UPDATE life_characters SET balance=balance-:x,updated_at=NOW() WHERE id=:c"),{"x":MEETING_COST,"c":cid})
        await s.execute(text("UPDATE life_candidates SET meetings=meetings+1 WHERE election_id=:e AND character_id=:c"),{"e":eid,"c":cid})
        await s.commit()
    return {"message":f"📣 Meeting organisé ! -{MEETING_COST:,} FCFA"}

async def cast_vote(eid,vid,candidate_id):
    async with AsyncSessionLocal() as s:
        try:
            await s.execute(text("""INSERT INTO life_political_votes(election_id,voter_character_id,candidate_id)
                                    VALUES(:e,:v,:c)"""),{"e":eid,"v":vid,"c":candidate_id})
            await s.execute(text("UPDATE life_candidates SET votes=votes+1 WHERE id=:c AND election_id=:e"),
                             {"c":candidate_id,"e":eid})
            await s.commit()
            return {"message":"🗳️ Vote enregistré."}
        except Exception:
            await s.rollback();return {"message":"❌ Tu as déjà voté ou le candidat est invalide."}
