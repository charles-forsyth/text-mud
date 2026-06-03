from typing import Dict, Optional
from aetheria.models import Item, deserialize_item


class Quest:
    def __init__(
        self,
        quest_id: str,
        name: str,
        description: str,
        objective_type: str,  # "kill", "fetch", "talk"
        objective_target: str,  # Enemy name, Item name, NPC name
        count_needed: int = 1,
        count_current: int = 0,
        gold_reward: int = 20,
        xp_reward: int = 50,
        item_reward: Optional[Item] = None,
        status: str = "inactive",  # "inactive", "active", "completed"
    ):
        self.quest_id = quest_id
        self.name = name
        self.description = description
        self.objective_type = objective_type
        self.objective_target = objective_target
        self.count_needed = count_needed
        self.count_current = count_current
        self.gold_reward = gold_reward
        self.xp_reward = xp_reward
        self.item_reward = item_reward
        self.status = status

    @property
    def is_objective_met(self) -> bool:
        return self.count_current >= self.count_needed

    def update_progress(
        self, target_type: str, target_name: str, amount: int = 1
    ) -> bool:
        """Updates objective progress if criteria match. Returns True if progress changed."""
        if self.status != "active":
            return False

        if (
            self.objective_type == target_type
            and self.objective_target.lower() == target_name.lower()
        ):
            self.count_current = min(self.count_needed, self.count_current + amount)
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "quest_id": self.quest_id,
            "name": self.name,
            "description": self.description,
            "objective_type": self.objective_type,
            "objective_target": self.objective_target,
            "count_needed": self.count_needed,
            "count_current": self.count_current,
            "gold_reward": self.gold_reward,
            "xp_reward": self.xp_reward,
            "item_reward": (self.item_reward.to_dict() if self.item_reward else None),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Quest":
        ir_data = data.get("item_reward")
        item_reward = deserialize_item(ir_data) if ir_data else None

        return cls(
            quest_id=data["quest_id"],
            name=data["name"],
            description=data["description"],
            objective_type=data["objective_type"],
            objective_target=data["objective_target"],
            count_needed=data.get("count_needed", 1),
            count_current=data.get("count_current", 0),
            gold_reward=data.get("gold_reward", 20),
            xp_reward=data.get("xp_reward", 50),
            item_reward=item_reward,
            status=data.get("status", "inactive"),
        )

    def __str__(self) -> str:
        prog = (
            f"({self.count_current}/{self.count_needed})"
            if self.objective_type in ["kill", "fetch"]
            else ""
        )
        return f"{self.name} {prog} - {self.description}"


def get_default_quests() -> Dict[str, Quest]:
    """Sets up the predefined questline templates for Aetheria MUD."""
    quests = {
        # Eldergrove / Whisperwood quests
        "q_eldergrove_goblins": Quest(
            quest_id="q_eldergrove_goblins",
            name="Forest Cleanse",
            description="Exterminate the Goblin Sentry lurking in the Whisperwood Outpost.",
            objective_type="kill",
            objective_target="Goblin Sentry",
            count_needed=1,
            gold_reward=30,
            xp_reward=50,
        ),
        "q_eldergrove_sigil": Quest(
            quest_id="q_eldergrove_sigil",
            name="The Aether Sigil",
            description="Defeat the corrupted giant tree 'The Forest Ancient' inside the Ancient Oak Cave and reclaim the Aether Sigil.",
            objective_type="kill",
            objective_target="The Forest Ancient",
            count_needed=1,
            gold_reward=100,
            xp_reward=200,
        ),
        # Silverlight / Spire final quests
        "q_silverlight_malakor": Quest(
            quest_id="q_silverlight_malakor",
            name="Confronting Malakor",
            description="Enter Castle Shadowspire and defeat Archmage Malakor inside the Shadow Throne Room.",
            objective_type="kill",
            objective_target="Archmage Malakor",
            count_needed=1,
            gold_reward=300,
            xp_reward=500,
        ),
    }
    return quests
