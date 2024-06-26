from typing import List, Dict, Union
from random import randint

from slither.core.cfg.node import Node
from slither.core.variables.state_variable import StateVariable

from modules.code_optimizer.siphonNode import SiphonNode


class Block:
    """
    Block class

    """

    def __init__(self):
        # instructions inside the block
        self._instructions: List[Union["Node", "SiphonNode"]] = []

        # storage accesses
        self._state_variables_written: Dict[str, int] = {}
        self._state_variables_read: Dict[str, int] = {}

        # paths to follow in case of a new block or branch conditions
        self._true_path: Block = None
        self._false_path: Block = None
        self._prev_block: Block = None

        # used by the CFG builder to ensure that loops are only traversed once
        self._visited: bool = False

        # TODO is this good enough?
        self._id: int = randint(0, 10000)

        # reachability via paths, used to remove P1/P2 false positives in the PatternMatcher
        self._reachability: list[int] = []

        # in the CodeGenerator avoid generating again when false path ends
        self._was_converted_to_source: bool = False

    def __str__(self):
        return "\n".join(
            map(repr, [str(instruction) for instruction in self.instructions])
        )

    @property
    def instructions(self) -> List["Node"]:
        """Returns the list of instructions within this block

        Returns:
            list(Node): list of instructions
        """
        return list(self._instructions)

    @property
    def true_path(self) -> "Block":
        """Returns the true path

        Returns:
            Block: Next Block
        """
        return self._true_path

    @property
    def false_path(self) -> "Block":
        """Returns the false path

        Returns:
            Block: Next Block
        """
        return self._false_path

    @property
    def prev_block(self) -> "Block":
        """Returns the previous Block

        Returns:
            Block: Previous Block
        """
        return self._prev_block

    @property
    def id(self) -> int:
        """Returns Block Id

        Returns:
            id: Block Id
        """
        return self._id

    @property
    def state_variables_written(self) -> Dict[str, int]:
        """
        dict(StateVariable): State variables written
        """
        return self._state_variables_written

    @property
    def state_variables_read(self) -> Dict[str, int]:
        """
        dict(StateVariable): State variables read
        """
        return self._state_variables_read

    @property
    def was_converted_to_source(self) -> bool:
        """
        bool(was_converted_to_source): Was Block already converted to source code
        """
        return self._was_converted_to_source

    @property
    def visited(self) -> bool:
        """
        Returns: was the block already visited
        """
        return self._visited

    @true_path.setter
    def true_path(self, value):
        self._true_path = value

    @false_path.setter
    def false_path(self, value):
        self._false_path = value

    @prev_block.setter
    def prev_block(self, value):
        self._prev_block = value

    @id.setter
    def id(self, value):
        self._id = value

    @visited.setter
    def visited(self, value):
        self._visited = value

    @was_converted_to_source.setter
    def was_converted_to_source(self, value):
        self._was_converted_to_source = value

    def add_instruction(self, instruction: Node):
        self._instructions.append(instruction)

    def add_state_variable_written(self, variable: StateVariable):
        symbol = variable.name

        if variable.name in self._state_variables_written:
            self._state_variables_written[symbol] += 1
        else:
            self._state_variables_written[symbol] = 1

    def add_state_variable_read(self, variable: StateVariable):
        symbol = variable.name

        if variable.name in self._state_variables_read:
            self._state_variables_read[symbol] += 1
        else:
            self._state_variables_read[symbol] = 1
