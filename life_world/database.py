from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


LIFE_TABLE = "life_characters"



async def ensure_life_tables() -> None:
    """
    Create the complete MANUWORLD schema in the bot's existing database.

    Nothing is dropped. Existing tables/characters are preserved and the
    new tables are added alongside them.
    """
    async with AsyncSessionLocal() as session:
        statements = [
            # ------------------------------------------------------
            # CHARACTER / CORE LIFE
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_characters (
                id BIGSERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL UNIQUE,
                username VARCHAR(80),
                first_name VARCHAR(80) NOT NULL,
                last_name VARCHAR(80),
                nationality VARCHAR(80) NOT NULL,
                gender VARCHAR(20) NOT NULL,
                residence_country VARCHAR(80) NOT NULL,
                residence_city VARCHAR(80),
                birth_date DATE NOT NULL,
                life_id VARCHAR(32) NOT NULL UNIQUE,

                age INTEGER NOT NULL DEFAULT 9,
                experience BIGINT NOT NULL DEFAULT 0,
                experience_required BIGINT NOT NULL DEFAULT 100,
                life_level INTEGER NOT NULL DEFAULT 1,

                balance BIGINT NOT NULL DEFAULT 0,
                balance_bank BIGINT NOT NULL DEFAULT 0,

                family_name VARCHAR(80),
                family_id BIGINT,

                education_level VARCHAR(80) NOT NULL
                    DEFAULT 'École primaire',
                diploma_level VARCHAR(80),

                identity_card BOOLEAN NOT NULL DEFAULT FALSE,

                health INTEGER NOT NULL DEFAULT 100,
                energy INTEGER NOT NULL DEFAULT 100,
                happiness INTEGER NOT NULL DEFAULT 100,
                reputation INTEGER NOT NULL DEFAULT 0,

                job_id BIGINT,
                workplace VARCHAR(120),
                job_salary BIGINT NOT NULL DEFAULT 0,

                home_id BIGINT,
                relationship_status VARCHAR(30)
                    NOT NULL DEFAULT 'single',

                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # EDUCATION
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_education (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                school_name VARCHAR(120),
                level VARCHAR(80) NOT NULL,
                class_name VARCHAR(80),
                year INTEGER,
                average NUMERIC(5,2),
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ended_at TIMESTAMPTZ
            )
            """,

            # ------------------------------------------------------
            # JOBS / CAREERS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_jobs (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                minimum_age INTEGER NOT NULL DEFAULT 18,
                minimum_education VARCHAR(80),
                salary_min BIGINT NOT NULL DEFAULT 0,
                salary_max BIGINT NOT NULL DEFAULT 0,
                experience_reward INTEGER NOT NULL DEFAULT 0,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_employments (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                job_id BIGINT NOT NULL
                    REFERENCES life_jobs(id),
                company_name VARCHAR(120),
                salary BIGINT NOT NULL DEFAULT 0,
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                hired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                left_at TIMESTAMPTZ
            )
            """,

            # ------------------------------------------------------
            # FAMILY / RELATIONSHIPS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_families (
                id BIGSERIAL PRIMARY KEY,
                family_name VARCHAR(120) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_relationships (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                target_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                relationship_type VARCHAR(40) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ended_at TIMESTAMPTZ,
                UNIQUE(character_id, target_character_id, relationship_type)
            )
            """,

            # ------------------------------------------------------
            # HOUSING
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_homes (
                id BIGSERIAL PRIMARY KEY,
                owner_character_id BIGINT
                    REFERENCES life_characters(id) ON DELETE SET NULL,
                country VARCHAR(80),
                city VARCHAR(80),
                address VARCHAR(160),
                home_type VARCHAR(60) NOT NULL,
                value BIGINT NOT NULL DEFAULT 0,
                rent BIGINT NOT NULL DEFAULT 0,
                condition INTEGER NOT NULL DEFAULT 100,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # SKILLS / INVENTORY
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_skills (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                skill_name VARCHAR(80) NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                experience BIGINT NOT NULL DEFAULT 0,
                UNIQUE(character_id, skill_name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_inventory (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                item_name VARCHAR(120) NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                item_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                UNIQUE(character_id, item_name)
            )
            """,

            # ------------------------------------------------------
            # BANK / TRANSACTIONS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_transactions (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                transaction_type VARCHAR(40) NOT NULL,
                amount BIGINT NOT NULL,
                balance_after BIGINT NOT NULL,
                description TEXT,
                reference VARCHAR(120),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # EVENTS / LIFE HISTORY
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_events (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                title VARCHAR(160) NOT NULL,
                description TEXT,
                experience_reward INTEGER NOT NULL DEFAULT 0,
                money_change BIGINT NOT NULL DEFAULT 0,
                event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # PURCHASES / EXPENSES
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_expenses (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                category VARCHAR(50) NOT NULL,
                description VARCHAR(160) NOT NULL,
                amount BIGINT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # DOCUMENTS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_documents (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                document_type VARCHAR(60) NOT NULL,
                document_number VARCHAR(80) NOT NULL UNIQUE,
                status VARCHAR(30) NOT NULL DEFAULT 'valid',
                issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ
            )
            """,

            # ------------------------------------------------------
            # FRIEND REQUESTS / MARRIAGE / ADOPTION
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_friend_requests (
                id BIGSERIAL PRIMARY KEY,
                sender_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                receiver_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                responded_at TIMESTAMPTZ,
                UNIQUE(sender_character_id, receiver_character_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_marriage_requests (
                id BIGSERIAL PRIMARY KEY,
                sender_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                receiver_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                responded_at TIMESTAMPTZ,
                UNIQUE(sender_character_id, receiver_character_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_adoption_requests (
                id BIGSERIAL PRIMARY KEY,
                sender_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                receiver_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                responded_at TIMESTAMPTZ,
                UNIQUE(sender_character_id, receiver_character_id)
            )
            """,

            # ------------------------------------------------------
            # COMPANIES / GRADES / MEMBERS / SHARES
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_company_grades (
                id BIGSERIAL PRIMARY KEY,
                grade INTEGER NOT NULL UNIQUE,
                name VARCHAR(60) NOT NULL,
                employee_slots INTEGER NOT NULL,
                minimum_reputation INTEGER NOT NULL DEFAULT 0,
                minimum_credibility INTEGER NOT NULL DEFAULT 0,
                minimum_revenue BIGINT NOT NULL DEFAULT 0,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_companies (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL UNIQUE,
                owner_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id),
                grade_id BIGINT REFERENCES life_company_grades(id),
                capital BIGINT NOT NULL DEFAULT 0,
                treasury BIGINT NOT NULL DEFAULT 0,
                reputation INTEGER NOT NULL DEFAULT 0,
                credibility INTEGER NOT NULL DEFAULT 0,
                health INTEGER NOT NULL DEFAULT 100,
                total_revenue BIGINT NOT NULL DEFAULT 0,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_company_members (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                character_id BIGINT
                    REFERENCES life_characters(id) ON DELETE SET NULL,
                virtual_name VARCHAR(100),
                position VARCHAR(80) NOT NULL,
                knowledge INTEGER NOT NULL DEFAULT 1,
                performance INTEGER NOT NULL DEFAULT 50,
                salary BIGINT NOT NULL DEFAULT 0,
                is_virtual BOOLEAN NOT NULL DEFAULT FALSE,
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                hired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                left_at TIMESTAMPTZ
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_company_shareholders (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                shares NUMERIC(12,4) NOT NULL DEFAULT 0,
                invested_amount BIGINT NOT NULL DEFAULT 0,
                UNIQUE(company_id, character_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_company_positions (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                position_name VARCHAR(80) NOT NULL,
                max_slots INTEGER NOT NULL DEFAULT 1,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE(company_id, position_name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_company_transactions (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                character_id BIGINT
                    REFERENCES life_characters(id) ON DELETE SET NULL,
                transaction_type VARCHAR(40) NOT NULL,
                amount BIGINT NOT NULL,
                balance_after BIGINT NOT NULL,
                description TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # COMPANY JOB ADS / APPLICATIONS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_company_job_ads (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                position VARCHAR(80) NOT NULL,
                salary BIGINT NOT NULL DEFAULT 0,
                minimum_knowledge INTEGER NOT NULL DEFAULT 0,
                slots INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(20) NOT NULL DEFAULT 'open',
                created_by_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                closed_at TIMESTAMPTZ
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_company_job_applications (
                id BIGSERIAL PRIMARY KEY,
                job_ad_id BIGINT NOT NULL
                    REFERENCES life_company_job_ads(id) ON DELETE CASCADE,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                responded_at TIMESTAMPTZ,
                UNIQUE(job_ad_id, character_id)
            )
            """,

            # ------------------------------------------------------
            # COMPANY CONTRACTS / TASKS / COMMISSIONS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_company_contracts (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                title VARCHAR(160) NOT NULL,
                client_name VARCHAR(120) NOT NULL,
                difficulty VARCHAR(30) NOT NULL,
                reward BIGINT NOT NULL DEFAULT 0,
                total_orders INTEGER NOT NULL DEFAULT 0,
                virtual_orders INTEGER NOT NULL DEFAULT 0,
                real_orders INTEGER NOT NULL DEFAULT 0,
                completed_orders INTEGER NOT NULL DEFAULT 0,
                preparation_score INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(30) NOT NULL DEFAULT 'offered',
                reminder_count INTEGER NOT NULL DEFAULT 0,
                accepted_at TIMESTAMPTZ,
                deadline_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_company_tasks (
                id BIGSERIAL PRIMARY KEY,
                contract_id BIGINT NOT NULL
                    REFERENCES life_company_contracts(id) ON DELETE CASCADE,
                assigned_member_id BIGINT
                    REFERENCES life_company_members(id) ON DELETE SET NULL,
                task_type VARCHAR(60) NOT NULL,
                title VARCHAR(160) NOT NULL,
                difficulty VARCHAR(30) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                result_score INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_company_commissions (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                contract_id BIGINT
                    REFERENCES life_company_contracts(id) ON DELETE SET NULL,
                member_id BIGINT
                    REFERENCES life_company_members(id) ON DELETE SET NULL,
                character_id BIGINT
                    REFERENCES life_characters(id) ON DELETE SET NULL,
                amount BIGINT NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                paid_at TIMESTAMPTZ
            )
            """,

            # ------------------------------------------------------
            # BANKS / ACCOUNTS / INTEREST
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_banks (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL UNIQUE,
                bank_type VARCHAR(40) NOT NULL DEFAULT 'bank',
                interest_rate NUMERIC(7,4) NOT NULL DEFAULT 0,
                account_fee BIGINT NOT NULL DEFAULT 0,
                transfer_fee BIGINT NOT NULL DEFAULT 0,
                minimum_balance BIGINT NOT NULL DEFAULT 0,
                maximum_balance BIGINT,
                prestige INTEGER NOT NULL DEFAULT 1,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_bank_accounts (
                id BIGSERIAL PRIMARY KEY,
                bank_id BIGINT NOT NULL
                    REFERENCES life_banks(id),
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                account_number VARCHAR(40) NOT NULL UNIQUE,
                balance BIGINT NOT NULL DEFAULT 0,
                interest_accrued BIGINT NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_interest_at TIMESTAMPTZ
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_bank_transactions (
                id BIGSERIAL PRIMARY KEY,
                account_id BIGINT NOT NULL
                    REFERENCES life_bank_accounts(id) ON DELETE CASCADE,
                transaction_type VARCHAR(40) NOT NULL,
                amount BIGINT NOT NULL,
                balance_after BIGINT NOT NULL,
                description TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # ------------------------------------------------------
            # CREDIT CARDS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_credit_cards (
                id BIGSERIAL PRIMARY KEY,
                bank_id BIGINT NOT NULL
                    REFERENCES life_banks(id) ON DELETE CASCADE,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                card_name VARCHAR(100) NOT NULL,
                card_number VARCHAR(32) NOT NULL UNIQUE,
                card_type VARCHAR(40) NOT NULL DEFAULT 'standard',
                credit_limit BIGINT NOT NULL DEFAULT 0,
                used_credit BIGINT NOT NULL DEFAULT 0,
                available_credit BIGINT NOT NULL DEFAULT 0,
                interest_rate NUMERIC(7,4) NOT NULL DEFAULT 0,
                annual_fee BIGINT NOT NULL DEFAULT 0,
                reward_rate NUMERIC(7,4) NOT NULL DEFAULT 0,
                credit_score INTEGER NOT NULL DEFAULT 500,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                payment_due_at TIMESTAMPTZ,
                last_payment_at TIMESTAMPTZ
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_credit_card_transactions (
                id BIGSERIAL PRIMARY KEY,
                card_id BIGINT NOT NULL
                    REFERENCES life_credit_cards(id) ON DELETE CASCADE,
                transaction_type VARCHAR(40) NOT NULL,
                amount BIGINT NOT NULL,
                balance_after BIGINT NOT NULL,
                merchant VARCHAR(120),
                description TEXT,
                reward_earned BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_credit_card_payments (
                id BIGSERIAL PRIMARY KEY,
                card_id BIGINT NOT NULL
                    REFERENCES life_credit_cards(id) ON DELETE CASCADE,
                amount BIGINT NOT NULL,
                previous_balance BIGINT NOT NULL,
                remaining_balance BIGINT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # HOUSING PAYMENTS / PROPERTIES
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_properties (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT
                    REFERENCES life_characters(id) ON DELETE SET NULL,
                home_type VARCHAR(60) NOT NULL,
                country VARCHAR(80),
                city VARCHAR(80),
                address VARCHAR(160),
                purchase_price BIGINT NOT NULL DEFAULT 0,
                condition INTEGER NOT NULL DEFAULT 100,
                identity_required BOOLEAN NOT NULL DEFAULT TRUE,
                purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_rent_payments (
                id BIGSERIAL PRIMARY KEY,
                home_id BIGINT NOT NULL
                    REFERENCES life_homes(id) ON DELETE CASCADE,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                amount BIGINT NOT NULL,
                due_date DATE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'paid',
                paid_at TIMESTAMPTZ
            )
            """,

            # ------------------------------------------------------
            # ITEMS / BRANDS / INVENTORY / GIFTS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_item_brands (
                id BIGSERIAL PRIMARY KEY,
                category VARCHAR(60) NOT NULL,
                name VARCHAR(100) NOT NULL,
                prestige INTEGER NOT NULL DEFAULT 1,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE(category, name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_items (
                id BIGSERIAL PRIMARY KEY,
                brand_id BIGINT REFERENCES life_item_brands(id),
                category VARCHAR(60) NOT NULL,
                name VARCHAR(120) NOT NULL,
                price BIGINT NOT NULL DEFAULT 0,
                rarity VARCHAR(30) NOT NULL DEFAULT 'common',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE(category, name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_gifts (
                id BIGSERIAL PRIMARY KEY,
                sender_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                receiver_character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                item_id BIGINT NOT NULL
                    REFERENCES life_items(id),
                price_paid BIGINT NOT NULL DEFAULT 0,
                karma_gain INTEGER NOT NULL DEFAULT 0,
                happiness_gain INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'completed',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # SCHOOL HISTORY / DIPLOMAS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_diplomas (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                diploma_type VARCHAR(80) NOT NULL,
                school_level VARCHAR(80) NOT NULL,
                obtained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(character_id, diploma_type)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_school_years (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL
                    REFERENCES life_characters(id) ON DELETE CASCADE,
                class_name VARCHAR(80) NOT NULL,
                academic_year INTEGER NOT NULL,
                average NUMERIC(5,2),
                result VARCHAR(30) NOT NULL DEFAULT 'in_progress',
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ended_at TIMESTAMPTZ
            )
            """,

            # ------------------------------------------------------
            # GLOBAL GAME SETTINGS / GROUPS / JOB ANNOUNCEMENTS
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_game_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_bot_groups (
                group_id BIGINT PRIMARY KEY,
                title VARCHAR(160),
                can_post BOOLEAN NOT NULL DEFAULT TRUE,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_checked_at TIMESTAMPTZ
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS life_job_announcements (
                id BIGSERIAL PRIMARY KEY,
                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id) ON DELETE CASCADE,
                job_ad_id BIGINT NOT NULL
                    REFERENCES life_company_job_ads(id) ON DELETE CASCADE,
                message_id BIGINT,
                group_id BIGINT
                    REFERENCES life_bot_groups(group_id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'published',
                published_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,

            # ------------------------------------------------------
            # INDEXES
            # ------------------------------------------------------
            """
            CREATE INDEX IF NOT EXISTS idx_life_characters_username
            ON life_characters (LOWER(username))
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_life_events_character
            ON life_events (character_id, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_life_transactions_character
            ON life_transactions (character_id, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_life_employment_active
            ON life_employments (character_id, status)
            """,
                        # ------------------------------------------------------
            # COMPANY MARKET / SALES
            # ------------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS life_company_market (
                id BIGSERIAL PRIMARY KEY,

                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id)
                    ON DELETE CASCADE,

                product_name VARCHAR(160) NOT NULL,

                category VARCHAR(40) NOT NULL
                    DEFAULT 'other',

                price BIGINT NOT NULL
                    DEFAULT 0,

                stock INTEGER NOT NULL
                    DEFAULT 0,

                description TEXT,

                active BOOLEAN NOT NULL
                    DEFAULT TRUE,

                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT NOW(),

                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT NOW(),

                CONSTRAINT life_company_market_price_positive
                    CHECK (price > 0),

                CONSTRAINT life_company_market_stock_positive
                    CHECK (stock >= 0)
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS life_company_market_sales (
                id BIGSERIAL PRIMARY KEY,

                offer_id BIGINT
                    REFERENCES life_company_market(id)
                    ON DELETE SET NULL,

                company_id BIGINT NOT NULL
                    REFERENCES life_companies(id)
                    ON DELETE CASCADE,

                buyer_character_id BIGINT
                    REFERENCES life_characters(id)
                    ON DELETE SET NULL,

                quantity INTEGER NOT NULL
                    DEFAULT 1,

                unit_price BIGINT NOT NULL
                    DEFAULT 0,

                total_price BIGINT NOT NULL
                    DEFAULT 0,

                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT NOW(),

                CONSTRAINT life_company_market_sales_quantity_positive
                    CHECK (quantity > 0),

                CONSTRAINT life_company_market_sales_price_positive
                    CHECK (unit_price >= 0),

                CONSTRAINT life_company_market_sales_total_positive
                    CHECK (total_price >= 0)
            )
            """,

            # ------------------------------------------------------
            # INDEXES — COMPANY MARKET
            # ------------------------------------------------------
            """
            CREATE INDEX IF NOT EXISTS
            idx_life_company_market_active
            ON life_company_market (
                active,
                category
            )
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_life_company_market_company
            ON life_company_market (
                company_id,
                active
            )
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_life_company_market_sales_company
            ON life_company_market_sales (
                company_id,
                created_at
            )
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_life_company_market_sales_buyer
            ON life_company_market_sales (
                buyer_character_id,
                created_at
            )
            """,
        ]

        # ----------------------------------------------------------
        # SAFE MIGRATION OF AN EXISTING life_characters TABLE
        #
        # IMPORTANT:
        # Northflank/PostgreSQL may already contain an older
        # life_characters table. CREATE TABLE IF NOT EXISTS does NOT
        # update that existing table, so the required columns must be
        # added BEFORE creating indexes such as LOWER(username).
        # ----------------------------------------------------------
        result = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'life_characters'
                """
            )
        )
        existing = {row[0] for row in result.fetchall()}

        migrations = {
            "username": "ALTER TABLE life_characters ADD COLUMN username VARCHAR(80)",
            "last_name": "ALTER TABLE life_characters ADD COLUMN last_name VARCHAR(80)",
            "residence_city": "ALTER TABLE life_characters ADD COLUMN residence_city VARCHAR(80)",
            "age": "ALTER TABLE life_characters ADD COLUMN age INTEGER NOT NULL DEFAULT 9",
            "experience": "ALTER TABLE life_characters ADD COLUMN experience BIGINT NOT NULL DEFAULT 0",
            "experience_required": "ALTER TABLE life_characters ADD COLUMN experience_required BIGINT NOT NULL DEFAULT 100",
            "life_level": "ALTER TABLE life_characters ADD COLUMN life_level INTEGER NOT NULL DEFAULT 1",
            "balance_bank": "ALTER TABLE life_characters ADD COLUMN balance_bank BIGINT NOT NULL DEFAULT 0",
            "health": "ALTER TABLE life_characters ADD COLUMN health INTEGER NOT NULL DEFAULT 100",
            "energy": "ALTER TABLE life_characters ADD COLUMN energy INTEGER NOT NULL DEFAULT 100",
            "happiness": "ALTER TABLE life_characters ADD COLUMN happiness INTEGER NOT NULL DEFAULT 100",
            "reputation": "ALTER TABLE life_characters ADD COLUMN reputation INTEGER NOT NULL DEFAULT 0",
            "job_id": "ALTER TABLE life_characters ADD COLUMN job_id BIGINT",
            "workplace": "ALTER TABLE life_characters ADD COLUMN workplace VARCHAR(120)",
            "job_salary": "ALTER TABLE life_characters ADD COLUMN job_salary BIGINT NOT NULL DEFAULT 0",
            "home_id": "ALTER TABLE life_characters ADD COLUMN home_id BIGINT",
            "relationship_status": "ALTER TABLE life_characters ADD COLUMN relationship_status VARCHAR(30) NOT NULL DEFAULT 'single'",
            "created_at": "ALTER TABLE life_characters ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            "updated_at": "ALTER TABLE life_characters ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        }

        for column, statement in migrations.items():
            if column not in existing:
                await session.execute(text(statement))

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET experience_required = 100
                WHERE experience_required IS NULL
                """
            )
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET updated_at = NOW()
                WHERE updated_at IS NULL
                """
            )
        )

        # Make the new username column usable by the rest of MANUWORLD.
        # Existing records are preserved; NULL usernames remain NULL until
        # the Telegram user has a username.
        await session.flush()

        for statement in statements:
            await session.execute(text(statement))

        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_friend_receiver
            ON life_friend_requests (receiver_character_id, status)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_company_members_active
            ON life_company_members (company_id, status)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_company_contracts_active
            ON life_company_contracts (company_id, status)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_bank_accounts_character
            ON life_bank_accounts (character_id, status)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_inventory_character
            ON life_inventory (character_id)
        """))

        # ----------------------------------------------------------
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_credit_cards_character
            ON life_credit_cards (character_id, status)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_credit_card_transactions
            ON life_credit_card_transactions (card_id, created_at DESC)
        """))


        await session.commit()



async def get_life_character(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_characters
                WHERE telegram_id = :telegram_id
                LIMIT 1
                """
            ),
            {"telegram_id": telegram_id},
        )
        return result.mappings().first()


async def get_life_character_by_username(username: str):
    username = username.lstrip("@").strip()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_characters
                WHERE LOWER(username) = LOWER(:username)
                LIMIT 1
                """
            ),
            {"username": username},
        )
        return result.mappings().first()


async def create_life_character(**data: Any) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO life_characters (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    nationality,
                    gender,
                    residence_country,
                    residence_city,
                    birth_date,
                    life_id,
                    age,
                    experience,
                    experience_required,
                    life_level
                )
                VALUES (
                    :telegram_id,
                    :username,
                    :first_name,
                    :last_name,
                    :nationality,
                    :gender,
                    :residence_country,
                    :residence_city,
                    :birth_date,
                    :life_id,
                    9,
                    0,
                    100,
                    1
                )
                """
            ),
            data,
        )
        await session.commit()


def xp_required_for_next_age(age: int) -> int:
    """Game XP controls age; real calendar time does not."""
    age = max(9, int(age))
    return 100 + ((age - 9) * 25)


async def add_life_experience(
    telegram_id: int,
    amount: int,
) -> dict[str, int] | None:
    amount = max(0, int(amount))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT age, experience, life_level
                FROM life_characters
                WHERE telegram_id = :telegram_id
                FOR UPDATE
                """
            ),
            {"telegram_id": telegram_id},
        )
        row = result.mappings().first()

        if row is None:
            return None

        age = int(row["age"] or 9)
        experience = int(row["experience"] or 0)
        level = int(row["life_level"] or 1)

        experience += amount

        while experience >= xp_required_for_next_age(age):
            experience -= xp_required_for_next_age(age)
            age += 1
            level += 1

        required = xp_required_for_next_age(age)

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET age = :age,
                    experience = :experience,
                    experience_required = :required,
                    life_level = :level,
                    updated_at = NOW()
                WHERE telegram_id = :telegram_id
                """
            ),
            {
                "telegram_id": telegram_id,
                "age": age,
                "experience": experience,
                "required": required,
                "level": level,
            },
        )
        await session.commit()

        return {
            "age": age,
            "experience": experience,
            "experience_required": required,
            "life_level": level,
        }


# ==============================================================
# MANUWORLD — SAFE SCHEMA MIGRATIONS / EDUCATION HELPERS
# ==============================================================

async def ensure_life_world_migrations() -> None:
    """
    Safely upgrades an existing MANUWORLD database.

    Existing data is preserved. Missing columns are added only when
    necessary. This function is intentionally separate from
    ensure_life_tables() so main.py can run the complete schema setup
    once and then run these migrations.
    """
    async with AsyncSessionLocal() as session:

        # ----------------------------------------------------------
        # Columns used by the progressive Cameroon-style education
        # system. We keep the existing education_level column as the
        # canonical current level.
        # ----------------------------------------------------------
        migration_columns = {
            "username": (
                "ALTER TABLE life_characters "
                "ADD COLUMN username VARCHAR(80)"
            ),
            "last_study_at": (
                "ALTER TABLE life_characters "
                "ADD COLUMN last_study_at TIMESTAMPTZ"
            ),
            "last_work_at": (
                "ALTER TABLE life_characters "
                "ADD COLUMN last_work_at TIMESTAMPTZ"
            ),
            "school_class": (
                "ALTER TABLE life_characters "
                "ADD COLUMN school_class VARCHAR(80)"
            ),
            "school_year": (
                "ALTER TABLE life_characters "
                "ADD COLUMN school_year INTEGER"
            ),
            "school_xp": (
                "ALTER TABLE life_characters "
                "ADD COLUMN school_xp BIGINT NOT NULL DEFAULT 0"
            ),
            "school_xp_required": (
                "ALTER TABLE life_characters "
                "ADD COLUMN school_xp_required BIGINT NOT NULL DEFAULT 100"
            ),
            "school_last_exam_at": (
                "ALTER TABLE life_characters "
                "ADD COLUMN school_last_exam_at TIMESTAMPTZ"
            ),
            "current_diploma": (
                "ALTER TABLE life_characters "
                "ADD COLUMN current_diploma VARCHAR(100)"
            ),
        }

        result = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'life_characters'
                """
            )
        )

        existing = {row[0] for row in result.fetchall()}

        for column, statement in migration_columns.items():
            if column not in existing:
                await session.execute(text(statement))

        # ----------------------------------------------------------
        # Normalize the new school fields from the existing
        # education_level field. No existing education data is erased.
        # ----------------------------------------------------------
        await session.execute(
            text(
                """
                UPDATE life_characters
                SET school_class = CASE
                    WHEN education_level ILIKE '%primaire%' THEN 'CM2'
                    WHEN education_level ILIKE '%collège%' THEN '3e'
                    WHEN education_level ILIKE '%lycée%' AND (
                        current_diploma ILIKE '%baccalaur%'
                        OR diploma_level ILIKE '%baccalaur%'
                    ) THEN 'Terminale'
                    WHEN education_level ILIKE '%lycée%' THEN 'Première'
                    WHEN education_level ILIKE '%univers%' OR education_level ILIKE '%supérieur%' THEN 'Université'
                    ELSE COALESCE(school_class, 'CM2')
                END,
                current_diploma = CASE
                    WHEN education_level ILIKE '%primaire%' THEN COALESCE(NULLIF(current_diploma, ''), 'CEP')
                    WHEN education_level ILIKE '%collège%' THEN COALESCE(NULLIF(current_diploma, ''), 'BEPC')
                    WHEN education_level ILIKE '%lycée%' AND (
                        current_diploma ILIKE '%baccalaur%'
                        OR diploma_level ILIKE '%baccalaur%'
                    ) THEN COALESCE(NULLIF(current_diploma, ''), 'Baccalauréat')
                    WHEN education_level ILIKE '%lycée%' THEN COALESCE(NULLIF(current_diploma, ''), 'Probatoire')
                    WHEN education_level ILIKE '%univers%' OR education_level ILIKE '%supérieur%' THEN NULL
                    ELSE current_diploma
                END
                """
            )
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET school_xp_required = 100
                WHERE school_xp_required IS NULL
                   OR school_xp_required <= 0
                """
            )
        )

        # ----------------------------------------------------------
        # Keep education history consistent for existing characters.
        # ----------------------------------------------------------
        await session.execute(
            text(
                """
                INSERT INTO life_school_years (
                    character_id,
                    class_name,
                    academic_year,
                    result
                )
                SELECT
                    c.id,
                    COALESCE(c.school_class, c.education_level, 'CM2'),
                    EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER,
                    'in_progress'
                FROM life_characters c
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM life_school_years sy
                    WHERE sy.character_id = c.id
                      AND sy.result = 'in_progress'
                )
                """
            )
        )

        await session.commit()


# --------------------------------------------------------------
# EDUCATION CONSTANTS
# --------------------------------------------------------------

MANUWORLD_SCHOOL_PATH = (
    ("primary", "École primaire", "CM2", "CEP"),
    ("college", "Collège", "3e", "BEPC"),
    ("high_school", "Lycée", "Première", "Probatoire"),
    ("terminal", "Lycée", "Terminale", "Baccalauréat"),
    ("university", "Études supérieures", "Université", None),
)


def school_xp_required_for_level(level_key: str) -> int:
    """
    XP required before attempting the exam for a school level.
    The values are game values and can later be controlled globally.
    """
    values = {
        "primary": 100,
        "college": 150,
        "high_school": 200,
        "terminal": 250,
        "university": 500,
    }
    return values.get(level_key, 100)


def school_level_from_character(character: dict[str, Any]) -> dict[str, Any]:
    """
    Converts the existing education_level field into the canonical
    MANUWORLD school representation without changing the database.
    """
    raw = str(character.get("education_level") or "").lower()

    if "terminal" in raw:
        key = "terminal"
    elif "lycée" in raw or "lycee" in raw:
        key = "high_school"
    elif "collège" in raw or "college" in raw:
        key = "college"
    elif "univers" in raw or "supérieur" in raw or "superieur" in raw:
        key = "university"
    else:
        key = "primary"

    for current_key, name, class_name, diploma in MANUWORLD_SCHOOL_PATH:
        if current_key == key:
            return {
                "key": current_key,
                "name": name,
                "class_name": class_name,
                "diploma": diploma,
                "xp_required": school_xp_required_for_level(current_key),
            }

    return {
        "key": "primary",
        "name": "École primaire",
        "class_name": "CM2",
        "diploma": "CEP",
        "xp_required": 100,
    }


async def add_school_xp(
    telegram_id: int,
    amount: int,
) -> dict[str, int] | None:
    """
    Adds school XP while using the existing experience/age system
    independently. This prevents school progression from accidentally
    changing the character's age.
    """
    amount = max(0, int(amount))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT school_xp, school_xp_required
                FROM life_characters
                WHERE telegram_id = :telegram_id
                FOR UPDATE
                """
            ),
            {"telegram_id": telegram_id},
        )

        row = result.mappings().first()

        if row is None:
            return None

        current = int(row["school_xp"] or 0)
        required = int(row["school_xp_required"] or 100)

        current += amount

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET school_xp = :school_xp,
                    school_xp_required = :required,
                    updated_at = NOW()
                WHERE telegram_id = :telegram_id
                """
            ),
            {
                "telegram_id": telegram_id,
                "school_xp": current,
                "required": required,
            },
        )

        await session.commit()

        return {
            "school_xp": current,
            "school_xp_required": required,
        }
