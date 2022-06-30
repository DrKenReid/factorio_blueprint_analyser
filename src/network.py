from turtle import color
from matplotlib.pyplot import title
from numpy import size
from src import utils
from pyvis.network import Network as NetworkDisplay

# -----------------------------------------------------------
# Create a node network from a blueprint
# Provide calculations methods
# -----------------------------------------------------------


def create_network(blueprint):
    network_creator = NetworkCreator(blueprint)
    return network_creator.create_network()


class NetworkCreator:
    blueprint = {}
    node_map = []

    def __init__(self, blueprint):
        self.blueprint = blueprint

    def create_network(self):
        # Create a 2D array that will contain all nodes,
        # the same way as the blueprint array
        # Knowing where the nodes are located from each other will be useful

        # The nodes will then be exctracted from the 2D array in a list

        self.node_map = []

        for _ in range(self.blueprint.heigth):
            self.node_map += [[None for _ in range(self.blueprint.width)]]

        # Iterate over the blueprint entities
        # to create each nodes recursively
        for y in range(self.blueprint.heigth):
            for x in range(self.blueprint.width):
                self.create_node(x, y)

        # Optimize the network
        # TODO: Remove belts that follow each others

        return Network(self.blueprint, self.node_map)

    def create_node(self, x, y):
        # Returns a node object or None

        # Check if the cell hasn't been filled yet
        if x < 0 or x >= self.blueprint.width or y < 0 or y >= self.blueprint.heigth:
            return None

        # Check if a node already exists in the cell
        if self.node_map[y][x] is not None:
            return self.node_map[y][x]

        # Get the entity at the given position
        entity = self.blueprint.array[y][x]

        if entity is None:
            return None

        # We can now create the node
        node = Assembly_node(entity) \
            if entity.data["type"] == "assembling-machine" \
            else Transport_node(entity)

        # Each game entity interacts with the other nodes in there own way
        # The requiered nodes will be created recursively
        if node.type == "transport-belt":
            # The node is inserted in the map to avoid infinit recursion
            self.node_map[y][x] = node

            # We want to set the entity in front of the belt as the node's child
            # We get the coordinates of the entity in front of the belt:
            tile_in_front_offset = entity.get_tile_in_front_offset()
            target_x = x + tile_in_front_offset[0]
            target_y = y + tile_in_front_offset[1]

            # We get the node in front of the belt or create a new one
            child_node = self.create_node(target_x, target_y)

            if child_node is not None and entity.can_connect_to(child_node.entity):
                node.childs.append(child_node)
                child_node.parents.append(node)

            return node

        elif node.type == "inserter":
            # The node is inserted in the map to avoid infinit recursion
            self.node_map[y][x] = node

            # Set the entity where items are droped as the node's child
            tile_drop_offset = entity.get_drop_tile_offset()
            target_drop_x = x + tile_drop_offset[0]
            target_drop_y = y + tile_drop_offset[1]

            drop_child_node = self.create_node(target_drop_x, target_drop_y)

            if drop_child_node is not None and entity.can_move_to(drop_child_node.entity):
                node.childs.append(drop_child_node)
                drop_child_node.parents.append(node)

            # Set the entity where items are picked up as the node's parent
            tile_pickup_offset = entity.get_pickup_tile_offset()
            target_pickup_x = x + tile_pickup_offset[0]
            target_pickup_y = y + tile_pickup_offset[1]

            pickup_node = self.create_node(target_pickup_x, target_pickup_y)

            if pickup_node is not None and entity.can_move_from(pickup_node.entity):
                node.parents.append(pickup_node)
                pickup_node.childs.append(node)

            return node

        elif node.type == "assembling-machine":
            # We will create 9 nodes for the 9 tiles of the assembling machine
            # All the cells are the same object, they share their parents and childs
            for offset in node.entity.offsets:
                target_x = node.entity.position["x"] + offset[0]
                target_y = node.entity.position["y"] + offset[1]

                if target_x < 0 or target_x >= self.blueprint.width\
                        or target_y < 0 or target_y >= self.blueprint.heigth:
                    continue

                self.node_map[target_y][target_x] = node
            return node

        elif node.type == "underground-belt":
            self.node_map[y][x] = node

            if entity.belt_type == "output":
                # Set the entity where items are droped as the node's child
                # Exactly the same as for the transport belt
                tile_in_front_offset = entity.get_tile_in_front_offset()
                target_x = x + tile_in_front_offset[0]
                target_y = y + tile_in_front_offset[1]

                # We get the node in front of the belt or create a new one
                child_node = self.create_node(target_x, target_y)

                if child_node is not None and entity.can_connect_to(child_node.entity):
                    node.childs.append(child_node)
                    child_node.parents.append(node)
            else:
                # We try to connect to the output belt
                possible_output_coords = entity.get_possible_output_coords()
                for possible_coord in possible_output_coords:
                    child_node = self.create_node(
                        possible_coord["x"], possible_coord["y"])

                    if child_node is not None and \
                            child_node.entity.name == node.entity.name and \
                            child_node.entity.belt_type == "output":

                        node.childs.append(child_node)
                        child_node.parents.append(node)
                        break

                    # No output belt found, print warning?

            return node

        elif node.type in ["container", "logistic-container"]:
            # Those entities does not interact with others
            self.node_map[y][x] = node
            return node

        elif node.type == "splitter":

            # We need to add the second splitter tile to the map
            if x == entity.position["x"] and y == entity.position["y"]:
                # If we are the original splitter, we need to add the second splitter
                self.node_map[y][x] = node

                second_belt_offset = entity.get_second_belt_offset()
                second_node_x = x + second_belt_offset[0]
                second_node_y = y + second_belt_offset[1]

                if second_node_x >= 0 and second_node_x < self.blueprint.width and\
                        second_node_y >= 0 and second_node_y < self.blueprint.heigth:
                    self.node_map[second_node_y][second_node_x] = node
            else:
                # We create the original splitter instead
                return self.create_node(entity.position["x"], entity.position["y"])

            # Set the entity where items are droped as the node's child
            drop_tile_offsets = entity.get_drop_tile_offsets()
            for offset in drop_tile_offsets:
                target_drop_x = x + offset[0]
                target_drop_y = y + offset[1]

                drop_child_node = self.create_node(
                    target_drop_x, target_drop_y)

                if drop_child_node is not None and entity.can_move_to(drop_child_node.entity):
                    node.childs.append(drop_child_node)
                    drop_child_node.parents.append(node)

            return node

        utils.verbose(f"Unsupported entity type: {entity.data['type']}")
        return None


