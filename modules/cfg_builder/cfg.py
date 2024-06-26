import os
from typing import Dict
from random import randint

from slither.core.declarations import Function, Contract
from slither.core.cfg.node import NodeType, Node
from slither.core.variables.local_variable import LocalVariable
from slither.core.variables.state_variable import StateVariable
from slither.core.declarations import StructureContract

from modules.cfg_builder.block import Block


class CFG:
    """
    CFG class

    """

    def __init__(
        self, filename: str, contract: Contract, function: Function, export_cfg=False
    ):
        # pass along to other modules
        self._filename: str = filename
        self._contract: Contract = contract
        self._function: Function = function

        # starting block
        self._head: Block = Block()

        # visited nodes
        self._visited_nodes: dict = {}

        # visited blocks
        self._visited_blocks: dict = {}

        # for debugging
        self._export_cfg: bool = export_cfg

    def __hash__(self):
        # safeguard for older contracts
        if not self.contract.id or not self.function.id:
            return randint(0, 10000)
        return hash(self.contract.id + self.function.id)

    @property
    def function(self) -> Function:
        """Returns the function

        Returns:
            function: function instance
        """
        return self._function

    @property
    def contract(self) -> Contract:
        """Returns the contract

        Returns:
            contract: contract instance
        """
        return self._contract

    @property
    def head(self) -> Block:
        """Returns the starting block in the cfg
        Returns:
            head: head of the cfg
        """
        return self._head

    @property
    def visited_nodes(self) -> Dict:
        """Returns the mapping of visited nodes to their blocks

        Returns:
            Dict(vars): Dict of visited nodes to their blocks
        """
        return self._visited_nodes

    @property
    def visited_blocks(self) -> Dict:
        """Returns the mapping of visited blocks to their ids

        Returns:
            Dict(vars): Dict of visited blocks to their ids
        """
        return self._visited_blocks

    @property
    def export_cfg(self) -> bool:
        """Exports the CFG to a file

        Returns:
            bool: should export the CFG for debugging
        """
        return self._export_cfg

    def build_cfg(self):
        for node in self.function.nodes:
            if node.type != NodeType.ENTRYPOINT:
                # find the first node with instructions
                self.build_cfg_recursive(node, self._head)
                break

        if self.export_cfg:
            cfg_to_dot(
                self._filename,
                self.contract.name,
                self.function.name,
                self.function.name,
                self.head,
            )

    def build_cfg_recursive(
        self,
        node: Node,
        current_block: Block,
        is_false_path=False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None,
    ):
        if true_path_loop_depth is None:
            true_path_loop_depth = []

        if false_path_loop_depth is None:
            false_path_loop_depth = []

        match node.type:
            case NodeType.IF:
                self.handle_if_case(
                    node,
                    current_block,
                    is_false_path,
                    true_path_loop_depth,
                    false_path_loop_depth,
                )

            case NodeType.ENDIF:
                self.handle_end_if_case(
                    node,
                    current_block,
                    is_false_path,
                    true_path_loop_depth,
                    false_path_loop_depth,
                )

            case NodeType.STARTLOOP:
                self.handle_start_loop_case(
                    node,
                    current_block,
                    is_false_path,
                    true_path_loop_depth,
                    false_path_loop_depth,
                )

            case NodeType.IFLOOP:
                self.handle_if_loop_case(
                    node,
                    current_block,
                    is_false_path,
                    true_path_loop_depth,
                    false_path_loop_depth,
                )

            case _:
                self.handle_default_case(
                    node,
                    current_block,
                    is_false_path,
                    true_path_loop_depth,
                    false_path_loop_depth,
                )

    def handle_if_case(
        self,
        node: Node,
        current_block: Block,
        is_false_path=False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None,
    ):
        true_block = self.create_new_block(current_block, False, node)
        self.build_cfg_recursive(
            node.son_true,
            true_block,
            False,
            true_path_loop_depth,
            false_path_loop_depth,
        )

        # avoid creating a new block if else case does not exist
        if node.son_false.type == NodeType.ENDIF:
            self.build_cfg_recursive(node.son_false, current_block, True)

        else:
            false_block = self.create_new_block(current_block, True)
            self.build_cfg_recursive(
                node.son_false,
                false_block,
                True,
                true_path_loop_depth,
                false_path_loop_depth,
            )

    def handle_end_if_case(
        self,
        node: Node,
        current_block: Block,
        is_false_path=False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None,
    ):
        if not node.sons:
            return

        if node.sons[0].type == NodeType.ENDIF:
            # avoid creating a new block if next instruction is the end of an if

            # FIXME: this will only work for up to two nested IFS
            # Add additional ENDIF to close outside IF
            if (
                is_false_path
                and len(current_block.instructions) > 1
                and current_block.instructions[-2].type != NodeType.ENDIF
            ):
                current_block.add_instruction(node)

            self.build_cfg_recursive(
                node.sons[0],
                current_block,
                is_false_path,
                true_path_loop_depth,
                false_path_loop_depth,
            )

        # check if a block was already created in another path
        # avoid recursively checking an already traversed path,
        # instead just connect the path to the existing block
        elif created_block_id := self.visited_nodes.get(node.sons[0].node_id):
            created_block = self.visited_blocks[created_block_id]

            if is_false_path and current_block.instructions[-1].type == NodeType.IF:
                # else cases are in the false_path but not its subsequent instructions
                current_block.false_path = created_block
            else:
                current_block.true_path = created_block

        else:
            next_block = self.create_new_block(current_block, is_false_path)
            self.build_cfg_recursive(
                node.sons[0],
                next_block,
                False,
                true_path_loop_depth,
                false_path_loop_depth,
            )

    def handle_start_loop_case(
        self,
        node: Node,
        current_block: Block,
        is_false_path=False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None,
    ):
        # currently ethereum only allows for 1 variable to be in the scope of the for loop
        # https://github.com/ethereum/solidity/issues/13212

        # FIXME this is not always needed
        init_node = node.fathers[0]  # int i = 0

        loop_block = self.create_new_block(current_block, False, node)

        # add instructions to current block
        loop_block.add_instruction(node)
        loop_block.add_instruction(init_node)

        # add current loops
        true_path_loop_depth.append(loop_block)
        false_path_loop_depth.append(loop_block)

        self.build_cfg_recursive(
            node.sons[0],
            loop_block,
            is_false_path,
            true_path_loop_depth,
            false_path_loop_depth,
        )

    def handle_if_loop_case(
        self,
        node: Node,
        current_block: Block,
        is_false_path=False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None,
    ):
        loop_true_block = self.create_new_block(current_block, False, node)
        self.build_cfg_recursive(
            node.son_true,
            loop_true_block,
            is_false_path,
            true_path_loop_depth,
            false_path_loop_depth,
        )

        if node.son_false.sons:
            loop_false_block = self.create_new_block(current_block, True)
            self.build_cfg_recursive(
                node.son_false.sons[0],
                loop_false_block,
                is_false_path,
                true_path_loop_depth,
                false_path_loop_depth,
            )

    def handle_default_case(
        self,
        node: Node,
        current_block: Block,
        is_false_path=False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None,
    ):
        self.add_instruction_to_block(current_block, node)

        if node.type == NodeType.ENDLOOP:
            return

        if node.sons:
            # needed in the CodeGenerator to determine the closure of the IF
            if node.sons[0].type == NodeType.ENDIF:
                current_block.add_instruction(node.sons[0])

            # found a loop
            if node.sons[0].type == NodeType.IFLOOP:
                if is_false_path and false_path_loop_depth:
                    current_block.true_path = false_path_loop_depth.pop()
                elif true_path_loop_depth:
                    current_block.true_path = true_path_loop_depth.pop()

                self.build_cfg_recursive(
                    node.sons[0].son_false,
                    current_block,
                    is_false_path,
                    true_path_loop_depth,
                    false_path_loop_depth,
                )

            else:
                self.build_cfg_recursive(
                    node.sons[0],
                    current_block,
                    is_false_path,
                    true_path_loop_depth,
                    false_path_loop_depth,
                )

    def create_new_block(
        self, current_block: Block, is_false_path=False, init_instruction: Node = None
    ) -> Block:
        new_block = Block()
        self.visited_blocks[new_block.id] = new_block

        self.set_block_paths(current_block, new_block, is_false_path)

        if init_instruction:
            self.add_instruction_to_block(current_block, init_instruction)

        return new_block

    def set_block_paths(
        self, current_block: Block, new_block: Block, is_false_path=False
    ):
        if not is_false_path:
            current_block.true_path = new_block
        else:
            current_block.false_path = new_block
        new_block.prev_block = current_block

    def add_instruction_to_block(self, block: Block, instruction: Node):
        # add instruction to current block
        block.add_instruction(instruction)

        # keep track of storage accesses at a block level
        self.check_for_state_variables(block, instruction)

        # store the block where the instruction was first inserted
        if instruction.node_id not in self.visited_nodes:
            self.visited_nodes[instruction.node_id] = block.id

    def check_for_state_variables(self, block: Block, instruction: Node):
        if instruction.state_variables_written:
            [
                block.add_state_variable_written(s_instruction)
                for s_instruction in instruction.state_variables_written
            ]

        if instruction.state_variables_read:
            [
                block.add_state_variable_read(s_instruction)
                for s_instruction in instruction.state_variables_read
            ]

    def retrieve_function_args(self) -> list["LocalVariable"]:
        return self.function.parameters

    def retrieve_storage_variables(self) -> list["StateVariable"]:
        return self.contract.variables

    def retrieve_user_defined_data_structures(self) -> list["StructureContract"]:
        return self.contract.structures


