"""
Multiplayer game service for managing real-time games
"""
import random
import string
import asyncio
from typing import Optional, List, Dict, Set
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.multiplayer import MultiplayerGame, MultiplayerPlayer
from app.models.user import User
from app.schemas.multiplayer import (
    Position,
    PlayerState,
    GameResponse,
    GameStateUpdate,
)
from app.utils.time_utils import utc_now


# Player colors
PLAYER_COLORS = [
    "#4CAF50",  # Green
    "#2196F3",  # Blue
    "#F44336",  # Red
    "#FF9800",  # Orange
    "#9C27B0",  # Purple
    "#00BCD4",  # Cyan
    "#FFEB3B",  # Yellow
    "#E91E63",  # Pink
]


@dataclass
class ActiveGame:
    """In-memory game state for active games"""
    game_id: str
    db_id: UUID
    status: str = "waiting"
    mode: str = "classic"
    max_players: int = 4
    grid_size: int = 20
    speed: int = 100
    players: Dict[UUID, PlayerState] = field(default_factory=dict)
    food_positions: List[Position] = field(default_factory=list)
    power_ups: List[Dict] = field(default_factory=list)
    countdown: Optional[int] = None
    winner_id: Optional[UUID] = None
    room_code: str = ""
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    game_loop_task: Optional[asyncio.Task] = None


class MultiplayerService:
    """Service for multiplayer game operations"""

    def __init__(self):
        # In-memory storage for active games
        self.active_games: Dict[str, ActiveGame] = {}
        self.room_code_to_game: Dict[str, str] = {}
        self.user_to_game: Dict[UUID, str] = {}
        # WebSocket connections per game
        self.game_connections: Dict[str, Set] = {}

    def _generate_room_code(self) -> str:
        """Generate a unique room code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if code not in self.room_code_to_game:
                return code

    def _spawn_food(self, game: ActiveGame) -> Position:
        """Spawn food at a random valid position"""
        occupied = set()
        for player in game.players.values():
            for pos in player.snake_positions:
                occupied.add((pos.x, pos.y))
        for food in game.food_positions:
            occupied.add((food.x, food.y))

        attempts = 0
        while attempts < 100:
            x = random.randint(0, game.grid_size - 1)
            y = random.randint(0, game.grid_size - 1)
            if (x, y) not in occupied:
                return Position(x=x, y=y)
            attempts += 1

        # Fallback - just pick random spot
        return Position(x=random.randint(0, game.grid_size - 1),
                       y=random.randint(0, game.grid_size - 1))

    def create_game(
        self,
        db: Session,
        user_id: UUID,
        mode: str = "classic",
        max_players: int = 4,
        grid_size: int = 20,
        speed: int = 100
    ) -> ActiveGame:
        """Create a new multiplayer game"""
        # Check if user already in a game
        if user_id in self.user_to_game:
            old_game_id = self.user_to_game[user_id]
            self.leave_game(db, user_id, old_game_id)

        game_id = str(uuid4())
        room_code = self._generate_room_code()

        # Create in database
        db_game = MultiplayerGame(
            game_id=game_id,
            mode=mode,
            status="waiting",
            room_code=room_code,
            max_players=max_players,
            food_positions=[],
            power_ups=[]
        )
        db.add(db_game)
        db.commit()
        db.refresh(db_game)

        # Create in-memory game
        game = ActiveGame(
            game_id=game_id,
            db_id=db_game.id,
            status="waiting",
            mode=mode,
            max_players=max_players,
            grid_size=grid_size,
            speed=speed,
            room_code=room_code,
            created_at=utc_now()
        )

        self.active_games[game_id] = game
        self.room_code_to_game[room_code] = game_id
        self.game_connections[game_id] = set()

        # Add creator as first player
        self._add_player_to_game(db, game, user_id, 0)

        return game

    def join_game_by_code(
        self,
        db: Session,
        user_id: UUID,
        room_code: str
    ) -> tuple[ActiveGame, int]:
        """Join a game by room code. Returns (game, player_index)"""
        game_id = self.room_code_to_game.get(room_code.upper())
        if not game_id:
            raise ValueError("Game not found")

        game = self.active_games.get(game_id)
        if not game:
            raise ValueError("Game not found")

        if game.status != "waiting":
            raise ValueError("Game already started")

        if len(game.players) >= game.max_players:
            raise ValueError("Game is full")

        # Check if already in this game
        if user_id in game.players:
            return game, game.players[user_id].player_index

        # Leave any other game
        if user_id in self.user_to_game:
            old_game_id = self.user_to_game[user_id]
            if old_game_id != game_id:
                self.leave_game(db, user_id, old_game_id)

        player_index = len(game.players)
        self._add_player_to_game(db, game, user_id, player_index)

        return game, player_index

    def _add_player_to_game(
        self,
        db: Session,
        game: ActiveGame,
        user_id: UUID,
        player_index: int
    ):
        """Add a player to a game"""
        user = db.query(User).filter(User.id == user_id).first()

        # Calculate starting position
        start_positions = [
            (2, game.grid_size // 2),
            (game.grid_size - 3, game.grid_size // 2),
            (game.grid_size // 2, 2),
            (game.grid_size // 2, game.grid_size - 3),
        ]
        start_x, start_y = start_positions[player_index % len(start_positions)]

        player_state = PlayerState(
            user_id=user_id,
            username=user.username if user else None,
            display_name=user.display_name if user else None,
            player_index=player_index,
            score=0,
            is_alive=True,
            snake_positions=[Position(x=start_x, y=start_y)],
            direction="right",
            color=PLAYER_COLORS[player_index % len(PLAYER_COLORS)]
        )

        game.players[user_id] = player_state
        self.user_to_game[user_id] = game.game_id

        # Save to database
        db_player = MultiplayerPlayer(
            game_id=game.db_id,
            user_id=user_id,
            player_index=player_index,
            score=0,
            is_alive=True,
            snake_positions=[{"x": start_x, "y": start_y}],
            direction="right"
        )
        db.add(db_player)
        db.commit()

    def leave_game(self, db: Session, user_id: UUID, game_id: str):
        """Remove a player from a game"""
        game = self.active_games.get(game_id)
        if not game:
            return

        if user_id in game.players:
            del game.players[user_id]

        if user_id in self.user_to_game:
            del self.user_to_game[user_id]

        # If game is empty, clean up
        if not game.players:
            self._cleanup_game(db, game_id)

    def _cleanup_game(self, db: Session, game_id: str):
        """Clean up a game"""
        game = self.active_games.get(game_id)
        if not game:
            return

        # Cancel game loop if running
        if game.game_loop_task:
            game.game_loop_task.cancel()

        # Update database
        db_game = db.query(MultiplayerGame).filter(
            MultiplayerGame.game_id == game_id
        ).first()
        if db_game:
            db_game.status = "finished"
            db.commit()

        # Remove from memory
        if game.room_code in self.room_code_to_game:
            del self.room_code_to_game[game.room_code]
        if game_id in self.game_connections:
            del self.game_connections[game_id]
        if game_id in self.active_games:
            del self.active_games[game_id]

    def start_game(self, db: Session, game_id: str) -> bool:
        """Start a game"""
        game = self.active_games.get(game_id)
        if not game:
            return False

        if game.status != "waiting":
            return False

        if len(game.players) < 2:
            return False

        game.status = "countdown"
        game.countdown = 3

        # Spawn initial food
        for _ in range(3):
            game.food_positions.append(self._spawn_food(game))

        # Update database
        db_game = db.query(MultiplayerGame).filter(
            MultiplayerGame.game_id == game_id
        ).first()
        if db_game:
            db_game.status = "countdown"
            db_game.food_positions = [{"x": f.x, "y": f.y} for f in game.food_positions]
            db.commit()

        return True

    def process_player_move(
        self,
        game_id: str,
        user_id: UUID,
        direction: str
    ) -> bool:
        """Process a player move"""
        game = self.active_games.get(game_id)
        if not game or game.status != "playing":
            return False

        player = game.players.get(user_id)
        if not player or not player.is_alive:
            return False

        # Validate direction change (can't reverse)
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        if opposites.get(direction) == player.direction:
            return False

        player.direction = direction
        return True

    def get_game_state(self, game_id: str) -> Optional[GameStateUpdate]:
        """Get current game state"""
        game = self.active_games.get(game_id)
        if not game:
            return None

        return GameStateUpdate(
            game_id=game.game_id,
            status=game.status,
            players=list(game.players.values()),
            food_positions=game.food_positions,
            power_ups=game.power_ups,
            countdown=game.countdown,
            winner_id=game.winner_id
        )

    def get_game_response(self, game: ActiveGame) -> GameResponse:
        """Convert ActiveGame to GameResponse"""
        return GameResponse(
            id=game.db_id,
            game_id=game.game_id,
            mode=game.mode,
            status=game.status,
            room_code=game.room_code,
            max_players=game.max_players,
            current_players=len(game.players),
            players=list(game.players.values()),
            food_positions=game.food_positions,
            power_ups=game.power_ups,
            grid_size=game.grid_size,
            created_at=game.created_at,
            started_at=game.started_at
        )

    def get_user_current_game(self, user_id: UUID) -> Optional[str]:
        """Get the game ID a user is currently in"""
        return self.user_to_game.get(user_id)

    def tick_game(self, db: Session, game_id: str) -> Optional[GameStateUpdate]:
        """Process one game tick - move snakes, check collisions"""
        game = self.active_games.get(game_id)
        if not game or game.status != "playing":
            return None

        # Move each alive player's snake
        for player in game.players.values():
            if not player.is_alive:
                continue

            head = player.snake_positions[0]
            dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[player.direction]
            new_head = Position(x=head.x + dx, y=head.y + dy)

            # Check wall collision
            if new_head.x < 0 or new_head.x >= game.grid_size or \
               new_head.y < 0 or new_head.y >= game.grid_size:
                player.is_alive = False
                continue

            # Check self collision
            if any(pos.x == new_head.x and pos.y == new_head.y for pos in player.snake_positions):
                player.is_alive = False
                continue

            # Check collision with other snakes
            for other_id, other_player in game.players.items():
                if other_id == player.user_id:
                    continue
                if any(pos.x == new_head.x and pos.y == new_head.y for pos in other_player.snake_positions):
                    player.is_alive = False
                    break

            if not player.is_alive:
                continue

            # Move snake
            player.snake_positions.insert(0, new_head)

            # Check food
            ate_food = False
            for i, food in enumerate(game.food_positions):
                if food.x == new_head.x and food.y == new_head.y:
                    player.score += 10
                    game.food_positions.pop(i)
                    game.food_positions.append(self._spawn_food(game))
                    ate_food = True
                    break

            if not ate_food:
                player.snake_positions.pop()

        # Check for game over
        alive_players = [p for p in game.players.values() if p.is_alive]
        if len(alive_players) <= 1:
            game.status = "finished"
            if alive_players:
                game.winner_id = alive_players[0].user_id

            # Update database
            db_game = db.query(MultiplayerGame).filter(
                MultiplayerGame.game_id == game_id
            ).first()
            if db_game:
                db_game.status = "finished"
                db_game.finished_at = utc_now()
                db.commit()

        return self.get_game_state(game_id)


# Global instance
multiplayer_service = MultiplayerService()
