"""Words and questions for Board Brawl's minigames: trivia, draw-and-guess, potion math."""

import random

# (question, right answer, three wrong answers)
TRIVIA = [
    ("Which country did Halloween's jack-o'-lanterns start in, carved from turnips?", "Ireland", "Mexico", "Germany", "Romania"),
    ("What was Frankenstein's first name in Mary Shelley's novel?", "Victor", "Henry", "Igor", "Boris"),
    ("Which vampire lives in Transylvania in Bram Stoker's novel?", "Count Dracula", "Count Orlok", "Lestat", "Nosferatu"),
    ("How many legs does a spider have?", "8", "6", "10", "12"),
    ("Which planet has the most known moons?", "Saturn", "Jupiter", "Neptune", "Mars"),
    ("What's the name of the ghost-busting company's car in Ghostbusters?", "Ecto-1", "Spook-1", "The Phantom", "Slimer"),
    ("Which famous escape artist died on Halloween?", "Harry Houdini", "David Copperfield", "Penn Jillette", "Harry Blackstone"),
    ("What colour is a polar bear's skin?", "Black", "White", "Pink", "Grey"),
    ("In Hocus Pocus, how many Sanderson sisters are there?", "3", "2", "4", "5"),
    ("What's a group of crows called?", "A murder", "A parliament", "A gaggle", "A coven"),
    ("Which fear is the fear of spiders?", "Arachnophobia", "Claustrophobia", "Acrophobia", "Coulrophobia"),
    ("What does a werewolf turn into?", "A wolf", "A bat", "A cat", "A raven"),
    ("What is the largest organ of the human body?", "Skin", "Liver", "Brain", "Lungs"),
    ("Which candy did Elliott use to lure E.T.?", "Reese's Pieces", "M&M's", "Skittles", "Jelly beans"),
    ("Which country gave the US the Statue of Liberty?", "France", "England", "Spain", "Italy"),
    ("How many bones are in an adult human body?", "206", "186", "226", "306"),
    ("Who directed The Nightmare Before Christmas?", "Henry Selick", "Tim Burton", "Wes Anderson", "Guillermo del Toro"),
    ("What's the Pumpkin King called in The Nightmare Before Christmas?", "Jack Skellington", "Oogie Boogie", "Sally", "Zero"),
    ("Which metal is said to kill werewolves?", "Silver", "Iron", "Gold", "Copper"),
    ("What is the chemical symbol for gold?", "Au", "Ag", "Go", "Gd"),
    ("Which game features the ghosts Blinky, Pinky, Inky and Clyde?", "Pac-Man", "Galaga", "Dig Dug", "Frogger"),
    ("Which Mario character lives in a haunted mansion?", "King Boo", "Bowser", "Wario", "Kamek"),
    ("What's the main ingredient in guacamole?", "Avocado", "Lime", "Pea", "Tomatillo"),
    ("What is the fastest land animal?", "Cheetah", "Pronghorn", "Lion", "Greyhound"),
    ("Which ocean is the largest?", "Pacific", "Atlantic", "Indian", "Arctic"),
    ("What's the scariest-named fish: one that lives in the deep and lights its own lure?", "Anglerfish", "Viperfish", "Gulper eel", "Lanternfish"),
    ("Who wrote 'The Raven'?", "Edgar Allan Poe", "H. P. Lovecraft", "Stephen King", "Washington Irving"),
    ("Who wrote 'The Legend of Sleepy Hollow'?", "Washington Irving", "Edgar Allan Poe", "Mark Twain", "Nathaniel Hawthorne"),
    ("What does the headless horseman throw at Ichabod Crane?", "A pumpkin", "His head", "A lantern", "A skull"),
    ("How many hearts does an octopus have?", "3", "1", "2", "8"),
    ("In which year did the Titanic sink?", "1912", "1905", "1921", "1898"),
    ("Which band sang 'Thriller'... wait, who sang it?", "Michael Jackson", "Prince", "Madonna", "Lionel Richie"),
    ("What is the only mammal that can truly fly?", "The bat", "The flying squirrel", "The sugar glider", "The colugo"),
    ("Which vegetable is a Halloween lantern usually carved from today?", "Pumpkin", "Squash", "Turnip", "Melon"),
    ("Which zombie film is set in a shopping mall?", "Dawn of the Dead", "28 Days Later", "Shaun of the Dead", "World War Z"),
    ("What's the capital of Australia?", "Canberra", "Sydney", "Melbourne", "Perth"),
    ("Which element has the symbol Fe?", "Iron", "Fluorine", "Lead", "Francium"),
    ("How many players are on a soccer team on the field?", "11", "10", "9", "12"),
    ("What colour do you get mixing blue and yellow?", "Green", "Purple", "Orange", "Brown"),
    ("Which monster is stitched together from body parts?", "Frankenstein's monster", "The Mummy", "The Wolf Man", "The Creature"),
    ("What's the name of the clown in Stephen King's It?", "Pennywise", "Twisty", "Captain Spaulding", "Art"),
    ("Which planet is known as the Red Planet?", "Mars", "Venus", "Jupiter", "Mercury"),
    ("What is a baby bat called?", "A pup", "A kit", "A cub", "A batling"),
    ("How many minutes are in a day?", "1440", "1240", "1600", "1080"),
    ("Which instrument has 88 keys?", "Piano", "Organ", "Accordion", "Harpsichord"),
    ("In Minecraft, which green mob explodes?", "Creeper", "Zombie", "Slime", "Enderman"),
    ("What's the longest river in the world (by most measures)?", "The Nile", "The Amazon", "The Yangtze", "The Mississippi"),
    ("Which candy is shaped like a tiny ear of corn?", "Candy corn", "Circus peanuts", "Smarties", "Dots"),
    ("In what month is the Mexican Día de los Muertos?", "November", "October", "December", "September"),
    ("Which animal is a witch's classic companion?", "Black cat", "Owl", "Toad", "Raven"),
]

