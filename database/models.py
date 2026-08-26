from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer
from sqlalchemy import Boolean, Integer,Column
from sqlalchemy import JSON
from sqlalchemy import UniqueConstraint


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="fr",
    )
    coins: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=50_000_000,
    )

    gems: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=500,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tier: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    max_clubs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=20,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="inactive",
    )

    parent_league_id: Mapped[int | None] = mapped_column(
        ForeignKey("leagues.id"),
        nullable=True,
    )

    promotion_target_id: Mapped[int | None] = mapped_column(
        ForeignKey("leagues.id"),
        nullable=True,
    )

    relegation_target_id: Mapped[int | None] = mapped_column(
        ForeignKey("leagues.id"),
        nullable=True,
    )

    promotion_slots: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )

    relegation_slots: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    clubs: Mapped[list["Club"]] = relationship(
        back_populates="league",
    )

class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)

    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    league_id: Mapped[int | None] = mapped_column(
        ForeignKey("leagues.id"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    logo_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    stadium_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    owner: Mapped["User"] = relationship()

    league: Mapped["League | None"] = relationship(
        back_populates="clubs",
    )
class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    position: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    overall: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    potential: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    value: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    image_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    starter_pool = Column(Boolean, nullable=False, default=False)


class ClubPlayer(Base):
    __tablename__ = "club_players"

    id: Mapped[int] = mapped_column(primary_key=True)

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_current: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    club: Mapped["Club"] = relationship()

    player: Mapped["Player"] = relationship()
# ==========================================================
# PLAYER CONTRACT
# ==========================================================

class PlayerContract(Base):
    __tablename__ = "player_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
    )

    salary: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=100_000,
    )

    duration_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=30),
    )

    last_paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    club: Mapped["Club"] = relationship()
    player: Mapped["Player"] = relationship()


# ==========================================================
# SAVED LINEUP
# ==========================================================

class SavedLineup(Base):
    __tablename__ = "saved_lineups"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    formation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    club: Mapped["Club"] = relationship()

    players: Mapped[list["SavedLineupPlayer"]] = relationship(
        back_populates="saved_lineup",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "club_id",
            "formation",
            name="uq_saved_lineup_club_formation",
        ),
    )


# ==========================================================
# SAVED LINEUP PLAYER
# ==========================================================

class SavedLineupPlayer(Base):
    __tablename__ = "saved_lineup_players"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    saved_lineup_id: Mapped[int] = mapped_column(
        ForeignKey(
            "saved_lineups.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
    )

    slot_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    position: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    shirt_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_captain: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    saved_lineup: Mapped["SavedLineup"] = relationship(
        back_populates="players",
    )

    player: Mapped["Player"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "saved_lineup_id",
            "slot_id",
            name="uq_saved_lineup_slot",
        ),
    )
class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class LeagueSeasonClub(Base):
    __tablename__ = "league_season_clubs"

    id: Mapped[int] = mapped_column(primary_key=True)

    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id"),
        nullable=False,
    )

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id"),
        nullable=False,
    )

    position: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    played: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    wins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    draws: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    losses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    goals_for: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    goals_against: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    promoted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    relegated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(primary_key=True)

    season_id: Mapped[int | None] = mapped_column(
    ForeignKey("seasons.id"),
    nullable=True,
)

    home_club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    away_club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    competition_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    round_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
    )
class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)

    fixture_id: Mapped[int] = mapped_column(
        ForeignKey("fixtures.id"),
        unique=True,
        nullable=False,
    )

    home_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    away_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_started",
    )

    possession_home: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )

    possession_away: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )

    stats: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id"),
        nullable=False,
    )

    minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    club_id: Mapped[int | None] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=True,
    )

    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
    )

    data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class Lineup(Base):
    __tablename__ = "lineups"

    id: Mapped[int] = mapped_column(primary_key=True)

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id"),
        nullable=False,
    )

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    formation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class LineupPlayer(Base):
    __tablename__ = "lineup_players"

    id: Mapped[int] = mapped_column(primary_key=True)

    lineup_id: Mapped[int] = mapped_column(
        ForeignKey("lineups.id"),
        nullable=False,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
    )

    position: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    shirt_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_starting: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_captain: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
