
# -----------------------------------------------------------
# Items class
# Used to calculate bottleneck
# -----------------------------------------------------------


class Item:
    def __init__(self, name, amount, type="item"):
        self.name = name
        self.amount = amount
        self.type = type

    def __str__(self):
        return f"{self.name} ({self.amount})"

    def get_ingame_image_path(self):
        # Item image url
        # To display the entity game image, we will the images
        # from : https://wiki.factorio.com/Category:Game_images

        # We need to transform the entity name to a valid url
        entity_wiki_name = self.name.capitalize().replace('-', '_')

        return f"https://wiki.factorio.com/images/{entity_wiki_name}.png"


class Flow:
    def __init__(self):
        self.items = {}
        # Format:  {
        #    item_name_1: 0.8, # Per min
        #    item_name_2: 0.4,
        # }

    def add_item(self, item, amount):
        if item is None:
            print(f"ERROR: a flow was added without an item")
            raise Exception("Flow added without item")

        if amount is None:
            print(f"ERROR: a flow was added without an amount")
            raise Exception("Flow added without amount")

        if item not in self.items:
            self.items[item] = amount
        else:
            self.items[item] += amount

        print("FLOW: added item:", item, amount)

    @property
    def total_amount(self):
        if len(self.items) == 0:
            return 0
        return sum(self.items.values())

    def __str__(self) -> str:
        return "[" + ", ".join([f"{item}: {amount}" for item, amount in self.items.items()]) + "]"