WORDS = [
    "ghost", "pumpkin", "witch", "vampire", "skeleton", "bat", "spider", "zombie", "mummy", "cauldron",
    "broom", "candy", "haunted house", "graveyard", "moon", "owl", "black cat", "coffin", "werewolf", "spiderweb",
    "candle", "scarecrow", "bone", "eyeball", "monster", "potion", "wizard", "dragon", "castle", "tombstone",
    "lantern", "crow", "frankenstein", "costume", "mask", "pirate", "robot", "alien", "ufo", "shark",
    "volcano", "pizza", "rocket", "snowman", "guitar", "toilet", "dinosaur", "octopus", "unicorn", "hot dog",
    "rainbow", "bicycle", "tornado", "banana", "cactus", "penguin", "teapot", "crown", "dice", "treasure",
]


def trivia(n):
    picks = random.sample(TRIVIA, n)
    out = []
    for q, right, *wrong in picks:
        opts = [right, *wrong]
        random.shuffle(opts)
        out.append({"q": q, "opts": opts, "a": opts.index(right)})
    return out


def word():
    return random.choice(WORDS)


def sums(n):
    """Potion math: n sums that get a bit harder."""
    out = []
    for i in range(n):
        kind = random.choice(["+", "-", "×"] if i >= 2 else ["+", "-"])
        if kind == "+":
            a, b = random.randint(3, 20 + i * 6), random.randint(3, 20 + i * 6)
            out.append([f"{a} + {b}", a + b])
        elif kind == "-":
            a = random.randint(10, 30 + i * 6)
            b = random.randint(2, a - 1)
            out.append([f"{a} − {b}", a - b])
        else:
            a, b = random.randint(2, 6 + i), random.randint(2, 9)
            out.append([f"{a} × {b}", a * b])
    return out
