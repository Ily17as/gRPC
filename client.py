import time
import argparse
import random
from typing import Iterable
from enum import Enum, StrEnum
import grpc
import game_pb2 as cf
import game_pb2_grpc as cf_grpc


class Player(StrEnum):
    RED = "R"
    YELLOW = "Y"

    def mark(self) -> cf.Mark:
        if self == Player.RED:
            return cf.MARK_RED
        if self == Player.YELLOW:
            return cf.MARK_YELLOW
        raise Exception("Invalid player.")

    def equals_mark(self, mark: cf.Mark) -> bool:
        return self.mark() == mark


class Action(Enum):
    CREATE_GAME = 1
    CONNECT_TO_GAME = 2


def prompt_action() -> Action:
    while True:
        print("Please, choose an option:")
        print(" (1) create a new game")
        print(" (2) connect to a game")
        answer = input("> ")

        try:
            answer = int(answer.strip())
        except ValueError:
            continue

        for item in Action:
            if item.value == answer:
                return item


def prompt_player(auto_choice: str = None) -> Player:
    if auto_choice:
        return Player(auto_choice.upper())
    while True:
        answer = input("Choose a player (R/Y): ").upper()
        if answer == Player.RED.value:
            return Player.RED
        if answer == Player.YELLOW.value:
            return Player.YELLOW


def prompt_game_id(auto_id: int = None) -> int:
    if auto_id is not None:
        return auto_id
    while True:
        try:
            return int(input("Enter game ID to connect: "))
        except ValueError:
            continue


def prompt_move(player: Player, valid_columns: set[int], automate: bool) -> int:
    if automate:
        return random.choice(list(valid_columns))
    while True:
        try:
            col = int(input(f"Your move (column 1-7) [{player.value}]: "))
        except ValueError:
            continue
        if not (1 <= col <= 7):
            print("Column must be in range [1,7].")
        elif col not in valid_columns:
            print("This column is full.")
        else:
            return col


def draw_board(moves: Iterable[cf.Move]):
    board = [[" "] * 7 for _ in range(6)]
    for move in moves:
        for row in reversed(board):
            if row[move.column - 1] == " ":
                row[move.column - 1] = "R" if move.mark == cf.MARK_RED else "Y"
                break
    print(" 1 2 3 4 5 6 7")
    for row in board:
        print("|" + "|".join(row) + "|")
    print(" " + "-" * 13)


def play_game(stub: cf_grpc.ConnectFourStub, game: cf.Game, player: Player, automate: bool):
    while not game.is_finished:
        draw_board(game.moves)
        if player.equals_mark(game.turn):
            full_columns = {move.column for move in game.moves if sum(1 for m in game.moves if m.column == move.column) >= 6}
            available_columns = set(range(1, 8)) - full_columns
            if not available_columns:
                break
            col = prompt_move(player, available_columns, automate)
            move = cf.Move(mark=player.mark(), column=col)
            game = stub.MakeMove(cf.MakeMoveRequest(game_id=game.id, move=move))
        else:
            if not automate:
                print("Waiting for the opponent's move...\n")
            while not game.is_finished and not player.equals_mark(game.turn):
                time.sleep(1)
                game = stub.GetGame(cf.GetGameRequest(game_id=game.id))

    print("[ Game over ]")
    draw_board(game.moves)
    if not game.HasField("winner"):
        print("Draw.")
    elif player.equals_mark(game.winner):
        print("🎉 You won! 🎉")
    else:
        print("You lose.")


def main(server_address: str, automate: bool, player_choice: str, game_id_arg: int):
    with grpc.insecure_channel(server_address) as channel:
        stub = cf_grpc.ConnectFourStub(channel)

        print("Welcome to Connect Four! 👋\n")

        action = prompt_action() if not automate else (Action.CONNECT_TO_GAME if game_id_arg is not None else Action.CREATE_GAME)
        if action == Action.CREATE_GAME:
            player = prompt_player(player_choice) if automate else prompt_player()
            print(f"Creating a new game...")
            game = stub.CreateGame(cf.CreateGameRequest())
        elif action == Action.CONNECT_TO_GAME:
            game_id = prompt_game_id(game_id_arg)
            player = prompt_player(player_choice) if automate else prompt_player()
            print(f"Retrieving game (ID={game_id})...")
            try:
                game = stub.GetGame(cf.GetGameRequest(game_id=game_id))
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    print(f"Error: game with ID={game_id} not found.")
                    return
                else:
                    raise e
        else:
            raise Exception(f"Invalid action: {action}")

        print(f"Playing game (ID={game.id}) as player {player}.")
        play_game(stub, game, player, automate)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("server_address", help="Address of the Connect Four server.")
    parser.add_argument("--automate", action="store_true", help="Let the client play automatically.")
    parser.add_argument("--player", choices=["R", "Y"], help="Choose player color (R/Y) when automating.")
    parser.add_argument("--game_id", type=int, help="Game ID to connect to when automating.")
    args = parser.parse_args()

    try:
        main(args.server_address, args.automate, args.player, args.game_id)
    except grpc.RpcError as e:
        print(f"gRPC error (code={e.code()}): {e.details()}")
    except KeyboardInterrupt:
        print("Exiting...")
