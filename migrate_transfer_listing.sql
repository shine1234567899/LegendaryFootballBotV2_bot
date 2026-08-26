-- Run once on the existing PostgreSQL database.
-- This adds the missing seller_club_id column required by /sellplayer
-- and /mytransfers.

ALTER TABLE transfer_listings
ADD COLUMN IF NOT EXISTS seller_club_id BIGINT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_transfer_listings_seller_club'
    ) THEN
        ALTER TABLE transfer_listings
        ADD CONSTRAINT fk_transfer_listings_seller_club
        FOREIGN KEY (seller_club_id)
        REFERENCES clubs(id);
    END IF;
END $$;
