from pathlib import Path
from typing import Annotated

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import game

Row = Annotated[
    list[Annotated[int, Field(ge=0, lt=game.KINDS)]],
    Field(min_length=game.SIZE, max_length=game.SIZE),
]
BoardModel = Annotated[list[Row], Field(min_length=game.SIZE, max_length=game.SIZE)]


class Cell(BaseModel):
    row: int = Field(ge=0, lt=game.SIZE)
    col: int = Field(ge=0, lt=game.SIZE)


class MoveRequest(BaseModel):
    board: BoardModel
    a: Cell
    b: Cell


class Step(BaseModel):
    cleared: list[tuple[int, int]]
    points: int
    board: BoardModel


class MoveResponse(BaseModel):
    valid: bool
    steps: list[Step] = []
    board: BoardModel
    shuffled: bool = False


class NewGameResponse(BaseModel):
    board: BoardModel


app = FastAPI(title="Gem Match")


@app.post("/api/new")
def new_game() -> NewGameResponse:
    return NewGameResponse(board=game.new_board())


@app.post("/api/move")
def move(req: MoveRequest) -> MoveResponse:
    result = game.play_move(req.board, (req.a.row, req.a.col), (req.b.row, req.b.col))
    if result is None:
        return MoveResponse(valid=False, board=req.board)
    return MoveResponse(valid=True, **result)


# On Vercel, public/ is served by the CDN before reaching this app.
# The mount lets `uvicorn main:app` serve the same files locally.
app.mount(
    "/",
    StaticFiles(directory=Path(__file__).parent / "public", html=True, check_dir=False),
    name="public",
)