class Network:
    def __init__(self, blueprint, nodes_array):
        self.blueprint = blueprint
        self.nodes_array = nodes_array

        self.nodes = []

        for row in self.nodes_array:
            for node in row:
                if node is not None:
                    # Check that the node is not already in the list
                    # It's normal if the node takes multiple tiles
                    # (They appear multiple times in the map)
                    if node not in self.nodes:
                        self.nodes.append(node)

    def root_nodes(self):
        roots = []
        for node in self.nodes:
            if len(node.parents) == 0:
                roots.append(node)
        return roots

    def leaf_nodes(self):
        leafs = []
        for node in self.nodes:
            if len(node.childs) == 0:
                leafs.append(node)
        return leafs

    def display(self):
        net = NetworkDisplay(directed=True, height=1000, width=1900)
        net.repulsion(node_distance=100, spring_length=0)

        # Nodes and edges
        for node in self.nodes:
            # Define node size
            node_size = 3
            if node.type == "transport-belt":
                node_size = 3
            if node.type == "underground-belt" or "splitter":
                node_size = 4
            if node.type == "container" or "logistic-container":
                node_size = 3
            if node.type == "assembling-machine":
                node_size = 5
            if node.type == "inserter":
                node_size = 4

            net.add_node(node.entity.number,
                         value=node_size,
                         shape="image",
                         image=node.entity.get_ingame_image_path(),
                         brokenImage="https://wiki.factorio.com/images/Warning-icon.png")

        for node in self.nodes:
            for child in node.childs:
                net.add_edge(node.entity.number,
                             child.entity.number,
                             color="black")

        # Display recipes
        for node in self.nodes:
            if node.type == "assembling-machine" and node.entity.recipe is not None:
                node_id = str(node.entity.number) + "_recipe"
                net.add_node(node_id,
                             label=node.entity.recipe.name,
                             value=3,
                             shape="image",
                             image=node.entity.recipe.get_ingame_image_path(),
                             brokenImage="https://wiki.factorio.com/images/Warning-icon.png")

                net.add_edge(node.entity.number,
                             node_id,
                             title="produce",
                             color="grey",
                             size=2,
                             dashes=True,
                             arrowStrikethrough=False)

        # Display inputs
        for node in self.root_nodes():
            # TODO: Display the expected input materials
            node_id = str(node.entity.number) + "_root"
            net.add_node(node_id,
                         label="Input",
                         value=3,
                         shape="text")

            net.add_edge(node_id,
                         node.entity.number,
                         color="red",
                         size=2,
                         dashes=True,
                         arrowStrikethrough=False)

        # Display outputs
        for node in self.leaf_nodes():
            # TODO: Display the expected produced materials
            node_id = str(node.entity.number) + "_leaf"
            net.add_node(node_id,
                         label="Output",
                         value=3,
                         shape="text")

            net.add_edge(node.entity.number,
                         node_id,
                         color="blue",
                         size=2,
                         dashes=True,
                         arrowStrikethrough=False)

        # Display nodes transported items
        for node in self.nodes:
            if node.type != "assembling-machine" and node.transported_items is not None:
                for (i, item) in enumerate(node.transported_items):
                    node_id = str(node.entity.number) + "_item_" + str(i)
                    net.add_node(node_id,
                                 label=" ",
                                 value=2,
                                 shape="image",
                                 image=item.get_ingame_image_path(),
                                 brokenImage="https://wiki.factorio.com/images/Warning-icon.png")

                    net.add_edge(node_id,
                                 node.entity.number,
                                 title="transport",
                                 color="lightgrey")

        # Display the graph
        net.show("graph.html")

    def calculate_bottleneck(self):
        # ===========================================
        # === Step 1: Purpose back propagation ======
        # ===========================================

        # The first step is to calculate the purpose of each node
        # We will start from each assembling machine and go up and down
        # each parent and child node to tell them what we expect them to do

        for node in self.nodes:
            # If the node is an assembling machine, we start from it
            if node.type == "assembling-machine":
                node.calculate_purpose()


