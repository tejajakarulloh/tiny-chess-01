import base64, json, os, sys, urllib.error, urllib.request, zlib

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")
VAL = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 20000}
_DATA = b"eJy9U80OwiAMfhWy80hGsRdfxezi1WTxbnx3pZSWdkw9mfA1pP/9oI/pPp3DZZnD8OAXJAa8kRnQ6ZEOeWCFaqUIMLTqHGJBEg1dI/YJSQNNdAXHs6xzmLYyaix9x1MReSDIoC7g8tSKEt0qI4OdJB3r24Sptq/2ZW/fxbv8aDoFYQx9fz/NWWi5Ei0gNB8Kcdkf9VrMC6Gzoreii00OJvoIJr//Sbb1T9MVMm5EhlKkVKLVOSr/6wdHEdm62CUZira+/qdDh6yPwbe66OvzBWT/u3Y="
PST = json.loads(zlib.decompress(base64.b64decode(_DATA)).decode())

def post(path, body):
    req = urllib.request.Request(ENV_URL + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")

def parse_board(fen):
    board, rows = {}, fen.split()[0].split("/")
    for r, row in enumerate(rows):
        col = 0
        for c in row:
            if c.isdigit():
                col += int(c)
            else:
                board["abcdefgh"[col] + str(8 - r)] = c
                col += 1
    return board

def sq_idx(sq):
    return (8 - int(sq[1])) * 8 + (ord(sq[0]) - ord("a"))

def eval_pos(board, is_white):
    score = 0
    for sq, p in board.items():
        low = p.lower()
        val = VAL.get(low, 0)
        idx = sq_idx(sq)
        pst_val = PST.get(low, [0]*64)[idx if p.isupper() else (63 - idx)]
        tot = val + pst_val
        score += tot if p.isupper() else -tot
    return score if is_white else -score

def sort_moves(board, moves):
    def key(m):
        f, t = m[:2], m[2:4]
        victim, mover = board.get(t), board.get(f)
        v_val = VAL.get(victim.lower(), 0) if victim else 0
        m_val = VAL.get(mover.lower(), 0) if mover else 0
        promo = VAL.get(m[4], 0) if len(m) == 5 else 0
        return -(v_val * 10 - m_val + promo)
    return sorted(moves, key=key)

def simulate_move(board, move):
    nb = dict(board)
    f, t = move[:2], move[2:4]
    p = nb.pop(f, None)
    if not p: return nb
    if len(move) == 5:
        p = move[4].upper() if p.isupper() else move[4].lower()
    nb[t] = p
    if p.lower() == "k" and abs(ord(f[0]) - ord(t[0])) > 1:
        row = f[1]
        if t[0] == "g":
            nb.pop("h" + row, None)
            nb["f" + row] = "R" if p.isupper() else "r"
        elif t[0] == "c":
            nb.pop("a" + row, None)
            nb["d" + row] = "R" if p.isupper() else "r"
    return nb

def choose_move(fen, legal, is_white):
    board = parse_board(fen)
    sorted_m = sort_moves(board, legal)
    if not sorted_m: return legal[0]
    best_move, best_score = sorted_m[0], -999999
    for m in sorted_m:
        nb = simulate_move(board, m)
        score = -eval_pos(nb, not is_white)
        if m[2:4] in ("d4", "d5", "e4", "e5"):
            score += 20
        if score > best_score:
            best_score, best_move = score, m
    return best_move

def main():
    while True:
        g = post("/game", {})
        if g.get("status") == "done":
            break
        is_white = g.get("colour") == "white"
        while g.get("status") == "your_move":
            m = choose_move(g["fen"], g["legal_moves"], is_white)
            g = post("/move", {"game": g["game"], "move": m})
        print(f"game {g.get('game')}: {g.get('outcome')} by {g.get('reason')}", file=sys.stderr)
    print(f"done: {g.get('wins', 0)} won, {g.get('draws', 0)} drawn, {g.get('losses', 0)} lost", file=sys.stderr)

if __name__ == "__main__":
    main()
