import os
N = int(os.environ.get("PERTURB_N") or "0")

def pytest_configure(config):
    if N <= 0:
        return
    import gilded.chassis as chassis
    G = chassis.GildedGame
    _init, _end = G.__init__, G.end_turn

    def init(self, *a, **k):
        _init(self, *a, **k)
        for _ in range(N):
            self.rng.random()

    def end_turn(self, *a, **k):
        out = _end(self, *a, **k)
        for _ in range(N):
            self.rng.random()
        return out

    G.__init__, G.end_turn = init, end_turn
