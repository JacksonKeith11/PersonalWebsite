# Samurai: the class's design

**Built (Nov 2026)** at the owner's request, with the Armoured Samurai look (option 3 of four: a black kabuto
with a gold crest, a red face mask, red lacquered plate). The live numbers are in `app/saltbound/classes.py`
(the Samurai block, `RESOLVE_CAP`, `RESOLVE_ROUND`, `MEDITATION`); the measured results are in
`docs/saltbound.md`.

## The mechanic: Sheathed and Drawn

- The blade is **Sheathed** or **Drawn** (`x["sheathed"]`); every fight starts Sheathed. An action's `stance`
  says which it needs (`Combat.do_place`; the bots skip the others in `candidates`).
- **Resolve** (`x["resolve"]`, to 15): +3 at the start of each round while Sheathed (Patient Blade: +5), plus
  the die from Kamae and Sheathe, and what picks add (`Actions.add_resolve`).
- **Sheathed**: the Draw (front row: the die + all the Resolve, then Drawn, Resolve spent), Scabbard Strike
  (the die; stays Sheathed), Kamae (half the die as Armor, the die to Resolve). The **iai counter**
  (`Combat.iai_counter`): the first enemy to hit the Samurai each round is cut for half the Resolve.
- **Drawn**: Cut (the die +2) and Sheathe (half the die as Armor, the die to Resolve, then Sheathed).
- **Any other attack while Sheathed** (a gear skill such as Kesa Cut) works, but it draws the blade and
  throws the Resolve away (`Combat.draw_blade`, in `resolve_action`).
- **Meditation** (the map ability): after a rest, the next fight starts with 8 Resolve.

The decision: how much damage to give up now (the die rather than the die +2, and dice on Kamae rather than
hits) for a bigger Draw later, read against the enemies' intents.

## The kit

Dice d8 + d6, 29 HP (+4 a level). Starts with the Draw, Cut, Scabbard Strike, Kamae and Sheathe, the Katana
(Kesa Cut: the die, then half the die to every enemy in its row) and the Padded Coat. Crits: the Draw,
Vulnerable; Cut, +3 Resolve; Scabbard Strike, Weak; Kesa Cut, Wound.

| | Iai (the draw) | Bushido (the code) |
|---|---|---|
| Actions | Flash Draw (cd 2, Sheathed: every front-row enemy takes the die + half the Resolve; Drawn); Waiting Stance (cd 2, Sheathed: the die +2 Armor, this round's counter cuts for all the Resolve) | Duel (cd 2, any row: its attack turns on you, the die to Resolve); Return Stroke (cd 2, Drawn: the die, then Sheathed); Kiai (cd 3: every enemy Weak, +3 Resolve) |
| Passives | Patient Blade (+5 a round, not 3); Zanshin (after the Draw, the next hit this round +4); Mirror Edge (the counter cuts for all the Resolve); Iai Master (the Draw +5 as the party's first move of the round); Hilt and Sheath (Scabbard Strike +2 Resolve); Deep Kamae (Kamae: the whole die as Armor, +1 Resolve); Chiburi (a Cut that kills sheathes the blade); **One Cut** (capstone: the Draw ignores Armor; a kill keeps half the Resolve and the blade Sheathed) | Honor Guard (each enemy hit on an ally +2 Resolve); Unbowed (below half HP the Draw deals half again); Loyalty (an ally knocked down: Sheathe, +8 Resolve); Tempered Spirit (Resolve to 18, and the Draw gives 3 Armor); **Final Breath** (capstone: once a fight, knocked down, cut the attacker for the Resolve +5) |

## Notes from building it

- **Keys**: an event is already `duel`, so the Duel action is `single_combat`; the Mender has `steady_hands`,
  so that pick became Tempered Spirit (`tempered`).
- **Sheathe adds Resolve.** The first build only gave half the die as Armor, and the bots never sheathed:
  once Drawn they Cut for the rest of the fight (514 Cuts, no Sheathes in six runs). Sheathing has to start
  the next Draw to be worth a die against a Cut.
- **The bots** keep Resolve at `bot.resolve_worth` (0.8 a point, less as the enemies run out of HP) and price
  the Draw by the Resolve it spends (`draw_cost`, cheaper near the cap, where waiting gains nothing);
  `sheathe_value` counts the Resolve a round and the counter. A Sheathed Samurai's other attacks are charged
  the Resolve they'd throw away.
- `tools/saltbound-check.py` sets the blade the way each action needs, with 8 Resolve, before placing it.