def cfg_to_dot(
    dir: str, sub_dir: str, base_dir: str, filename: str, starting_node: Block
):
    """
        Export the function to a dot file. Useful for debugging.
    Args:
        filename (str)
    """

    # Create the directory if it doesn't exist
    dir_path = os.path.join(
        "output", dir.replace(".sol", ""), sub_dir, base_dir, "cfgs"
    )
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Create the file path
    file_path = os.path.join(dir_path, filename)

    with open(f"{file_path}.dot", "w", encoding="utf8") as f:
        f.write("digraph{\n")
        cfg_to_dot_recursive(f, starting_node, [])
        f.write("}\n")


def cfg_to_dot_recursive(file, block: Block, visited_list):
    if not block:
        return

    file.write(
        f'{str(block.id)}[label="{block.id} {[str(instruction) for instruction in block.instructions]}"];\n'
    )

    if block.true_path:
        # FIXME this causes double arrows
        file.write(f'{block.id}->{block.true_path.id}[label="True"];\n')

        if block.true_path.id not in visited_list:
            visited_list.append(block.true_path.id)
            cfg_to_dot_recursive(file, block.true_path, visited_list)

    if block.false_path:
        file.write(f'{block.id}->{block.false_path.id}[label="False"];\n')
        cfg_to_dot_recursive(file, block.false_path, visited_list)
