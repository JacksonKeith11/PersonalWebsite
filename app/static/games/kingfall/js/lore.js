// Words for the big moments: each boss's title on its name card as it enters, a line for each phase
// after the first, and an epitaph when it falls. Kept in the browser; the server never needs them.
export const LORE = {
  corvin: { title: 'Who broke his oath to guard the gate', phases: { 2: 'The oathless blade catches fire' }, fall: 'His oath is kept at last' },
  mire: { title: 'Queen of the drowned fen', phases: { 2: 'She sinks into the mire' }, fall: 'The bog grows still' },
  bellwarden: { title: 'Keeper of the cracked bell', phases: { 2: 'The bell tolls three times' }, fall: 'The bell is silent' },
  headsmen: { title: 'The Hook and the Axe', phases: {}, fall: 'The yard is empty' },
  wolf: { title: 'Hunger of the thorn wood', phases: { 2: 'The forest goes dark' }, fall: 'The thorns wither' },
  alchemist: { title: 'Who boiled the king’s physic', phases: { 2: 'The floor turns to poison' }, fall: 'The furnace goes cold' },
  wyrm: { title: 'What gnaws beneath the boneyard', phases: { 2: 'It burrows deeper' }, fall: 'The bones lie down' },
  mirror: { title: 'Your own blade, turned', phases: { 2: 'The mirrors shatter' }, fall: 'Only glass remains' },
  bastion: { title: 'The wall that walked', phases: { 2: 'The furnace roars' }, fall: 'The siege is broken' },
  moth: { title: 'Saint of the last candle', phases: { 2: 'The candles are snuffed' }, fall: 'The dust settles' },
  king: { title: 'Who wore the crown too long', phases: { 2: 'The crown swells him hollow', 3: 'The roof gives way' }, fall: 'Long live no one' },
  drake: { title: 'The sun’s black shadow', phases: { 2: 'It takes to the sky', 3: 'The bridge burns' }, fall: 'The eclipse passes' },
};
export const ROMAN = ['', 'I', 'II', 'III', 'IV'];
