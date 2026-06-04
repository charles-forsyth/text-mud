from typing import Dict, List, Optional, Any


class TalentNode:
    """Represents an unlockable skill node or passive trait in a class tree."""

    def __init__(
        self,
        node_id: str,
        name: str,
        description: str,
        max_rank: int = 3,
        prerequisites: Optional[List[str]] = None,
        stat_modifiers: Optional[
            Dict[str, float]
        ] = None,  # e.g., {"attack_multiplier": 0.05}
        unlocks_spell_name: Optional[str] = None,
    ):
        self.node_id = node_id
        self.name = name
        self.description = description
        self.max_rank = max_rank
        self.current_rank = 0
        self.prerequisites = prerequisites or []
        self.stat_modifiers = stat_modifiers or {}
        self.unlocks_spell_name = unlocks_spell_name

    def to_dict(self) -> dict:
        return {"node_id": self.node_id, "current_rank": self.current_rank}

    @classmethod
    def from_template(
        cls, node_id: str, current_rank: int, template: "TalentNode"
    ) -> "TalentNode":
        node = cls(
            node_id=node_id,
            name=template.name,
            description=template.description,
            max_rank=template.max_rank,
            prerequisites=template.prerequisites,
            stat_modifiers=template.stat_modifiers,
            unlocks_spell_name=template.unlocks_spell_name,
        )
        node.current_rank = current_rank
        return node


class SkillTree:
    """Manages skill point allocations, prerequisite paths, and cumulative modifiers."""

    def __init__(self, class_name: str, nodes: Dict[str, TalentNode]):
        self.class_name = class_name
        self.nodes = nodes
        self.allocated_points = 0

    def can_allocate(self, node_id: str, available_points: int) -> bool:
        """Validates rank ceilings, point pool, and prerequisite node statuses."""
        node = self.nodes.get(node_id)
        if not node or available_points < 1:
            return False

        if node.current_rank >= node.max_rank:
            return False

        # Check prerequisite node chains
        for prereq_id in node.prerequisites:
            prereq = self.nodes.get(prereq_id)
            if not prereq or prereq.current_rank < prereq.max_rank:
                return False

        return True

    def allocate(self, node_id: str, player: Any) -> bool:
        """Allocates a skill point, unlocking active spells or updating stat configurations."""
        if not self.can_allocate(node_id, player.skill_points):
            return False

        node = self.nodes[node_id]
        node.current_rank += 1
        player.skill_points -= 1
        self.allocated_points += 1

        # Unlock unique spell if first point invested
        if node.unlocks_spell_name and node.current_rank == 1:
            player.unlock_spell_from_tree(node.unlocks_spell_name)

        return True

    def get_cumulative_multiplier(self, modifier_name: str) -> float:
        """Calculates combined scaling multipliers from all unlocked passive nodes."""
        multiplier = 0.0
        for node in self.nodes.values():
            if node.current_rank > 0:
                mod_val = node.stat_modifiers.get(modifier_name, 0.0)
                multiplier += mod_val * node.current_rank
        return multiplier

    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "allocated_points": self.allocated_points,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillTree":
        class_name = data.get("class_name", "Warrior")
        tree = get_tree_for_class(class_name)
        nodes_data = data.get("nodes", {})
        for nid, n_dict in nodes_data.items():
            if nid in tree.nodes:
                tree.nodes[nid].current_rank = n_dict.get("current_rank", 0)
        tree.allocated_points = data.get("allocated_points", 0)
        return tree


def get_tree_for_class(class_name: str) -> SkillTree:
    """Returns a newly initialized, class-specific Talent Tree template."""
    c_name = class_name.capitalize()

    nodes: Dict[str, TalentNode] = {}

    if c_name == "Warrior":
        nodes = {
            "iron_skin": TalentNode(
                node_id="iron_skin",
                name="Iron Skin",
                description="Increases physical defense by 10% per rank.",
                max_rank=3,
                stat_modifiers={"defense_multiplier": 0.10},
            ),
            "heavy_strikes": TalentNode(
                node_id="heavy_strikes",
                name="Heavy Strikes",
                description="Increases attack power by 10% per rank.",
                max_rank=3,
                stat_modifiers={"attack_multiplier": 0.10},
            ),
            "shield_slam": TalentNode(
                node_id="shield_slam",
                name="Shield Slam",
                description="Unlocks the active Shield Slam ability.",
                max_rank=1,
                prerequisites=["iron_skin"],
                unlocks_spell_name="Shield Slam",
            ),
        }
    elif c_name == "Mage":
        nodes = {
            "arcane_efficiency": TalentNode(
                node_id="arcane_efficiency",
                name="Arcane Efficiency",
                description="Increases maximum mana capacity by 15% per rank.",
                max_rank=3,
                stat_modifiers={"max_mana_multiplier": 0.15},
            ),
            "pyromaniac": TalentNode(
                node_id="pyromaniac",
                name="Pyromaniac",
                description="Increases spell casting power by 12% per rank.",
                max_rank=3,
                stat_modifiers={"attack_multiplier": 0.12},
            ),
            "meteor": TalentNode(
                node_id="meteor",
                name="Meteor",
                description="Unlocks the devastating Meteor spell.",
                max_rank=1,
                prerequisites=["pyromaniac"],
                unlocks_spell_name="Meteor",
            ),
        }
    elif c_name == "Rogue":
        nodes = {
            "shadow_step": TalentNode(
                node_id="shadow_step",
                name="Shadow Step",
                description="Increases evasion modifiers by 10% per rank.",
                max_rank=3,
                stat_modifiers={"evasion_multiplier": 0.10},
            ),
            "critical_strikes": TalentNode(
                node_id="critical_strikes",
                name="Critical Strikes",
                description="Increases attack power by 12% per rank.",
                max_rank=3,
                stat_modifiers={"attack_multiplier": 0.12},
            ),
            "assassinate": TalentNode(
                node_id="assassinate",
                name="Assassinate",
                description="Unlocks the deadly Assassinate active attack.",
                max_rank=1,
                prerequisites=["critical_strikes"],
                unlocks_spell_name="Assassinate",
            ),
        }
    else:  # Default to Cleric or fallback
        nodes = {
            "divine_blessing": TalentNode(
                node_id="divine_blessing",
                name="Divine Blessing",
                description="Increases maximum health pool by 12% per rank.",
                max_rank=3,
                stat_modifiers={"max_hp_multiplier": 0.12},
            ),
            "holy_defense": TalentNode(
                node_id="holy_defense",
                name="Holy Defense",
                description="Increases physical defense by 8% per rank.",
                max_rank=3,
                stat_modifiers={"defense_multiplier": 0.08},
            ),
            "resurrection": TalentNode(
                node_id="resurrection",
                name="Resurrection",
                description="Unlocks the restorative Resurrect healing spell.",
                max_rank=1,
                prerequisites=["divine_blessing"],
                unlocks_spell_name="Resurrect",
            ),
        }

    return SkillTree(class_name=c_name, nodes=nodes)