class MatchPlayerStats(Base):
    __tablename__ = "match_player_stats"

    id: Mapped[int] = mapped_column(primary_key=True)

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id"),
        nullable=False,
    )

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
    )

    minutes_played: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    goals: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    assists: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    shots: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    shots_on_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    passes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    tackles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    yellow_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    red_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    rating: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0,
    )
class TransferListing(Base):
    __tablename__ = "transfer_listings"

    id: Mapped[int] = mapped_column(primary_key=True)

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        unique=True,
        nullable=False,
    )

    price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    currency = Column(String(10), nullable=False, default="COINS")

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="available",
    )

    listed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    sold_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    player: Mapped["Player"] = relationship()
    currency = Column(String(10), nullable=False, default="COINS")
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)

    sender_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    receiver_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    offered_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
    )

    requested_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
    )

    offered_coins: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    requested_coins: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    product_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    telegram_charge_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class DailyReward(Base):
    __tablename__ = "daily_rewards"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    reward_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    streak: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)

    referrer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    referred_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    reward_claimed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    question: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    option_a: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    option_b: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    option_c: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    option_d: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    correct_answer: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )

    reward: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=5_000_000,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
class QuizHistory(Base):
    __tablename__ = "quiz_history"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_questions.id"),
        nullable=False,
    )

    answer: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class RankingSnapshot(Base):
    __tablename__ = "ranking_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id"),
        nullable=False,
    )

    ranking_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    rating: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0,
    )

    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    matches_played: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    wins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    draws: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    losses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    goals: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
class Sanction(Base):
    __tablename__ = "sanctions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    issued_by: Mapped[int] = mapped_column(
    BigInteger,
    ForeignKey("users.id"),
    nullable=False,
)
class Trophy(Base):
    __tablename__ = "trophies"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class UserTrophy(Base):
    __tablename__ = "user_trophies"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    trophy_id: Mapped[int] = mapped_column(
        ForeignKey("trophies.id"),
        nullable=False,
    )

    season_id: Mapped[int | None] = mapped_column(
        ForeignKey("seasons.id"),
        nullable=True,
    )

    rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class Award(Base):
    __tablename__ = "awards"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    award_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    season_id: Mapped[int | None] = mapped_column(
        ForeignKey("seasons.id"),
        nullable=True,
    )

    awarded_by: Mapped[int] = mapped_column(
    BigInteger,
    ForeignKey("users.id"),
    nullable=False,
)

    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    competition_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
class CompetitionSeason(Base):
    __tablename__ = "competition_seasons"

    id: Mapped[int] = mapped_column(primary_key=True)

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"),
        nullable=False,
    )

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
class CompetitionRound(Base):
    __tablename__ = "competition_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)

    competition_season_id: Mapped[int] = mapped_column(
        ForeignKey("competition_seasons.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    round_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    round_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
class CompetitionParticipant(Base):
    __tablename__ = "competition_participants"

    id: Mapped[int] = mapped_column(primary_key=True)

    competition_season_id: Mapped[int] = mapped_column(
        ForeignKey("competition_seasons.id"),
        nullable=False,
    )

    # Club participant à une compétition de clubs
    club_id: Mapped[int | None] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=True,
    )

    # Manager qui représente le pays en World Cup
    manager_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
    )

    # Utilisé pour la représentation temporaire en World Cup
    country_code: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    country_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    seed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )

    eliminated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "competition_season_id",
            "country_code",
            name="uq_worldcup_country",
        ),
        UniqueConstraint(
            "competition_season_id",
            "manager_id",
            name="uq_worldcup_manager",
        ),
    )
class GameSetting(Base):
    __tablename__ = "game_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

# ==========================================================
# TELEGRAM STARS PAYMENTS
# ==========================================================

class StarPayment(Base):
    __tablename__ = "star_payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    telegram_payment_charge_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )

    product: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    stars: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    coins: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    gems: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )