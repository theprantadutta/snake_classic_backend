"""
Multiplayer API endpoints with WebSocket support
"""
import json
import asyncio
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.user import User
from app.core.dependencies import get_current_user
from app.core.security import decode_access_token
from app.schemas.multiplayer import (
    GameCreateRequest,
    GameJoinRequest,
    GameResponse,
    GameCreateResponse,
    GameJoinResponse,
    PlayerAction,
    WebSocketMessage,
)
from app.services.multiplayer_service import multiplayer_service

router = APIRouter(prefix="/multiplayer", tags=["multiplayer"])


@router.post("/create", response_model=GameCreateResponse)
async def create_game(
    request: GameCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new multiplayer game room"""
    try:
        game = multiplayer_service.create_game(
            db,
            current_user.id,
            mode=request.mode,
            max_players=request.max_players,
            grid_size=request.grid_size,
            speed=request.speed
        )
        return GameCreateResponse(
            success=True,
            message="Game created successfully",
            game=multiplayer_service.get_game_response(game),
            room_code=game.room_code
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/join", response_model=GameJoinResponse)
async def join_game(
    request: GameJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join a game by room code"""
    try:
        game, player_index = multiplayer_service.join_game_by_code(
            db, current_user.id, request.room_code
        )
        return GameJoinResponse(
            success=True,
            message="Joined game successfully",
            game=multiplayer_service.get_game_response(game),
            player_index=player_index
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/game/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get game state"""
    game = multiplayer_service.active_games.get(game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    return multiplayer_service.get_game_response(game)


@router.post("/game/{game_id}/start")
async def start_game(
    game_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a game (host only)"""
    game = multiplayer_service.active_games.get(game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    # Check if user is in this game
    if current_user.id not in game.players:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not in this game"
        )

    # Only the host (first player) can start
    if game.players[current_user.id].player_index != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can start the game"
        )

    success = multiplayer_service.start_game(db, game_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start game - need at least 2 players"
        )

    return {"success": True, "message": "Game starting"}


@router.post("/game/{game_id}/leave")
async def leave_game(
    game_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Leave a game"""
    multiplayer_service.leave_game(db, current_user.id, game_id)
    return {"success": True, "message": "Left game"}


@router.get("/current")
async def get_current_game(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the game the current user is in, if any"""
    game_id = multiplayer_service.get_user_current_game(current_user.id)
    if not game_id:
        return {"in_game": False, "game": None}

    game = multiplayer_service.active_games.get(game_id)
    if not game:
        return {"in_game": False, "game": None}

    return {
        "in_game": True,
        "game": multiplayer_service.get_game_response(game)
    }


# WebSocket endpoint
@router.websocket("/ws/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str):
    """WebSocket endpoint for real-time game communication"""
    await websocket.accept()

    # Get token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"type": "error", "data": {"message": "No token provided"}})
        await websocket.close()
        return

    # Verify token
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload.get("sub"))
    except Exception as e:
        await websocket.send_json({"type": "error", "data": {"message": "Invalid token"}})
        await websocket.close()
        return

    # Check if game exists
    game = multiplayer_service.active_games.get(game_id)
    if not game:
        await websocket.send_json({"type": "error", "data": {"message": "Game not found"}})
        await websocket.close()
        return

    # Check if user is in this game
    if user_id not in game.players:
        await websocket.send_json({"type": "error", "data": {"message": "Not in this game"}})
        await websocket.close()
        return

    # Add connection
    multiplayer_service.game_connections[game_id].add(websocket)

    # Send initial state
    state = multiplayer_service.get_game_state(game_id)
    if state:
        await websocket.send_json({
            "type": "game_state",
            "data": state.model_dump(mode="json")
        })

    db = SessionLocal()

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)

            action = PlayerAction(**message)

            if action.action == "move":
                multiplayer_service.process_player_move(
                    game_id, user_id, action.direction
                )

            elif action.action == "ready":
                # Player is ready - could trigger game start if all ready
                pass

            elif action.action == "start" and game.players[user_id].player_index == 0:
                # Host starting game
                multiplayer_service.start_game(db, game_id)

                # Start countdown
                for i in range(3, 0, -1):
                    game.countdown = i
                    await _broadcast_to_game(game_id, {
                        "type": "countdown",
                        "data": {"count": i}
                    })
                    await asyncio.sleep(1)

                game.status = "playing"
                game.countdown = None

                # Start game loop
                asyncio.create_task(_game_loop(db, game_id))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Remove connection
        if game_id in multiplayer_service.game_connections:
            multiplayer_service.game_connections[game_id].discard(websocket)

        # Leave game if disconnected during waiting
        if game.status == "waiting":
            multiplayer_service.leave_game(db, user_id, game_id)
            await _broadcast_to_game(game_id, {
                "type": "player_left",
                "data": {"user_id": str(user_id)}
            })

        db.close()


async def _broadcast_to_game(game_id: str, message: dict):
    """Broadcast a message to all players in a game"""
    connections = multiplayer_service.game_connections.get(game_id, set())
    dead_connections = set()

    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead_connections.add(ws)

    # Remove dead connections
    for ws in dead_connections:
        connections.discard(ws)


async def _game_loop(db: Session, game_id: str):
    """Main game loop for a multiplayer game"""
    game = multiplayer_service.active_games.get(game_id)
    if not game:
        return

    try:
        while game.status == "playing":
            # Process game tick
            state = multiplayer_service.tick_game(db, game_id)

            if state:
                await _broadcast_to_game(game_id, {
                    "type": "game_state",
                    "data": state.model_dump(mode="json")
                })

            if game.status == "finished":
                await _broadcast_to_game(game_id, {
                    "type": "game_over",
                    "data": {
                        "winner_id": str(game.winner_id) if game.winner_id else None,
                        "final_scores": {
                            str(uid): p.score for uid, p in game.players.items()
                        }
                    }
                })
                break

            # Wait for next tick (based on game speed)
            await asyncio.sleep(game.speed / 1000.0)

    except Exception as e:
        print(f"Game loop error: {e}")
    finally:
        # Clean up game after a delay
        await asyncio.sleep(10)
        multiplayer_service._cleanup_game(db, game_id)
