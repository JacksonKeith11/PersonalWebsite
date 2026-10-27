# Threefold Path: art direction

The look of the game's characters, what each hero class looks like, and how to draw new sprites so
they match. Read it before drawing or changing a sprite. Terrain is covered in `docs/game.md`
(`tiles.js`); this doc is about characters and monsters.

## The look

**Matte, cel-shaded, top-down three-quarter pixel art.** The owner's reference is a muted
top-down wizard:
<https://assetstorev1-prd-cdn.unity3d.com/key-image/0fa61edd-360f-48ea-8f80-0153559966f0.jpg>.
The board's terrain follows a cozy 16-bit farm tileset in spirit: rich, but never shiny.

- **Not glossy.** No rim highlights, no specular dots, no gradients. An earlier pass that lit every
  shape's upper-left edge was rejected as "too shiny and glossy".
- **Not blobby.** Silhouettes are clean and deliberate: readable heads, hands and weapons, not
  smoothed lumps. Doubling a 16×16 grid with EPX was rejected for this.
- **Muted, mid-value colours.** Earthy, slightly greyed. Avoid pure white, pure black and fully
  saturated primaries. A colour reads as "red" at `#a83030`, not `#ff0000`.
- **Dark outlines.** Near black, tinted by whatever they wrap (`flat32()` does this).
- **Chunky, chibi proportions.** Heads are large (7–8 px wide) so faces read at board size; bodies
  are compact, weapons and props oversized enough to read at 64×64 on screen.

## Canvas and shading

- **32×32 per sprite, facing right.** Enemies are mirrored in battle, so everything is drawn
  facing right.
- **Feet on rows 29–30.** Leave at least one empty pixel on every edge for the outline.
- **Height:**
  - Humanoids stand about 24–30 px tall.
  - Small creatures (slimes, bats, imps) sit lower, about 12–20 px.
  - Big things fill the canvas.
  - Bosses are drawn at 32×32 like everything else, then scaled up in battle by `FOES[id].scale`.
    So they need chunky detail that survives the scaling.
- **Draw flat colour regions only.** Don't draw the outline or the shading yourself. `flat32()` in
  `art.js` does it:
  - a 1px outline around the outside, 86% toward `#181028` from the colour it wraps;
  - a 2px darker band (32% toward `#181028`) where a colour ends to the lower right, which also
    separates neighbouring colours;
  - a faint lighter edge (8% toward warm white) where a colour starts upper left.
- **Use two tones per material at most:** a base, plus a darker variant for folds, insides and
  backs. The automatic band supplies the rest of the form.
- **Letters `e` and `o` are never shaded.** Use them for eyes and fine dark lines.

## Shared palette

| Material | Colours |
|---|---|
| Skin | `#e0b48a`, shadowed `#a8785a` (darker skin `#d8a880` / `#a07658`) |
| Eyes | `#1a1420`; glowing eyes are a single bright pixel (red `#ff4040`, cyan `#7fe3ff`, gold `#ffe14d`) |
| Steel | `#a8b0bc` / `#7a8494`; blade `#dfe6ee` |
| Gold trim | `#c8a040` / `#d0a840` |
| Wood | `#6a4a2e`, dark `#5a3a24` |
| Bone | `#d8d0c0` / `#b8b0a0` |
| Cloth | Muted: purple `#5b3a8a`, blue `#3a5aa8`, red `#a83030`, teal `#2a6a6a`, green `#4a5a3a` |
| Goblinoid skin | `#6a9a4a` / `#4a7a34` |

Use magic colours sparingly, as small glowing accents rather than large areas:
- fire `#ff7a1a` / `#ffd23f`
- frost `#7fe3ff`
- poison `#8be04e`
- hex `#e070c0`

## Faces

- **Eyes:** two dark pixels three apart (for example x 12 and x 15), on a face 6–8 px wide.
- **Brow shadow:** the row under a hat brim or hood uses the shadowed skin tone.
- **Mouths and beards:** a moustache or mouth is a short dark or hair-coloured line; beards are
  their own colour region.
- **Hooded and masked faces:** a dark inner region (`#1e1418`-ish) with only the eyes, or a single
  glowing pixel per eye.

## The heroes (chosen by the owner)

All 21 were picked from four options each. Their drawing code is in `tools/threefold-art/`:
- base classes: `warrior.py`, `mage.py`, `rogue.py`;
- first tier: `promos.py`, whose `knight()`, `wizard()` and `bandit()` are the base looks every
  promotion builds on;
