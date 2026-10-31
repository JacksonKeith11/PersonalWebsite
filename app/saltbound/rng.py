"""A small seeded random number generator whose whole state is one integer.

Everything random in a run (the map, dice, intents, loot, events) draws from the run's `Rng`, and
its state is saved with the run, so a restored run carries on exactly as it would have. Never use
the global `random` module in game code.
"""

MASK = (1 << 64) - 1


class Rng:
    def __init__(self, state):
        self.state = state & MASK

    def next(self):
        # splitmix64
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def random(self):
        return (self.next() >> 11) / float(1 << 53)

    def randint(self, a, b):
        return a + self.next() % (b - a + 1)

    def chance(self, p):
        return self.random() < p

    def choice(self, seq):
        return seq[self.next() % len(seq)]

    def shuffle(self, seq):
        for i in range(len(seq) - 1, 0, -1):
            j = self.next() % (i + 1)
            seq[i], seq[j] = seq[j], seq[i]
        return seq

    def sample(self, seq, k):
        return self.shuffle(list(seq))[:k]

    def weighted(self, pairs):
        """pairs: [(item, weight), ...] -> one item."""
        total = sum(w for _, w in pairs)
        if total <= 0:
            return pairs[0][0]
        x = self.random() * total
        for item, w in pairs:
            x -= w
            if x < 0:
                return item
        return pairs[-1][0]
