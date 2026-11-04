// Item icons: a small pixel picture for every item, drawn in code like the place icons (art.js). An
// icon is a base shape (a 12×12 grid of letters) painted in a material, with an accent and a glow,
// then outlined. Many items share a shape in different materials, so a new item usually needs only
// a line in ICON. Rarity isn't in the picture: the UI frames it.
//   m main  n main, dark  l main, light   w wood/grip  x wood, dark   a accent  b accent, dark  g glow

const K = '#1b1226';
const DIR4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const urls = {};

const MAT = {
  steel: ['#a8b0bc', '#6a7484', '#dfe6ee'], iron: ['#7a7a82', '#4e4e58', '#a0a0a8'], gold: ['#c8a040', '#8a6a24', '#ecd27a'],
  bronze: ['#b07a3a', '#7a5226', '#d6a060'], wood: ['#8a6a44', '#5a4028', '#a8875a'], drift: ['#a89a80', '#7a6e5a', '#c8bca0'],
  coral: ['#d0786a', '#9a4e48', '#eca092'], bone: ['#d8d0c0', '#a8a090', '#efe8da'], leather: ['#8a5a3a', '#5e3a24', '#a8784e'],
  blue: ['#4a6aa8', '#2e4478', '#7090c8'], red: ['#a84040', '#742a2a', '#c86a5a'], white: ['#d8d4c8', '#a8a498', '#f0ece0'],
  green: ['#4a7a50', '#2e5236', '#6a9a6a'], grey: ['#7a8088', '#50565e', '#9aa0a8'], kelp: ['#4a8050', '#2a5a34', '#7ab070'],
  pearl: ['#e8e4f0', '#a8a0b8', '#ffffff'], black: ['#3a3a4a', '#20202c', '#6a6a80'], glass: ['#8ad0d8', '#4a8a98', '#d0f4f8'],
  ember: ['#e07030', '#9a3a1a', '#ffc060'], frost: ['#9ad0f0', '#5a8ab0', '#e0f4ff'], abyss: ['#4a3a6a', '#2a1e44', '#7a62a0'],
  shark: ['#7a8a98', '#4e5a68', '#a8b4c0'], cork: ['#b89060', '#86643e', '#d4b080'], whale: ['#8a9ab0', '#5a6a80', '#c0ccd8'],
  blood: ['#b03040', '#701a26', '#e06070'], tan: ['#b8a078', '#8a7452', '#d4bc94'], purple: ['#7a4a8a', '#52305e', '#a070b0'],
  // the other regions' materials
  obsidian: ['#3a3048', '#1e1828', '#6a5a88'], magma: ['#d8502a', '#8a2a14', '#ffb050'], sand: ['#d8b878', '#a88a50', '#f0dca8'],
  stone: ['#8a8478', '#5e594e', '#b0aa9c'], amber: ['#d8902a', '#9a5e14', '#f8c060'], jade: ['#3a9a6a', '#1e6a46', '#7ad0a0'],
  holy: ['#f0e8d0', '#c8b890', '#ffffff'], crystal: ['#c890e8', '#8a58b0', '#f0d0ff'], dream: ['#8a78c8', '#5a4a90', '#c0b0f0'],
  ice: ['#c0e8f8', '#80b8d8', '#ffffff'], fur: ['#d8d0c4', '#a49a8c', '#f4f0e8'],
};
const WOOD = ['#8a6a44', '#5a4028'];

const SHAPE = {
  axe: ['........nn..', '.......nmmn.', '......nmmmmn', '.....wnmlmmn', '....wx.nmmn.', '...wx...nn..', '..wx........', '.wx.........', 'wx..........'],
  bigaxe: ['......nnnn..', '.....nmmmmn.', '....nmmlmmmn', '....nmmmmmmn', '...wxnmmmmn.', '..wx..nmmn..', '.wx...nnn...', 'wx..........', 'x...........'],
  sword: ['..........lm', '.........lmn', '........lmn.', '.......lmn..', '......lmn...', '..a..lmn....', '...almn.....', '....an......', '...waa......', '..wx..a.....', '.wx.........', 'b...........'],
  rapier: ['...........l', '..........l.', '.........m..', '........m...', '.......m....', '......m.....', '..aa.m......', '..a.a.......', '...wa.a.....', '..wx........', '.wx.........', 'b...........'],
  staff: ['........aa..', '.......abba.', '.......abga.', '........aa..', '.......w....', '......wx....', '.....wx.....', '....wx......', '...wx.......', '..wx........', '.wx.........', 'wx..........'],
  fork: ['......w..w..', '......w..w..', '.......ww...', '.......w....', '......wx....', '.....wx.....', '....wx......', '...wx.......', '..wx........', '.wx.........', 'wx..........'],
  lantern: ['....wwwwww..', '...wx.....a.', '..wx.....bab', '.wx......aga', 'wx.......bab', '..........a.'],
  bow: ['....ww......', '...wxl......', '..wx.l......', '.wx..l......', '.w...l......', '.w...l......', '.w...l......', '.wx..l......', '..wx.l......', '...wxl......', '....ww......'],
  daggers: ['l........l..', '.m......m...', '..m....m....', '...m..m.....', '....mm......', '....mm......', '...a..a.....', '..w....w....', '.x......x...'],
  knife: ['.........ll.', '........lmn.', '.......lmn..', '......lmn...', '.....lmn....', '....aa......', '...wx.......', '..wx........', '.xx.........'],
  lute: ['..........xx', '.........xw.', '........xw..', '..nnn..xw...', '.nmmmnxw....', 'nmmmmmn.....', 'nmmamnm.....', 'nmmmmmn.....', '.nmmmn......', '..nnn.......'],
  sling: ['..w.....w...', '..w.....w...', '...w...w....', '....a.a.....', '.....w......', '.....w......', '.....w......', '.....x......'],
  harpoon: ['.........lm.', '..........m.', '.......mmm..', '........w.m.', '.......wx...', '......wx....', '.....wx.....', '....wx......', '...wx.......', '..wx........', '.wx.........'],
  gun: ['............', 'nmmmmmmmn...', 'lllllllmn...', '......xwwn..', '......xww...', '.......xw...', '.......xww..', '........xw..'],
  hammer: ['...nnnnnn...', '..nmmmmmmn..', '..nmlmmmmn..', '..nmmmmmmn..', '...nnwwnn...', '.....wx.....', '.....wx.....', '.....wx.....', '.....wx.....', '.....xx.....'],
  wand: ['..........g.', '.........gag', '........wag.', '.......wx...', '......wx....', '.....wx.....', '....wx......', '...xx.......'],
  censer: ['.....aa.....', '.....a......', '.....a......', '....nnnn....', '...nmmmmn...', '...mgmgmm...', '...nmmmmn...', '....nnnn....'],
  tome: ['..nnnnnnnn..', '.nmmmmmmmmw.', '.nmmaammmmw.', '.nmaggammmw.', '.nmmaammmmw.', '.nmmmmmmmmw.', '.nmmmmmmmmw.', '.nnnnnnnnnw.', '..wwwwwwwww.'],
  vest: ['..nn....nn..', '.nmmn..nmmn.', '.nmmmnnmmmn.', '.nmmmaammmn.', '.nmmmaammmn.', '.nmmmmmmmmn.', '.nmmmmmmmmn.', '.nmmmmmmmmn.', '.nnnnnnnnnn.'],
  apron: ['...a....a...', '....a..a....', '...nmmmmn...', '...nmmmmn...', '.a.nmmmmn.a.', '..anmmmmna..', '..nmmmmmmn..', '..nmmaammn..', '..nmmmmmmn..', '..nmmmmmmn..', '..nnnnnnnn..'],
  coat: ['...nn..nn...', '..nmmnnmmn..', '.nmmmmammmn.', 'nmmmmmammmmn', 'nmnmmmammnmn', 'nmnmmmammnmn', '..nmmmammn..', '..nmmmammn..', '..nmmmammn..', '..nnnnnnnn..'],
  robe: ['....nnnn....', '...nmmmmn...', '..nmmmmmmn..', '.nmmmmmmmmn.', '.nmnmmmmnmn.', '..nmaaaamn..', '..nmmmmmmn..', '.nmmmmmmmmn.', '.nmmmmmmmmn.', 'nmmmmmmmmmmn', 'nnnnnnnnnnnn'],
  plate: ['..nnn..nnn..', '.nmmmnnmmmn.', 'nmllmmmmllmn', 'nmmmmmmmmmmn', 'nmmmmaammmmn', '.nmmmaammmn.', '.nmmmmmmmmn.', '..nmmmmmmn..', '...nnnnnn...'],
  cloak: ['....nnnn....', '...nmaamn...', '..nmmmmmmn..', '.nmmmmmmmmn.', '.nmmmmmmmmn.', 'nmmmmmmmmmmn', 'nmmmmmmmmmmn', 'nmnmmnnmmnmn', 'nn.nn..nn.nn'],
  helmet: ['...nnnnnn...', '..nmmmmmmn..', '.nmmaaaammn.', '.nmagggaamn.', '.nmaggggamn.', '.nmmaaaammn.', '..nmmmmmmn..', '.nnmmmmmmnn.', 'nmmmmmmmmmmn', 'nnnnnnnnnnnn'],
  shield: ['.nnnnnnnnnn.', 'nmmmmaammmmn', 'nmmmmaammmmn', 'nmaaaaaaaamn', 'nmmmmaammmmn', '.nmmmaammmn.', '.nmmmaammmn.', '..nmmaammn..', '...nmaamn...', '....nnnn....'],
  conch: ['........nn..', '......nnmmn.', '....nnmmmmn.', '..nnmmlmmmn.', '.nmmmmmmmn..', 'nmmalmmmn...', 'nmmaammn....', '.nmmmnn.....', '..nnn.......'],
  shell: ['....nnnn....', '..nnmmmmnn..', '.nmlnmnmlmn.', 'nmmnmmmnmmmn', 'nmnmmnmmnmmn', '.nmmnmmnmmn.', '..nnmmmmnn..', '....nmmn....', '.....nn.....'],
  compass: ['....nnnn....', '..nnmmmmnn..', '.nmllllllmn.', '.nmllaalllmn', 'nmllllalllmn', 'nmlllblllmn.', '.nmllbllmn..', '..nnmmmmnn..', '....nnnn....'],
  tooth: ['.nnnnnnnn...', '.nmmlmmmmn..', '..nmlmmmn...', '..nmmmmmn...', '...nmmmn....', '...nmmmn....', '....nmn.....', '....nmn.....', '.....n......'],
  bone: ['.nn......nn.', 'nmmn....nmmn', 'nmmmnnnnmmmn', '.nnmmmmmmnn.', '..nmmmmmmn..', '.nnmmmmmmnn.', 'nmmmnnnnmmmn', 'nmmn....nmmn', '.nn......nn.'],
  orb: ['....nnnn....', '..nnmmmmnn..', '.nmllmmmmmn.', '.nmlmmmmmmn.', 'nmmmmmmmmmmn', 'nmmmmmmmmmmn', '.nmmmmmmmnn.', '..nnmmmmn...', '....nnnn....'],
  globe: ['....nnnn....', '..nnggggnn..', '.ngglgggggn.', '.nglgaaggg n', 'ngggaagggggn', 'nggggggggggn', '.ngggggggnn.', '..nnggggn...', '...wwwwww...', '..wxxxxxxw..'],
  idol: ['....nnnn....', '...nmmmmn...', '...ngmmgn...', '...nmmmmn...', '....nmmn....', '..nnmmmmnn..', '.nmmmmmmmmn.', '.nmnmmmmnmn.', '..nnmmmmnn..', '...nmmmmn...', '..nnnnnnnn..'],
  dice: ['nnnnnn......', 'nlllln......', 'nlnlln.nnnnn', 'nllnln.nmmmn', 'nlllln.nmnmn', 'nnnnnn.nmmmn', '.......nnmnn', '.......nmmmn', '.......nnnnn'],
  locket: ['.....aa.....', '....a..a....', '.....aa.....', '....nnnn....', '...nmmmmn...', '..nmmllmmn..', '..nmlggmmn..', '..nmmmmmmn..', '...nmmmmn...', '....nnnn....'],
  hourglass: ['nnnnnnnnnnnn', '.w.nmmmmn.w.', '.w..nggn..w.', '.w...gg...w.', '.w...nn...w.', '.w..n..n..w.', '.w.n.gg.n.w.', '.w.nggggn.w.', 'nnnnnnnnnnnn'],
  heart: ['.nnn...nnn..', 'nmmmn.nmmmn.', 'nmllmnmmmmmn', 'nmlmmmmmmmmn', 'nmmmmmmmmmmn', '.nmmmmmmmmn.', '..nmmmmmmn..', '...nmmmmn...', '....nmmn....', '.....nn.....'],
  gem: ['...nnnnnn...', '..nllmmmmn..', '.nllmmmmmmn.', 'nnnnnnnnnnnn', '.nmmmmmmmmn.', '..nmmmmmmn..', '...nmmmmn...', '....nmmn....', '.....nn.....'],
  coin: ['....nnnn....', '..nnmmmmnn..', '.nmmllllmmn.', '.nmlmmmmmmn.', 'nmmlmmaammmn', 'nmmmmaammmmn', '.nmmmmmmmmn.', '..nnmmmmnn..', '....nnnn....'],
  medal: ['...aabbaa...', '...aabbaa...', '....abba....', '.....bb.....', '....nnnn....', '...nmmmmn...', '..nmmllmmn..', '..nmlmmmmn..', '...nmmmmn...', '....nnnn....'],
  whistle: ['............', '.nnnnnnnn...', 'nmmmmmmmmnn.', 'nmllllmmmmmn', 'nmmmmmmmmmmn', '.nnnnnnnmmn.', '.......nmmn.', '.......nnnn.', '..aa........', '.a..a.......'],
  bell: ['.....aa.....', '.....nn.....', '....nmmn....', '...nmlmmn...', '...nmlmmn...', '..nmmmmmmn..', '..nmmmmmmn..', '.nmmmmmmmmn.', 'nnnnnnnnnnnn', '.....nn.....'],
  lens: ['....nnnn....', '..nnggggnn..', '.ngglggggn..', '.nglggggggn.', '.ngggggggn..', '..nnggggnnw.', '....nnnn.wx.', '.........wx.', '..........wx'],
  spyglass: ['..........nn', '........nnmn', '......nnmmn.', '....nnmmmn..', '..nnamlmn...', 'nnmmamnn....', 'nmmmann.....', 'nmmnn.......', '.nn.........'],
  ring: ['....aaaa....', '...aggga....', '....aaaa....', '..nnnnnnnn..', '.nmmn..nmmn.', 'nmmn....nmmn', 'nmmn....nmmn', '.nmmn..nmmn.', '..nnnnnnnn..'],
  flask: ['....nnnn....', '....ammn....', '....nnnn....', '....nggn....', '...nggggn...', '..nggggggn..', '.nggllgggn..', '.nggggggggn.', '.nggggggggn.', '..nnnnnnnn..'],
  bottle: ['.....nn.....', '.....aa.....', '.....nn.....', '....nmmn....', '...nmmmmn...', '...nmlmmn...', '...nmaamn...', '...nmaamn...', '...nmmmmn...', '...nnnnnn...'],
  anchor: ['....nnnn....', '....n..n....', '....nnnn....', '.....nn.....', '..nnnmmnnn..', '.....mm.....', 'nn...mm...nn', 'nmn..mm..nmn', '.nmmmmmmmmn.', '..nnnnnnnn..'],
  keg: ['...nnnnnn...', '..nmmmmmmn..', '.aaaaaaaaaa.', '.nmmmmmmmmn.', '.nmmmmmmmmn.', '.aaaaaaaaaa.', '..nmmmmmmn..', '...nnnnnn...', '.....gg.....', '......g.....'],
  scroll: ['.nnnnnnnnnn.', 'nwmmmmmmmmwn', 'nwmaaaammmwn', 'nwmmmmmmmmwn', 'nwmaaammmmwn', 'nwmmmmmmmmwn', 'nwmaaaaammwn', 'nwmmmmmmmmwn', '.nnnnnnnnnn.'],
  jar: ['...nnnnnn...', '...naaaan...', '....nnnn....', '...nmmmmn...', '..nmlgggmn..', '..nmggggmn..', '..nmggggmn..', '..nmmmmmmn..', '...nnnnnn...'],
  // the other regions' shapes
  spear: ['...........l', '..........lm', '.........lmn', '........ww..', '.......wx...', '......wx....', '.....wx.....', '....wx......', '...wx.......', '..wx........', '.wx.........', 'wx..........'],
  glaive: ['........nnl.', '.......nmmml', '........nmml', '.........wn.', '........wx..', '.......wx...', '......wx....', '.....wx.....', '....wx......', '...wx.......', '..wx........', '.wx.........'],
  khopesh: ['......nnn...', '.....nmmmn..', '....nm..mln.', '........mln.', '.......mln..', '......mln...', '.....mln....', '...aamn.....', '...wa.......', '..wx........', '.wx.........', 'b...........'],
  club: ['.......nnn..', '......nmmmn.', '......nmlmn.', '.....nmmmmn.', '.....nmmmn..', '....wnnnn...', '...wx.......', '..wx........', '.wx.........', 'wx..........'],
  pick: ['....nnnnn...', '...nmmmmmn..', '..nm..w..mn.', '.n....w...n.', '......wx....', '......wx....', '......wx....', '......wx....', '......wx....', '......xx....'],
  feather: ['.........ll.', '........lmml', '.......lmmmn', '......lmmmn.', '.....lmmmn..', '....lmmmn...', '...lmmmn....', '...mmmn.....', '..nmn.......', '.n..........', 'n...........'],
  pouch: ['....aaaa....', '.....aa.....', '...nnnnnn...', '..nmmmmmmn..', '.nmmmlmmmmn.', '.nmlmmmmmmn.', '.nmmmmmmmmn.', '.nmmmmmmmmn.', '..nnnnnnnn..'],
  frog: ['..nn....nn..', '.nlgn..nlgn.', '.nmmnnnnmmn.', 'nmmmmmmmmmmn', 'nmmmmmmmmmmn', '.nmmaaaammn.', '..nmmmmmmn..', '.nmn....nmn.', 'nn........nn'],
  disc: ['....aaaa....', '..aannnnaa..', '.anmmllmmna.', '.nmlmmmmmmn.', 'anmmmggmmmna', 'anmmmggmmmna', '.nmmmmmmmmn.', '.anmmmmmmna.', '..aannnnaa..', '....aaaa....'],
  box: ['..nnnnnnnn..', '.nmmmmmmmmn.', 'nnnnnnnnnnnn', 'nmmmmaammmmn', 'nmmmaggammmn', 'nmmmmaammmmn', 'nmmmmmmmmmmn', 'nnnnnnnnnnnn', '.w........w.'],
  pelt: ['.nn......nn.', 'nmmn....nmmn', 'nmmmnnnnmmmn', '.nmmmmmmmmn.', '..nmmllmmn..', '..nmmmmmmn..', '..nmmmmmmn..', '.nmmmnnmmmn.', 'nmmn....nmmn', '.nn......nn.'],
  plume: ['......aa....', '.....aggb...', '....aggb....', '...aggb.....', '..aggb......', '..agb.......', '...b........', '..n.........', '.n..........', 'n...........'],
  ingot: ['............', '............', '...nnnnnnnn.', '..nllllllmn.', '.nmmmmmmmmn.', 'nmmmmmmmmn..', 'nnnnnnnnn...', '............'],
};

// item key -> [shape, material, accent, glow]
const ICON = {
  hand_axe: ['axe', 'steel'], great_axe: ['bigaxe', 'steel'], boarding_axe: ['axe', 'iron'],
  oak_staff: ['staff', 'wood', 'tan', 'gold'], gnarled_staff: ['staff', 'wood', 'kelp', 'kelp'], driftwood_staff: ['staff', 'drift', 'drift', 'glass'],
  storm_staff: ['staff', 'iron', 'blue', 'frost'], forked_staff: ['fork', 'wood'], leviathan_rod: ['lantern', 'abyss', 'abyss', 'glass'],
  lantern_rod: ['lantern', 'wood', 'bronze', 'ember'], reef_lantern: ['lantern', 'coral', 'coral', 'glass'],
  rapier: ['rapier', 'steel', 'gold'], coral_blade: ['sword', 'coral', 'bronze'], captains_sabre: ['sword', 'steel', 'gold'],
  ember_blade: ['sword', 'ember', 'iron'], heirloom_sword: ['sword', 'gold', 'blue'], crownbreaker: ['sword', 'abyss', 'gold'],
  short_bow: ['bow', 'wood'], gull_bow: ['bow', 'white'], daggers: ['daggers', 'steel'], gutting_knife: ['knife', 'steel', 'leather'],
  lute: ['lute', 'wood'], sling: ['sling', 'leather', 'tan'], rusty_harpoon: ['harpoon', 'bronze'], harpoon_gun: ['gun', 'iron'],
  flintlock: ['gun', 'steel'], tide_hammer: ['hammer', 'whale'], shellbreaker: ['hammer', 'iron'], kelp_wand: ['wand', 'kelp', 'green', 'kelp'],
  chaplain_censer: ['censer', 'gold', 'gold', 'ember'], abyssal_tome: ['tome', 'abyss', 'gold', 'glass'],
  hide_vest: ['vest', 'leather', 'tan'], cork_vest: ['vest', 'cork', 'red'], sharkskin: ['vest', 'shark', 'white'],
  leather_apron: ['apron', 'leather', 'tan'], nurses_apron: ['apron', 'white', 'red'], padded_coat: ['coat', 'tan', 'bronze'],
  oilskin_coat: ['coat', 'gold', 'leather'], wool_robe: ['robe', 'blue', 'tan'], kelpweave_robe: ['robe', 'kelp', 'bronze'],
  mistweave: ['robe', 'grey', 'white'], pilgrim_shawl: ['cloak', 'tan', 'red'], smugglers_cloak: ['cloak', 'black', 'gold'],
  coral_mail: ['plate', 'coral', 'bronze'], whaleplate: ['plate', 'whale', 'bone'], barnacle_plate: ['plate', 'iron', 'drift'],
  gilded_cuirass: ['plate', 'gold', 'red'], tidelord_aegis: ['shield', 'whale', 'gold'], divers_harness: ['helmet', 'bronze', 'iron', 'glass'],
  siren_conch: ['conch', 'pearl', 'coral'],
  lucky_shell: ['shell', 'coral'], brass_compass: ['compass', 'bronze', 'red'], shark_tooth: ['tooth', 'bone'], gull_bone: ['bone', 'bone'],
  pearl_charm: ['orb', 'pearl'], black_pearl: ['orb', 'black'], storm_glass: ['globe', 'iron', 'white', 'frost'], drowned_idol: ['idol', 'kelp', 'kelp', 'glass'],
  gamblers_bones: ['dice', 'bone'], frost_locket: ['locket', 'frost', 'steel', 'frost'], salt_locket: ['locket', 'drift', 'iron', 'white'],
  tide_hourglass: ['hourglass', 'gold', 'gold', 'glass'], powder_heart: ['heart', 'ember'], bloodstone: ['gem', 'blood'], ember_charm: ['gem', 'ember'],
  weighted_coin: ['coin', 'gold', 'bronze'], captains_medal: ['medal', 'gold', 'red'], bosuns_whistle: ['whistle', 'bronze', 'tan'], bosuns_bell: ['bell', 'bronze', 'leather'],
  sea_glass_lens: ['lens', 'iron', 'iron', 'glass'], spyglass: ['spyglass', 'bronze', 'leather'], tarnished_ring: ['ring', 'iron', 'iron', 'kelp'],
  rum_flask: ['bottle', 'leather', 'tan'], anchor_pendant: ['anchor', 'iron'],
  potion: ['flask', 'grey', 'red', 'kelp'], big_potion: ['bottle', 'green', 'tan'], bomb: ['keg', 'wood', 'iron', 'ember'], ward_scroll: ['scroll', 'tan', 'blue'],
  smelling_salts: ['jar', 'glass', 'leather', 'white'],
  powder_salt: ['jar', 'iron', 'ember', 'ember'], still_pearl: ['orb', 'pearl', 'gold'], seer_glass: ['globe', 'glass', 'gold', 'glass'],
  // Cinderreach
  obsidian_cleaver: ['axe', 'obsidian', 'magma', 'magma'], magma_maul: ['hammer', 'magma', 'obsidian'], ashen_wand: ['wand', 'grey', 'magma', 'ember'],
  slagplate: ['plate', 'obsidian', 'magma'], salamander_scale: ['vest', 'magma', 'amber'], cinder_heart: ['heart', 'magma', 'obsidian'],
  // the Shifting Sands
  khopesh: ['khopesh', 'bronze', 'gold'], sandstorm_staff: ['staff', 'sand', 'gold', 'sand'], scarab_bow: ['bow', 'sand'],
  nomad_wraps: ['robe', 'sand', 'blue'], sphinx_mantle: ['cloak', 'gold', 'blue'], scarab_amulet: ['locket', 'gold', 'jade', 'jade'],
  oasis_flask: ['bottle', 'sand', 'blue'],
  // the Stillwood
  petrified_club: ['club', 'stone'], gorgon_glaive: ['glaive', 'stone', 'jade'], amber_rod: ['staff', 'stone', 'amber', 'amber'],
  bark_of_ages: ['vest', 'stone', 'kelp'], sentinel_plate: ['shield', 'stone', 'amber'], amber_drop: ['gem', 'amber'], fossil_tooth: ['tooth', 'stone'],
  // the Verdant Deep
  machete: ['knife', 'steel', 'jade'], dart_blowpipe: ['harpoon', 'jade', 'kelp'], jade_spear: ['spear', 'jade'],
  vinewoven_mail: ['coat', 'kelp', 'jade'], jaguar_pelt: ['pelt', 'amber', 'black'], jade_frog: ['frog', 'jade', 'gold', 'amber'],
  // Aetherhold
  seraph_blade: ['sword', 'holy', 'gold'], sunlance: ['spear', 'gold', 'holy'], hymnal: ['tome', 'holy', 'gold', 'gold'],
  guardian_mantle: ['cloak', 'holy', 'gold'], vestment_of_light: ['robe', 'holy', 'gold'], angel_feather: ['feather', 'holy'],
  sun_disc: ['disc', 'gold', 'amber', 'holy'],
  // the Prism Wood
  prism_staff: ['staff', 'crystal', 'crystal', 'crystal'], crystal_shiv: ['knife', 'crystal', 'iron'], geode_hammer: ['hammer', 'crystal'],
  crystal_carapace: ['plate', 'crystal', 'glass'], prismweave_robe: ['robe', 'crystal', 'glass'], tuning_fork: ['fork', 'crystal'],
  prism_shard: ['gem', 'crystal'],
  // the Drowsing Vale
  dreamcatcher: ['staff', 'wood', 'dream', 'dream'], sleepwalker_knife: ['knife', 'dream', 'black'], moonsilk_robe: ['robe', 'dream', 'pearl'],
  nightmare_mail: ['plate', 'black', 'dream'], sandman_pouch: ['pouch', 'dream', 'gold'], music_box: ['box', 'wood', 'gold', 'dream'],
  // the Frostpeaks
  frostbrand: ['sword', 'ice', 'frost'], ice_pick: ['pick', 'ice'], yeti_hide: ['pelt', 'fur', 'frost'], glacier_plate: ['plate', 'ice', 'frost'],
  rime_amulet: ['locket', 'ice', 'steel', 'frost'], aurora_crystal: ['globe', 'iron', 'ice', 'crystal'],
  // relics
  phoenix_plume: ['plume', 'magma', 'magma', 'ember'], sunking_khopesh: ['khopesh', 'gold', 'sand'], stillwood_heart: ['shield', 'amber', 'stone'],
  jade_fang: ['spear', 'jade', 'gold'], arbiter_wings: ['feather', 'gold', 'holy'], heartprism: ['globe', 'crystal', 'gold', 'crystal'],
  somnarch_lantern: ['lantern', 'dream', 'gold', 'dream'], rimeheart: ['heart', 'ice'],
  // materials
  fate_feather: ['feather', 'dream'], starmetal: ['ingot', 'iron', 'gold'], wyrm_ember: ['orb', 'magma'],
};
const BY_SLOT = { weapon: ['sword', 'steel'], armor: ['vest', 'leather'], trinket: ['coin', 'gold'], use: ['flask', 'grey', 'red', 'kelp'] };