- masters: `masters.py`.

A promoted hero keeps their base silhouette so they still look like themselves.

| Class | Look |
|---|---|
| **Warrior** | Knight: closed great helm with a slit visor and a red plume, steel plate, blue tabard with a gold cross, red kite shield with a gold cross, longsword raised in the right hand. |
| Blademaster | The knight in black-and-gold plate with a gold plume and gold tabard; longsword raised, parrying dagger low in the left hand. No shield. |
| Juggernaut | The knight crouched behind a huge grey rectangular shield with a gold cross; only the plumed helm, a war hammer and the boots show. |
| Samurai | Dark armour with a gold tabard, a wide straw jingasa hat, the face showing, hand resting on a sheathed katana worn across the hips. |
| Dragoon | The knight in red plate with gold trim, a spiked dragon-crest helm and a tall lance held upright. No shield. |
| Hoplite | Bronze armour and Corinthian helm with a transverse red crest, a large round bronze shield in front, spear raised. |
| Briar Knight | Grey-green armour, a helm sprouting antler-like branches, a bark shield of vertical planks, a thorn-studded mace. |
| **Mage** | Slim classic wizard: tall purple pointed hat with a bent tip and gold band, long white beard, purple robe with a gold-trimmed centre panel and hem, brown belt, wooden staff topped with a cyan crystal. |
| Pyromancer | The wizard in red, with a flame burning at the top of the staff. |
| Chronomancer | The wizard in teal, a robe dotted with gold stars, a crescent-moon staff. |
| Stormcaller | The wizard in blue with pale trim; a small grey thundercloud sits on top of the staff, with sparks. |
| Warlock | The wizard in black-violet with crimson trim, a horned hat, a grey beard and a skull-topped staff. |
| Arithmetician | The teal wizard without a staff: black scholar's cap with a gold tassel, gold spectacles, holding a scroll. |
| Oracle | Teal robes, a tall gold headdress framing a shadowed face, no beard, a glowing purple orb held in the hand. |
| **Rogue** | Bandit: blue bandana with a trailing knot, moustache, cream shirt under a brown open vest, green half-cape over the left shoulder, curved dagger in the right hand. |
| Assassin | The bandit in black: black bandana and leathers, a red scarf, a punch-blade (katar) in the right hand. |
| Trickster | The bandit with a teal bandana, a dark domino mask, a pink cape, juggling knives overhead. |
| Ninja | The assassin fully masked in a violet hood, a katana slung behind the body with only the hilt over the shoulder and the tip by the hip showing. |
| Plaguebringer | The assassin in a mossy green hood with a grey gas mask with green lenses, wisps of green fumes. |
| Bard | The trickster with a teal feathered cap, the mask, the pink cape and a wooden lute. |
| Mesmer | The trickster in violet and black: dark bandana with a pink feather, a long purple cape, a pendulum with a lilac gem swinging from the hand. |

## Monsters

Monsters follow the same rules. All 55 were drawn in one pass from this doc and are in
`tools/threefold-art/monsters.py`. The owner reviews them in game and asks for changes one by one.
The Dark Knight is `knight_dark()` there, and its art key is `knight`.

- **One clear idea each.** The silhouette should say what it does: a bomb for exploders, a shield
  for rampart bearers, a lens or mirror for reflectors, roots and legs for things that can't move.
- **Use the act's palette:**
  - Greenwood: greens and browns.
  - Marsh: murky teal and olive.
  - Crypt: bone, slate and violet.
  - Rime Halls: pale blue and white.
  - Ember Peaks: charcoal with fire accents.
  - Foundry: brass, iron and cyan.
- **Variants of a creature** (Snow Wolf from Wolf, Ice Golem from Golem) can be the same drawing
  with a new palette, plus one distinguishing detail.

## Adding or changing a sprite

1. Draw it in the right file under `tools/threefold-art/` with the kit (`G.rect`, `rows`, `ell`,
   `line`, `tri`, `text`). Preview it with `python3 monsheet.py out.png name ...` for monsters, or
   `sheet.py` for the hero batches.
2. Point its art key at the drawing in `picks.py`. New enemies also go in `monsters.KEYS`.
3. Run `python3 build.py`, which regenerates `app/static/games/threefold/js/sprites.js`. Never edit
   that file by hand.
4. Bump the game's `?v=`, check it in a browser, and commit the Python and `sprites.js` together.
