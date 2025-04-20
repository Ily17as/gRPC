import sys
import grpc
import time
from concurrent import futures
import game_pb2 as cf
import game_pb2_grpc as cf_grpc
from grpc import StatusCode


class ConnectFourService(cf_grpc.ConnectFourServicer):
    def __init__(self):
        self.games = {}
        self.next_game_id = 1

    def CreateGame(self, request, context):
        game_id = self.next_game_id
        self.next_game_id += 1

        game = cf.Game(id=game_id, turn=cf.MARK_RED, is_finished=False)
        self.games[game_id] = game

        print(f"[LOG] Created new game: ID={game_id}")
        return game

    def GetGame(self, request, context):
        game_id = request.game_id
        if game_id not in self.games:
            context.set_code(StatusCode.NOT_FOUND)
            context.set_details("Game not found.")
            print(f"[ERROR] GetGame: Game ID={game_id} not found")
            return cf.Game()
        return self.games[game_id]

    def MakeMove(self, request, context):
        game_id = request.game_id
        move = request.move

        if game_id not in self.games:
            context.set_code(StatusCode.NOT_FOUND)
            context.set_details("Game not found.")
            print(f"[ERROR] MakeMove: Game ID={game_id} not found")
            return cf.Game()

        game = self.games[game_id]

        if game.is_finished:
            context.set_code(StatusCode.FAILED_PRECONDITION)
            context.set_details("Game is already finished.")
            print(f"[ERROR] Game {game_id} is finished.")
            return game

        if move.mark != game.turn:
            context.set_code(StatusCode.FAILED_PRECONDITION)
            context.set_details("It's not your turn.")
            print(f"[ERROR] Game {game_id}: Not player’s turn.")
            return game

        if move.column < 1 or move.column > 7:
            context.set_code(StatusCode.INVALID_ARGUMENT)
            context.set_details("Column must be between 1 and 7.")
            print(f"[ERROR] Invalid column: {move.column}")
            return game

        col_moves = [m for m in game.moves if m.column == move.column]
        if len(col_moves) >= 6:
            context.set_code(StatusCode.FAILED_PRECONDITION)
            context.set_details("Column is full.")
            print(f"[ERROR] Column {move.column} is full.")
            return game

        game.moves.append(move)
        winner = self.check_winner(game.moves)

        if winner:
            game.winner = winner
            game.is_finished = True
            print(f"[LOG] Game {game_id}: Player {winner} wins!")
        elif len(game.moves) >= 6 * 7:
            game.is_finished = True
            print(f"[LOG] Game {game_id}: Draw.")
        else:
            game.turn = cf.MARK_YELLOW if game.turn == cf.MARK_RED else cf.MARK_RED

        return game

    def check_winner(self, moves):
        # Построим поле 6x7
        board = [[0] * 7 for _ in range(6)]
        for move in moves:
            for row in reversed(range(6)):
                if board[row][move.column - 1] == 0:
                    board[row][move.column - 1] = move.mark
                    break

        def check_line(r, c, dr, dc, mark):
            count = 0
            for _ in range(4):
                if 0 <= r < 6 and 0 <= c < 7 and board[r][c] == mark:
                    count += 1
                    r += dr
                    c += dc
                else:
                    break
            return count == 4

        for r in range(6):
            for c in range(7):
                mark = board[r][c]
                if mark == 0:
                    continue
                if (
                    check_line(r, c, 0, 1, mark) or  # →
                    check_line(r, c, 1, 0, mark) or  # ↓
                    check_line(r, c, 1, 1, mark) or  # ↘
                    check_line(r, c, 1, -1, mark)    # ↙
                ):
                    return mark
        return None


def serve(port):
    server = grpc.server(futures.ThreadPoolExecutor())
    cf_grpc.add_ConnectFourServicer_to_server(ConnectFourService(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[INFO] gRPC server listening on port {port}")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("[INFO] Server shutting down.")
        server.stop(0)


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "50051"
    serve(port)