class Node:
    def __init__(self, entity):
        # Network construction data
        self.entity = entity
        self.childs = []
        self.parents = []
        self.type = entity.data["type"]

    def get_materials_output(self):
        # Get the materials output of the node
        # If the node is an assembling machine, the output is the recipe result
        # Else, the output is the node inputs
        return None

    def calculate_purpose(self):
        return None

    def set_purpose(self, items, from_node=None):
        return None

    def __str__(self):
        return f"Node: {self.entity}, childs: {len(self.childs)}, parents: {len(self.parents)} "


class Assembly_node (Node):
    def __init__(self, entity):
        super().__init__(entity)

        # Bottleneck calculation data
        self.inputs = []
        self.outputs = []

        if self.entity.recipe is not None:
            # Set the self inputs as the recipe ingredients
            for input_item in self.entity.recipe.ingredients:
                self.inputs.append(input_item)

            # Set the self outputs as the recipe result
            self.outputs = [self.entity.recipe.result]
            # We only consider that the recipes makes one item at the moment
            # TODO: Add support for multiple items

    def calculate_purpose(self):
        if self.entity.recipe is not None:

            # First, we calculate the purpose of our parents
            # according to the inputs of the recipe
            print("calculate_purpose of ", self)
            if len(self.entity.recipe.ingredients) == 1:
                # We only need one ingredient to make the recipe
                # so our parents purpose is to provide the ingredient

                for parent in self.parents:
                    parent.set_purpose(
                        self.entity.recipe.ingredients, from_node=self)

            else:
                # We need more than one ingredient to make the recipe,
                # but we don't know witch parent will provide which ingredient

                # So we start by getting all our parents output items
                parent_outputs = []
                for parent in self.parents:
                    parent_output = parent.get_materials_output()
                    parent_outputs.append(parent_output)

                # Then, for each of our ingredients, we try to find a parent
                # that provides the ingredient
                provided_ingredients = []
                for input_item in self.entity.recipe.ingredients:
                    for parent_output in parent_outputs:
                        for parent_item in parent_output:
                            if input_item.name == parent_item.name:
                                # We found a parent that provides the ingredient
                                # We can ignore it and the ingredient it provides
                                provided_ingredients.append(parent_item)

                # The parents with no purpose will provide the other ingredients
                needed_ingredients = [item for item in self.entity.recipe.ingredients
                                      if item not in provided_ingredients]

                for (i, parent_output) in enumerate(parent_outputs):
                    if parent_output is None:
                        # needed_ing = ""
                        # for item in needed_ingredients:
                        #     needed_ing += item.name + " "
                        # print(
                        #     "the parent ", self.parents[i], " has no output so we asign it to " + needed_ing)
                        self.parents[i].set_purpose(
                            needed_ingredients, from_node=self)

            # Then we set the purpose of our childs
            # according to the outputs of the recipe

            for child in self.childs:
                child.set_purpose([self.entity.recipe.result], from_node=self)

    def get_materials_output(self):
        # Get the materials output of the node
        # For a assembling machine node, the output is the recipe result

        return self.outputs

    def __str__(self):
        inputs = ""
        for item in self.inputs:
            inputs += str(item) + " "

        outputs = ""
        for item in self.outputs:
            outputs += str(item) + " "

        return f"Assembly node, childs: {len(self.childs)}, parents: {len(self.parents)} " \
            + f" inputs: {inputs}, outputs: {outputs}"


class Transport_node (Node):
    def __init__(self, entity):
        super().__init__(entity)

        # Bottleneck calculation data
        self.transported_items = None

    def get_materials_output(self):
        if self.transported_items is None:
            # We don't know what the node outputs are
            # so we ask our parents for their output
            transported_items = []
            for parent in self.parents:
                transported_items += parent.get_materials_output()

            # self.transported_items = transported_items
            return transported_items

        return self.transported_items

    def set_purpose(self, items, from_node=None):
        if self.transported_items is not None:
            print(
                "warning: set_purpose called on a transport node that already has a purpose")
            # self.transported_items += items
        else:
            self.transported_items = items
            print("  setting the purpose of ", self)

            for parent in self.parents:
                if parent is not from_node:
                    parent.set_purpose(items, from_node=self)

            for child in self.childs:
                if child is not from_node:
                    child.set_purpose(items, from_node=self)

    def __str__(self):
        transported_items = ""

        if self.transported_items is None:
            transported_items = "?"

        elif len(self.transported_items) == 0:
            transported_items = "None"
        else:
            for item in self.transported_items:
                transported_items += str(item) + " "

        return f"Node {self.entity}, childs: {len(self.childs)}, parents: {len(self.parents)} " + f" transported items: {transported_items}"
