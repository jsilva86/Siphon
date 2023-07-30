import os

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
        dir_path = os.path.join("output", "optimized_code")
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # Create the file path
        # TODO: create name for file (contract + function)
        file_path = os.path.join(dir_path, "output")

        starting_node = self.cfg.head

        with open(f"{file_path}.sol", "w", encoding="utf8") as f:
            # adds initial "{"
            self.generate_function_declaration(f)
            self.generate_function_body(f, starting_node, set())
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

        file.write(func_declaration)

    def generate_function_args(self):
        if not self.cfg.function.parameters:
            return ""

        func_args = []

        # FIXME: some variables omit the type...
        for arg in [str(t) for t in self.cfg.function.parameters]:
            variable = self.cfg.function.variables_as_dict.get(arg)
            formatted_arg = f"{str(variable.type)} {variable.location} {arg}"
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

    def generate_function_body(
        self, file, current_block: Block, visited_source_lines: set
    ):
        if not current_block or current_block.was_converted_to_source:
            return

        # mark the block as generated to avoid duplicate code generation from false paths
        current_block.was_converted_to_source = True

        for instruction in current_block.instructions:
            # Slither Nodes can reference the same line multiple times,
            # for example, the "for loop" init, condition and update.
            # in those cases, the line only needs to be generated once
            if isinstance(instruction, Node):
                # close block
                # FIXME: same problem as loops.... ENDIF brings rest of line...
                if instruction.type in [NodeType.ENDIF, NodeType.ENDLOOP]:
                    file.write("}")
                    continue

                source_line_num = instruction.source_mapping.lines[0]
                if source_line_num not in visited_source_lines:
                    source_line = get_source_line_from_node(instruction).decode()
                    file.write(source_line)

                visited_source_lines.add(source_line_num)
            else:
                # Siphon Nodes are only referenced once
                file.write(str(instruction))

        # traverse both paths
        self.generate_function_body(file, current_block.true_path, visited_source_lines)
        self.generate_function_body(
            file, current_block.false_path, visited_source_lines
        )


def get_source_line_from_node(instruction: Node):
    # TODO: hardcoded filename...
    # start line of contract:
    # print(get_source_line_from_node(self.cfg._contract))
    # TODO wont work for multiline instructiosn: concat all lines[]
    return slitherSingleton.slither.crytic_compile.get_code_from_line(
        "sc-examples/Test.sol", instruction.source_mapping.lines[0]
    )


# export the singleton
codeGeneratorSingleton = CodeGenerator.get_instance()
