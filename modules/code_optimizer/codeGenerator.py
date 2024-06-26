import os
from collections import deque
import re

from slither.core.cfg.node import Node, NodeType
from slither.core.declarations import Function

from modules.cfg_builder.cfg import CFG
from modules.cfg_builder.block import Block
from modules.slither.slitherSingleton import slitherSingleton


class CodeGenerator:
    """
    CodeGenerator class

    """

    instance = None

    _filename: str = ""

    _cfg: CFG = None

    @property
    def cfg(self) -> CFG:
        return self._cfg

    @property
    def filename(self) -> str:
        return self._filename

    @staticmethod
    def get_instance():
        if not CodeGenerator.instance:
            CodeGenerator.instance = CodeGenerator()
        return CodeGenerator.instance

    def init_instance(self, filename: str):
        self._filename = filename

    def update_instance(self, cfg: CFG):
        # optimized CFG
        self._cfg = cfg

    def generate_source_code(self):
        # Create the directory if it doesn't exist
        dir_path = os.path.join(
            "output",
            self.filename.replace(".sol", ""),
            self.cfg.contract.name,
            self.cfg.function.name,
        )
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # Create the file path
        file_path = os.path.join(dir_path, f"{self.cfg.function.name}-optimized")

        starting_node = self.cfg.head

        with open(f"{file_path}.sol", "w", encoding="utf8") as f:
            # adds initial "{"
            self.generate_function_declaration(f)
            self.generate_function_body(f, starting_node)
            # close function scope
            f.write("}")

    def generate_function_declaration(self, file):
        func_name = self.cfg.function.name
        func_args = self.generate_function_args()
        visibility = self.cfg.function.visibility
        stateMutability = self.generate_state_mutability()
        return_types = self.generate_return_types()

        # function func_name(params) visibilityModifier stateMutabilityModifier returns (returnType) {
        func_declaration = f"function {func_name} {func_args} {visibility} {stateMutability} {return_types} {{"

        file.write(func_declaration + "\n")

    def generate_function_args(self):
        if not self.cfg.function.parameters:
            return "()"

        func_args = []

        # FIXME: some variables omit the type...
        for arg in [str(t) for t in self.cfg.function.parameters]:
            variable = self.cfg.function.variables_as_dict.get(arg)
            if variable.type.is_dynamic:
                formatted_arg = f"{str(variable.type)} {variable.location} {arg}"
            else:
                formatted_arg = f"{str(variable.type)} {arg}"
            func_args.append(formatted_arg)

        return f"( {', '.join(func_args)} )"

    def generate_state_mutability(self):
        if self.cfg.function.view:
            return "view"
        elif self.cfg.function.pure:
            return "pure"
        elif self.cfg.function.payable:
            return "payable"
        return ""

    def generate_return_types(self):
        if not self.cfg.function.return_type:
            return ""

        return_types = [str(type) for type in self.cfg.function.return_type]
        return f"returns ( {', '.join(return_types)} )"

    def generate_function_body(self, file, root_block: Block):
        if not root_block:
            return

        # Use a deque for custom pre-order traversal
        queue = deque([root_block])
        false_queue = deque([])

        reached_end_if = False

        current_block = None

        while queue or false_queue:
            # After finding an ENDIF, see if any false paths are still unvisited, if they are explore them
            # safeguard against no ELSE case, since both of them point to the same block: just do true path
            if (
                false_queue
                and reached_end_if
                and not (
                    current_block
                    and current_block.true_path
                    and current_block.true_path.id == false_queue[-1].id
                )
            ):
                # else branch exists
                is_loop_end = current_block.instructions[-1].type == NodeType.ENDLOOP
                current_block = false_queue.pop()

                # loop false branches are not ELSE
                if not is_loop_end:
                    if (
                        current_block.instructions
                        and current_block.instructions[0].type != NodeType.IF
                    ):
                        file.write("else {")
                    else:
                        file.write("else ")

            # process trailing false paths
            elif not queue and false_queue:
                current_block = false_queue.pop()

            else:
                current_block = queue.pop()

            reached_end_if = False
            if current_block.was_converted_to_source:
                continue

            # Mark the block as generated to avoid duplicate code generation from false paths
            current_block.was_converted_to_source = True
            for index, instruction in enumerate(current_block.instructions):
                # Slither Nodes can reference the same line multiple times,
                # for example, the "for loop" init, condition, and update.
                # in those cases, the line only needs to be generated once
                if isinstance(instruction, Node):
                    # ignore loop init instruction, START LOOP label and loop increment
                    # IFLOOP instruction handles all of them
                    # modified for loops are inline by siphon nodes and trailing instructions are removed here
                    if (
                        index + 1 != len(current_block.instructions)
                        and current_block.instructions[index + 1].type
                        in [NodeType.STARTLOOP, NodeType.ENDLOOP]
                    ) or instruction.type == NodeType.STARTLOOP:
                        continue

                    if instruction.type in [
                        NodeType.ENDIF,
                        NodeType.ENDLOOP,
                        NodeType.RETURN,
                    ]:
                        # returns have an implicit closure end
                        if instruction.type == NodeType.RETURN:
                            source_line = get_source_line_from_node(
                                self.filename, instruction
                            )
                            file.write(source_line + "\n")

                        reached_end_if = True
                        file.write("}\n")
                        continue

                    source_line = get_source_line_from_node(self.filename, instruction)
                    file.write(source_line + "\n")

                else:
                    # Siphon Nodes are only referenced once
                    file.write(str(instruction) + "\n")

            if current_block.false_path:
                false_queue.append(current_block.false_path)
            if current_block.true_path:
                queue.append(current_block.true_path)


def get_source_line_from_node(filename: str, instruction: Node):
    raw_line = slitherSingleton.slither.crytic_compile.get_code_from_line(
        filename, instruction.source_mapping.lines[0]
    ).decode()

    start = instruction.source_mapping.starting_column - 1
    end = instruction.source_mapping.ending_column - 1

    # barebones information from line
    # ex: if (x < 60) -> x < 60
    source_line = raw_line[start:end]

    match instruction.type:
        case NodeType.IF:
            return f"if ({source_line}) {{"
        case NodeType.IFLOOP:
            # match content inside parentheses
            pattern = r"\((?:[^()]*\([^()]*\)|[^()]+)\)"
            content = re.findall(pattern, raw_line)[0]
            return f"for{content} {{"

        case _:
            return f"{source_line};"


# export the singleton
codeGeneratorSingleton = CodeGenerator.get_instance()
