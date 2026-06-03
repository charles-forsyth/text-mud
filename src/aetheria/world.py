from typing import Dict, List, Optional
from aetheria.models import Item, deserialize_item, Equipment, EquipmentSlot, Consumable
from aetheria.entity import Enemy, Boss, deserialize_enemy


class NPC:
    def __init__(self, name: str, persona: str, dialogue_context: str = ""):
        self.name = name
        self.persona = persona
        self.dialogue_context = dialogue_context

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "persona": self.persona,
            "dialogue_context": self.dialogue_context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NPC":
        return cls(
            name=data["name"],
            persona=data["persona"],
            dialogue_context=data.get("dialogue_context", ""),
        )


class Room:
    def __init__(self, name: str, description: str, is_town: bool = False):
        self.name = name
        self.description = description
        self.is_town = is_town
        self.exits: Dict[str, Room] = {}
        self.items: List[Item] = []
        self.enemy: Optional[Enemy] = None
        self.npcs: List[NPC] = []
        self.locked: bool = False
        self.key_needed: Optional[Item] = None

    def add_exit(self, direction: str, room: "Room"):
        self.exits[direction] = room

    def get_exit(self, direction: str) -> Optional["Room"]:
        """Returns the Room linked in the given direction, or None if no exit exists."""
        return self.exits.get(direction.lower())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "is_town": self.is_town,
            "locked": self.locked,
            "key_needed": (self.key_needed.to_dict() if self.key_needed else None),
            "items": [item.to_dict() for item in self.items],
            "enemy": (self.enemy.to_dict() if self.enemy else None),
            "npcs": [npc.to_dict() for npc in self.npcs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        room = cls(
            name=data["name"],
            description=data["description"],
            is_town=data.get("is_town", False),
        )
        room.locked = data.get("locked", False)

        kn_data = data.get("key_needed")
        if kn_data:
            room.key_needed = deserialize_item(kn_data)

        room.items = [deserialize_item(i) for i in data.get("items", [])]

        enemy_data = data.get("enemy")
        if enemy_data:
            room.enemy = deserialize_enemy(enemy_data)

        room.npcs = [NPC.from_dict(n) for n in data.get("npcs", [])]
        return room


def build_default_world() -> Dict[str, Room]:
    """Assembles the entire default massive world map of towns and dungeons."""
    world: Dict[str, Room] = {}

    # ==================== TOWN #1: ELDERGROVE ====================
    eldergrove_center = Room(
        "Eldergrove Center",
        "A peaceful village square shaded by a gigantic golden oak. Wind chimes chime softly in the breeze.",
        is_town=True,
    )
    eldergrove_tavern = Room(
        "Eldergrove Tavern (The Golden Oak)",
        "A warm, rowdy tavern smelling of roasted pork and honey mead. Active travelers sit around the fireplace.",
        is_town=True,
    )
    eldergrove_blacksmith = Room(
        "Eldergrove Blacksmith (Iron & Ash)",
        "An open-air forge glowing with heat. Hammer blows ring out as weapons and steel armor are cooled in water.",
        is_town=True,
    )
    eldergrove_temple = Room(
        "Eldergrove Temple (Aether Sanctuary)",
        "A tranquil, quiet temple of soft white stone. Clerics offer restorative water to wounded travelers.",
        is_town=True,
    )

    # Setup Eldergrove Exits
    eldergrove_center.add_exit("north", eldergrove_tavern)
    eldergrove_center.add_exit("east", eldergrove_blacksmith)
    eldergrove_center.add_exit("west", eldergrove_temple)

    # Add NPCs to Eldergrove
    eldergrove_tavern.npcs.append(
        NPC(
            "Tavernkeeper Barnaby",
            "Barnaby is a jolly, stout dwarf with a massive braided beard. He has ran the Golden Oak for 30 years and knows all local rumors.",
            "Barnaby knows that Goblins have infested the Whisperwood forest to the south.",
        )
    )
    eldergrove_blacksmith.npcs.append(
        NPC(
            "Blacksmith Thorin",
            "Thorin is a stern, muscular elf who speaks in brief, gruff sentences. He values quality craftsmanship above all else.",
            "Thorin can sell you a Bronze Sword (+5 ATK, 40 Gold) or Leather Jerkin (+3 DEF, 30 Gold).",
        )
    )
    eldergrove_temple.npcs.append(
        NPC(
            "Priestess Althea",
            "Althea is a gentle young human woman wearing white robes. She radiates a serene, divine presence and heals the weary.",
            "Althea offers free advice and heals characters if they are hurt.",
        )
    )

    # ==================== DUNGEON #1: WHISPERWOOD ====================
    # Whisperwood is south of Eldergrove Center
    forest_entrance = Room(
        "Whisperwood Entrance",
        "The light dims as dense trees block the sun. Thick, twisting roots crawl across the mossy floor.",
    )
    goblin_outpost = Room(
        "Goblin Outpost",
        "A makeshift camp littered with wooden spikes and animal bones. A smelly campfire smokes in the center.",
    )
    whispering_glade = Room(
        "Whispering Glade",
        "A serene forest clearing where mystical light leaks through the canopy. Glowing blue herbs grow here.",
    )
    ancient_oak_cave = Room(
        "Ancient Oak Cave",
        "A cavernous hollow inside the roots of a giant dead oak. Spooky forest runes glow dimly on the bark.",
    )

    # Set up Whisperwood Exits
    eldergrove_center.add_exit("south", forest_entrance)
    forest_entrance.add_exit("north", eldergrove_center)
    forest_entrance.add_exit("south", goblin_outpost)

    goblin_outpost.add_exit("north", forest_entrance)
    goblin_outpost.add_exit("east", whispering_glade)
    goblin_outpost.add_exit("south", ancient_oak_cave)

    whispering_glade.add_exit("west", goblin_outpost)
    ancient_oak_cave.add_exit("north", goblin_outpost)

    # Setup Whisperwood Enemies
    goblin_outpost.enemy = Enemy(
        "Goblin Sentry",
        "A green goblin with a crude spear.",
        hp=35,
        max_hp=35,
        attack=12,
        defense=3,
        level=2,
        xp_value=25,
        gold_value=15,
    )

    # Boss: The Forest Ancient inside the Ancient Oak Cave
    whisperwood_boss = Boss(
        name="The Forest Ancient",
        description="A massive, corrupted tree golem with glowing purple eyes and roots like giant whips.",
        hp=120,
        max_hp=120,
        attack=22,
        defense=8,
        level=5,
        xp_value=100,
        gold_value=80,
        phases=2,
    )
    ancient_oak_cave.enemy = whisperwood_boss

    # Setup Whisperwood Items
    whispering_glade.items.append(
        Consumable(
            "Health Potion",
            "A glowing red potion that restores 20 HP.",
            value=15,
            hp_restore=20,
        )
    )
    whispering_glade.items.append(
        Consumable(
            "Mana Elixir",
            "A shimmering blue flask that restores 15 Mana.",
            value=20,
            mp_restore=15,
        )
    )

    # Place Rusty Sword in Goblin Outpost
    goblin_outpost.items.append(
        Equipment(
            "Bronze Dagger",
            "A quick, sharp bronze dagger.",
            EquipmentSlot.WEAPON,
            value=25,
            attack_bonus=4,
        )
    )

    # ==================== TOWN #2: SILVERLIGHT KEEP ====================
    # Connected via a portal/bridge after defeating the Forest Ancient (or directly east from Eldergrove Blacksmith, but locked!)
    silverlight_bridge = Room(
        "Silverlight Bridge",
        "A majestic stone bridge spanning a roaring white-water canyon. Beautiful white towers guard the gate ahead.",
    )
    silverlight_square = Room(
        "Silverlight Keep Square",
        "A grand city paved with pristine marble. Statues of noble knights stand watch, and flags ripple in the wind.",
        is_town=True,
    )
    silverlight_smithy = Room(
        "Silverlight Royal Armory",
        "A premium armory displaying polished steel breastplates and heavy, glowing magical weapons.",
        is_town=True,
    )

    # Setup Silverlight Exits
    eldergrove_blacksmith.add_exit("east", silverlight_bridge)
    silverlight_bridge.add_exit("west", eldergrove_blacksmith)
    silverlight_bridge.add_exit("east", silverlight_square)
    silverlight_square.add_exit("west", silverlight_bridge)
    silverlight_square.add_exit("north", silverlight_smithy)

    # Silverlight Armory NPC
    silverlight_smithy.npcs.append(
        NPC(
            "Quartermaster Elena",
            "Elena is a sharp-eyed high elven woman clad in decorative steel scale-mail. She only deals with veteran adventurers.",
            "Elena sells the Steel Broadsword (+12 ATK, 120 Gold) and Steel Plate (+10 DEF, 100 Gold).",
        )
    )

    # Lock Silverlight Bridge! Needs the "Aether Sigil" dropped by the Whisperwood Boss.
    silverlight_bridge.locked = True
    silverlight_bridge.key_needed = Item(
        "Aether Sigil",
        "A glowing crystal sigil left behind by the Forest Ancient.",
        value=0,
        is_quest_item=True,
    )

    # ==================== DUNGEON #2: CASTLE SHADOWSPIRE ====================
    # South of Silverlight Square lies the final massive dungeon
    shadowspire_gates = Room(
        "Shadowspire Gates",
        "The imposing iron gates of Castle Shadowspire. Thunder rumbles overhead, and purple lightning cracks.",
    )
    shadowspire_courtyard = Room(
        "Shadowspire Courtyard",
        "A spooky courtyard filled with gargoyles and dead fountains. Shadows dance along the cobblestone walls.",
    )
    spire_laboratory = Room(
        "Alchemical Laboratory",
        "A dark lab full of boiling cauldrons, strange colored glass beakers, and shelves of ancient magical books.",
    )
    shadow_throne_room = Room(
        "Shadow Throne Room",
        "The grand throne room where Archmage Malakor sits upon a throne of obsidian, channeling a giant floating dark void.",
    )

    # Setup Shadowspire Exits
    silverlight_square.add_exit("south", shadowspire_gates)
    shadowspire_gates.add_exit("north", silverlight_square)
    shadowspire_gates.add_exit("south", shadowspire_courtyard)

    shadowspire_courtyard.add_exit("north", shadowspire_gates)
    shadowspire_courtyard.add_exit("west", spire_laboratory)
    shadowspire_courtyard.add_exit("south", shadow_throne_room)

    spire_laboratory.add_exit("east", shadowspire_courtyard)
    shadow_throne_room.add_exit("north", shadowspire_courtyard)

    # Shadowspire Enemies
    shadowspire_courtyard.enemy = Enemy(
        "Shadow Gargoyle",
        "A stone gargoyle animated by dark necromancy.",
        hp=70,
        max_hp=70,
        attack=18,
        defense=6,
        level=6,
        xp_value=50,
        gold_value=30,
    )
    spire_laboratory.enemy = Enemy(
        "Void Horror",
        "A floating mass of tentacles and purple eyes.",
        hp=85,
        max_hp=85,
        attack=22,
        defense=4,
        level=7,
        xp_value=65,
        gold_value=40,
    )

    # Spire Lab loot
    spire_laboratory.items.append(
        Equipment(
            "Wizard's Ring",
            "An emerald ring that boosts mana flow.",
            EquipmentSlot.ACCESSORY,
            value=150,
            max_mana_bonus=25,
            attack_bonus=5,
        )
    )
    spire_laboratory.items.append(
        Consumable(
            "Super Elixir",
            "Fully restores HP and Mana.",
            value=100,
            hp_restore=150,
            mp_restore=100,
        )
    )

    # Main Boss: Archmage Malakor in Throne Room
    malakor = Boss(
        name="Archmage Malakor",
        description="A tall figure clad in obsidian robes, wielding a staff tipped with a black star crystal.",
        hp=250,
        max_hp=250,
        attack=32,
        defense=12,
        level=10,
        xp_value=500,
        gold_value=200,
        phases=2,
    )
    shadow_throne_room.enemy = malakor

    # Lock Shadow Throne Room! Requires "Void Key" from the Alchemical Laboratory
    shadow_throne_room.locked = True
    shadow_throne_room.key_needed = Item(
        "Void Key",
        "A heavy dark metal key humming with void energy.",
        value=0,
        is_quest_item=True,
    )

    # Make Void Horror drop the Void Key (we will write custom enemy-drop logic in the game loops)

    # Store all rooms in map dictionary
    world = {
        "Eldergrove Center": eldergrove_center,
        "Eldergrove Tavern (The Golden Oak)": eldergrove_tavern,
        "Eldergrove Blacksmith (Iron & Ash)": eldergrove_blacksmith,
        "Eldergrove Temple (Aether Sanctuary)": eldergrove_temple,
        "Whisperwood Entrance": forest_entrance,
        "Goblin Outpost": goblin_outpost,
        "Whispering Glade": whispering_glade,
        "Ancient Oak Cave": ancient_oak_cave,
        "Silverlight Bridge": silverlight_bridge,
        "Silverlight Keep Square": silverlight_square,
        "Silverlight Royal Armory": silverlight_smithy,
        "Shadowspire Gates": shadowspire_gates,
        "Shadowspire Courtyard": shadowspire_courtyard,
        "Alchemical Laboratory": spire_laboratory,
        "Shadow Throne Room": shadow_throne_room,
    }

    return world
