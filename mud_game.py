class Item:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __str__(self):
        return f"{self.name}: {self.description}"


class Enemy:
    def __init__(self, name, description, damage):
        self.name = name
        self.description = description
        self.damage = damage

    def attack(self, player):
        print(f"The {self.name} attacks you for {self.damage} damage!")
        player.take_damage(self.damage)

    def __str__(self):
        return f"{self.name}: {self.description} (Damage: {self.damage})"


class Room:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.exits = {}
        self.items = []
        self.enemy = None
        self.locked = False
        self.key_needed = None

    def add_exit(self, direction, room):
        self.exits[direction] = room

    def add_item(self, item):
        self.items.append(item)

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)

    def set_enemy(self, enemy):
        self.enemy = enemy

    def get_exit(self, direction):
        return self.exits.get(direction)

    def __str__(self):
        return f"{self.name}\n{self.description}"


class Player:
    def __init__(self, name, current_room):
        self.name = name
        self.current_room = current_room
        self.inventory = []
        self.hp = 100
        self.max_hp = 100

    def move(self, direction):
        if direction in self.current_room.exits:
            next_room = self.current_room.exits[direction]
            if next_room.locked:
                if next_room.key_needed and self.has_item(next_room.key_needed.name):
                    print(
                        f"You unlock the {next_room.name} with the {next_room.key_needed.name}."
                    )
                    next_room.locked = False
                else:
                    print(f"The {next_room.name} is locked. You need a key.")
                    return False
            self.current_room = next_room
            print(f"You move {direction} to the {next_room.name}.")
            print(next_room.description)
            return True
        else:
            print("You can't go that way.")
            return False

    def look(self):
        print(self.current_room)
        if self.current_room.items:
            print("Items here:")
            for item in self.current_room.items:
                print(f"- {item}")
        else:
            print("No items here.")

        if self.current_room.enemy:
            print(f"DANGER: {self.current_room.enemy}")

        if self.current_room.exits:
            print("Exits:", ", ".join(self.current_room.exits.keys()))

        print(f"HP: {self.hp}/{self.max_hp}")

    def take(self, item_name):
        for item in self.current_room.items:
            if item.name.lower() == item_name.lower():
                self.inventory.append(item)
                self.current_room.remove_item(item)
                print(f"You picked up the {item.name}.")
                return True
        print("Item not found.")
        return False

    def use(self, item_name):
        if item_name.lower() == "health potion":
            for item in self.inventory:
                if item.name == "Health Potion":
                    self.heal(20)
                    self.inventory.remove(item)
                    print("You used the Health Potion.")
                    return True
            print("You don't have a Health Potion.")
            return False
        else:
            print("You can't use that.")
            return False

    def inventory_list(self):
        if self.inventory:
            print("Inventory:")
            for item in self.inventory:
                print(f"- {item.name}")
        else:
            print("Your inventory is empty.")
        print(f"HP: {self.hp}/{self.max_hp}")

    def has_item(self, item_name):
        return any(item.name.lower() == item_name.lower() for item in self.inventory)

    def take_damage(self, amount):
        self.hp -= amount
        print(f"You took {amount} damage! Current HP: {self.hp}/{self.max_hp}")

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        print(f"You healed {amount} HP. Current HP: {self.hp}/{self.max_hp}")


class Game:
    def __init__(self):
        self.world = {}
        self.player = None
        self.is_running = True

    def setup_world(self):
        # Create Items
        golden_key = Item("Golden Key", "A shiny golden key.")
        rusty_sword = Item("Rusty Sword", "An old rusty sword.")
        potion = Item("Health Potion", "Restores 20 HP.")

        # Create Enemies
        goblin = Enemy("Goblin", "A nasty green goblin.", 10)

        # Create Rooms
        entrance_hall = Room(
            "Entrance Hall", "A grand entrance hall with cobwebs everywhere."
        )
        great_hall = Room(
            "Great Hall", "A massive hall with long tables and broken chairs."
        )
        kitchen = Room("Kitchen", "A smelly kitchen with rotting food.")
        dungeon = Room("Dungeon", "A dark, damp dungeon cell.")
        front_gate = Room("Front Gate", "The main exit from the castle. It is locked.")

        # Setup Exits
        entrance_hall.add_exit("north", great_hall)
        entrance_hall.add_exit("east", kitchen)
        entrance_hall.add_exit("south", front_gate)

        great_hall.add_exit("south", entrance_hall)
        great_hall.add_exit("west", dungeon)

        kitchen.add_exit("west", entrance_hall)

        dungeon.add_exit("east", great_hall)

        front_gate.add_exit("north", entrance_hall)

        # Setup Items in Rooms
        great_hall.add_item(golden_key)
        kitchen.add_item(rusty_sword)
        kitchen.add_item(potion)  # Add potion to kitchen

        # Setup Enemies in Rooms
        dungeon.set_enemy(goblin)

        # Lock Front Gate
        front_gate.locked = True
        front_gate.key_needed = golden_key

        # Set Starting Room
        self.player = Player("Hero", entrance_hall)
        self.world = {
            "Entrance Hall": entrance_hall,
            "Great Hall": great_hall,
            "Kitchen": kitchen,
            "Dungeon": dungeon,
            "Front Gate": front_gate,
        }

    def process_command(self, command):
        parts = command.lower().split()
        if not parts:
            return

        verb = parts[0]
        noun = " ".join(parts[1:]) if len(parts) > 1 else None

        if verb in ["quit", "exit"]:
            self.is_running = False
            print("Goodbye!")
        elif verb in ["n", "s", "e", "w", "north", "south", "east", "west"]:
            direction = verb
            if verb == "n":
                direction = "north"
            elif verb == "s":
                direction = "south"
            elif verb == "e":
                direction = "east"
            elif verb == "w":
                direction = "west"
            self.player.move(direction)
        elif verb == "go" and noun:
            self.player.move(noun)
        elif verb == "look":
            self.player.look()
        elif verb == "take" and noun:
            self.player.take(noun)
        elif verb == "use" and noun:
            self.player.use(noun)
        elif verb in ["i", "inventory"]:
            self.player.inventory_list()
        else:
            print("I don't understand that command.")

        # Enemy Turn
        if self.player.current_room.enemy:
            self.player.current_room.enemy.attack(self.player)

        # Check Game Over
        if self.player.hp <= 0:
            print("You have died! Game Over.")
            self.is_running = False
            return

        # Check Win Condition
        if (
            self.player.current_room.name == "Front Gate"
            and not self.player.current_room.locked
        ):
            if self.player.hp > 0:
                print("Congratulations! You have escaped the Haunted Castle!")
                self.is_running = False

    def play(self):
        print("Welcome to the Haunted Castle MUD!")
        self.player.look()
        while self.is_running:
            try:
                command = input("> ")
                self.process_command(command)
            except (KeyboardInterrupt, EOFError):
                self.is_running = False
                print("\nGoodbye!")


if __name__ == "__main__":
    game = Game()
    game.setup_world()
    game.play()
