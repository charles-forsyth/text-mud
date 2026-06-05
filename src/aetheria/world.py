from typing import Dict, List, Optional, Any
from aetheria.models import Item, deserialize_item, Equipment, EquipmentSlot, Consumable
from aetheria.entity import Enemy, Boss, deserialize_enemy


class NPC:
    def __init__(
        self,
        name: str,
        persona: str,
        dialogue_context: str = "",
        affinity: int = 0,
        relationship_flags: Optional[List[str]] = None,
    ):
        self.name = name
        self.persona = persona
        self.dialogue_context = dialogue_context
        self.dialogue_history: list[tuple[str, str]] = []
        self.affinity = max(-100, min(100, affinity))
        self.relationship_flags = (
            relationship_flags if relationship_flags is not None else []
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "persona": self.persona,
            "dialogue_context": self.dialogue_context,
            "dialogue_history": self.dialogue_history,
            "affinity": self.affinity,
            "relationship_flags": self.relationship_flags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NPC":
        npc = cls(
            name=data["name"],
            persona=data["persona"],
            dialogue_context=data.get("dialogue_context", ""),
            affinity=data.get("affinity", 0),
            relationship_flags=data.get("relationship_flags", []),
        )
        # Convert any inner lists back to tuples
        history_list = data.get("dialogue_history", [])
        npc.dialogue_history = [(speaker, text) for speaker, text in history_list]
        return npc


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
        self.hazard: Optional[Any] = None
        self._saved_exits_map: Dict[str, str] = {}

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
            "hazard": {
                "hazard_type": self.hazard.hazard_type,
                "damage_per_tick": self.hazard.damage_per_tick,
                "description": self.hazard.description,
                "mitigation_item": self.hazard.mitigation_item,
            }
            if self.hazard
            else None,
            "exits": {
                dir_: target.name for dir_, target in self.exits.items() if target
            },
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

        haz_data = data.get("hazard")
        if haz_data:
            from aetheria.weather import EnvironmentalHazard

            room.hazard = EnvironmentalHazard(
                hazard_type=haz_data["hazard_type"],
                damage_per_tick=haz_data["damage_per_tick"],
                description=haz_data["description"],
                mitigation_item=haz_data.get("mitigation_item"),
            )

        room._saved_exits_map = data.get("exits", {})
        return room


def build_default_world() -> Dict[str, Room]:
    """Assembles the entire default massive world map of towns and dungeons."""
    world: Dict[str, Room] = {}

    # ==================== TOWN #1: ELDERGROVE ====================
    eldergrove_center = Room(
        "Eldergrove Center",
        "The heart of Eldergrove beat beneath the sheltering boughs of a monolithic, golden-leaved oak that had stood for a thousand summers. Sunlight filters through the shimmering canopy, casting a warm, dappled amber glow across the cobblestone plaza. The air carries the sweet scent of wildflowers, freshly baked bread, and damp pine needles, while wind chimes suspended from ancient branches sing a soft, melodic lullaby with every passing breeze.",
        is_town=True,
    )
    eldergrove_tavern = Room(
        "Eldergrove Tavern (The Golden Oak)",
        "A heavy oak door yields to reveal a cozy, boisterous haven awash in the comforting warmth of a crackling hearth. The scent of slow-roasted pork glazes, spiced honey mead, and rich cedarwood smoke hangs thick in the air. Laughter and lively folk songs echo off the low timber rafters, where seasoned adventurers and weary travelers swap tall tales over frosty tankards of golden ale.",
        is_town=True,
    )
    eldergrove_blacksmith = Room(
        "Eldergrove Blacksmith (Iron & Ash)",
        "Heat radiates from an open-air forge like a physical wave, stinging the skin and carrying the pungent bite of coal smoke and molten metal. The ringing rhythm of Thorin’s heavy hammer striking red-hot steel vibrates through the ground, punctuated by the violent, escaping hiss of steam as forged blades are plunged into iron troughs of cooling spring water.",
        is_town=True,
    )
    eldergrove_temple = Room(
        "Eldergrove Temple (Aether Sanctuary)",
        "A sanctuary of absolute serenity, built from pristine blocks of soft white marble that seem to absorb and diffuse the harsh light of the outside world. The air is cool and smells faintly of crushed sage and incense, and the gentle murmur of natural spring water flowing into a central font provides a tranquil backdrop. Here, clerics tend to the sick and offer restorative draughts.",
        is_town=True,
    )

    # Setup Eldergrove Exits
    eldergrove_center.add_exit("north", eldergrove_tavern)
    eldergrove_tavern.add_exit("south", eldergrove_center)
    eldergrove_center.add_exit("east", eldergrove_blacksmith)
    eldergrove_blacksmith.add_exit("west", eldergrove_center)
    eldergrove_center.add_exit("west", eldergrove_temple)
    eldergrove_temple.add_exit("east", eldergrove_center)

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
        "The bright skies of Eldergrove vanish, swallowed by the dense, suffocating canopy of the Whisperwood. A heavy, perpetual twilight hangs beneath the branches, where thick, ancient roots crawl like sleeping serpents across a damp floor of spongy green moss. The forest is quiet—too quiet—save for the low, rhythmic sighing of the wind through high leaves that sounds unsettlingly like human whispers.",
    )
    goblin_outpost = Room(
        "Goblin Outpost",
        "A chaotic, makeshift barricade constructed from jagged, fire-hardened logs and crudely lashed wooden stakes. Splintered bones of forest beasts lie scattered in the mud around a sputtering, foul-smelling campfire that billows columns of acrid black smoke. The sickening odor of wet hide, rot, and stale grease clings to the humid air, warning of the hostile sentries lurking in the shadows.",
    )
    whispering_glade = Room(
        "Whispering Glade",
        "An enchanting, pristine oasis hidden deep within the dark forest, where a vertical shaft of ethereal, pale-blue starlight pierces the canopy. Luminescent azure flora and delicate glowing mushrooms line the perimeter, pulsing softly with an inner magical heartbeat. The air is remarkably crisp and energized with wild magic, humming with a gentle, static-like resonance.",
    )
    ancient_oak_cave = Room(
        "Ancient Oak Cave",
        "A damp, cavernous hollow carved into the subterranean root network of a colossal, fossilized dead oak. The ceiling is draped with hanging roots that slowly drip icy moisture onto the cold stone floor below. Cryptic runes of some long-forgotten, corrupted forest deity glow with a faint, malevolent purple radiance along the gnarled bark walls, filling the dark void with a heavy sense of impending doom.",
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
        "A majestic, soaring span of pure white granite that arches gracefully over a churning, deafening white-water chasm. Below, a roaring mountain river crashes violently against jagged rocks, sending a cool, refreshing mist high into the air. Pristine, fortified guard towers of immaculate stone stand vigilant at the eastern gate, their battlements flying the royal sapphire banners of Silverlight.",
    )
    silverlight_square = Room(
        "Silverlight Keep Square",
        "A spectacular, sprawling urban plaza paved with polished marble tiles that gleam brilliantly under the sky. Massive, lifelike statues of legendary knights in full plate armor stand sentinel around a grand fountain, their stone eyes gazing toward the horizon. Tall spires rise majestically into the heavens, and giant royal flags ripple with a crisp, snapping sound in the high mountain wind.",
        is_town=True,
    )
    silverlight_smithy = Room(
        "Silverlight Royal Armory",
        "An exquisite, high-ceilinged hall of stone and polished mahogany, reflecting the brilliant, cold glare of immaculate steel. The walls are lined with heavy breastplates, masterfully folded shields, and pristine weapons that hum with integrated magical enchantments. The air is crisp and carries the dry, clean smell of leather straps, polishing oils, and cold, powerful iron.",
        is_town=True,
    )

    # Setup Silverlight Exits
    eldergrove_blacksmith.add_exit("east", silverlight_bridge)
    silverlight_bridge.add_exit("west", eldergrove_blacksmith)
    silverlight_bridge.add_exit("east", silverlight_square)
    silverlight_square.add_exit("west", silverlight_bridge)
    silverlight_square.add_exit("north", silverlight_smithy)
    silverlight_smithy.add_exit("south", silverlight_square)

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
        "The immense, black-iron gates of Castle Shadowspire rise like jagged, broken teeth against a bruised, storm-swept sky. Thunder rumbles continuously, vibrating in the chest, while erratic arcs of crackling violet lightning silhouette the sharp, menacing towers of the fortress. A freezing, unnatural wind howls through the iron bars, carrying the scent of ozone and ancient decay.",
    )
    shadowspire_courtyard = Room(
        "Shadowspire Courtyard",
        "A desolate, wind-scoured courtyard littered with cracked cobblestones and choked with withered, black brambles. Skeletal gargoyles with empty, mocking stares perch atop crumbling battlements, and dry, long-dead stone fountains are filled with nothing but autumn dust and bone fragments. Shadows pool unnaturally deep in the corners, stretching and shifting of their own accord.",
    )
    spire_laboratory = Room(
        "Alchemical Laboratory",
        "A dark, cluttered sanctuary of forbidden knowledge, smelling heavily of sulfur, volatile chemicals, and ancient, dusty parchment. Shelves groaning under the weight of bizarre leather-bound grimoires surround bubbling cauldrons and complex glass apparatuses that drip glowing green and crimson liquids. A constant, ominous hum of dark magical energy resonates from the stone floor.",
    )
    shadow_throne_room = Room(
        "Shadow Throne Room",
        "A vast, cathedral-like hall of obsidian stone, cold as the grave. Towering pillars of black rock ascend into absolute darkness, where a colossal, swirling rift of pure void-energy hovers menacingly behind a throne of jagged volcanic glass. The air is thin and freezing, smelling strongly of ozone and burnt ash, as the void rift slowly pulls at the light and sound of the room with a deep, crushing silence.",
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

    # Set up environmental hazards on specific rooms
    from aetheria.weather import EnvironmentalHazard

    spire_laboratory.hazard = EnvironmentalHazard(
        hazard_type="Acidic Acid Fumes",
        damage_per_tick=8,
        description="Corrosive acidic gas fills the chamber",
        mitigation_item="Steel Plate",
    )
    forest_entrance.hazard = EnvironmentalHazard(
        hazard_type="Poison Vines",
        damage_per_tick=3,
        description="Thorny, venomous briars slash at your ankles",
        mitigation_item="Leather Jerkin",
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