function canvasFor(rows, pal) {
  const S = 16, off = 2;
  const c = document.createElement('canvas');
  c.width = S; c.height = S;
  const x = c.getContext('2d');
  const at = (X, Y) => (Y < 0 || Y >= rows.length || X < 0 || X >= rows[Y].length ? '.' : rows[Y][X]);
  const top = Math.floor((12 - rows.length) / 2);
  for (let Y = -1; Y <= rows.length; Y++) for (let X = -1; X <= 12; X++) {
    const ch = at(X, Y);
    if (ch !== '.' && ch !== ' ' && pal[ch]) { x.fillStyle = pal[ch]; x.fillRect(X + off, Y + off + top, 1, 1); continue; }
    if (DIR4.some(([dx, dy]) => { const o = at(X + dx, Y + dy); return o !== '.' && o !== ' '; })) { x.fillStyle = K; x.fillRect(X + off, Y + off + top, 1, 1); }
  }
  return c;
}

export function itemURL(key, slot) {
  key = key.split('@')[0];  // worked gear looks like its catalogue item
  if (urls[key]) return urls[key];
  const [shape, mat, acc, glow] = ICON[key] || BY_SLOT[slot] || BY_SLOT.trinket;
  const m = MAT[mat] || MAT.steel, a = MAT[acc || 'gold'] || MAT.gold, g = MAT[glow || 'glass'] || MAT.glass;
  const pal = { m: m[0], n: m[1], l: m[2], w: WOOD[0], x: WOOD[1], a: a[0], b: a[1], g: g[0] };
  return (urls[key] = canvasFor(SHAPE[shape] || SHAPE.coin, pal).toDataURL());
}
