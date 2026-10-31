# Shared bits for Saltbound's sprites. Reuses Roguelike Tactics' pixel kit so the two games share a look.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'threefold-art'))
from kit import G, render, sheet  # noqa: E402,F401
E = '#1a1420'
SKIN = {'s': '#e0b48a', 'S': '#a8785a'}
SKIN2 = {'s': '#c8946a', 'S': '#8e6448'}
def legs(g, c='L', boot='k', y=24):
    g.rect(10, y, 12, 28, c); g.rect(15, y, 17, 28, c); g.rect(9, 29, 12, 30, boot); g.rect(15, 29, 18, 30, boot)
def face(g, x=10, y=6, w=8, h=6, eyes=True):
    g.rect(x, y, x + w - 1, y + h - 1, 's'); g.rect(x, y, x + w - 1, y, 'S')
    if eyes:
        g.px(x + 2, y + 2, 'e'); g.px(x + 5, y + 2, 'e')
def torso(g, c, y=13, rows=11):
    spans = [(1, 10)] + [(0, 11)] * (rows - 1)
    g.rows(8, y, spans, c)
