from slither.core.declarations import Function, Contract
from slither.core.cfg.node import NodeType, Node

from lib.cfg_builder.block import Block

class CFG:
    """
    CFG class

    """
    def __init__(self, contract: Contract, function: Function):
        self._contract: Contract = contract
        self._function: Function = function
        
        # starting block
        self._head: Block = Block()
        
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
    
    
    def build_cfg(self):

        for node in self.function.nodes:
            if node.type != NodeType.ENTRYPOINT:
                # find the first node with instructions
                self.build_cfg_recursive(node, self._head)
                break
 
        s = self._head
        
        # while s != None:
        #     print(s)
        #     s = s.true_path
            
        self.cfg_to_dot("test.dot")
                   
    def build_cfg_recursive(
        self, 
        node: Node,
        current_block: Block,
        is_false_path = False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None
    ):
        
        if true_path_loop_depth is None:
           true_path_loop_depth = []
           
        if false_path_loop_depth is None:
           false_path_loop_depth = []

        match node.type:
            case NodeType.IF:
                self.handle_if_case(node, current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
                    
            case NodeType.ENDIF:
                self.handle_end_if_case(node, current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
                        
            case NodeType.STARTLOOP:
                self.handle_start_loop_case(node, current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
                
            case NodeType.IFLOOP:      
                self.handle_if_loop_case(node, current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
                        
            case _:
                self.handle_default_case(node, current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
                
    def handle_if_case(
        self, 
        node: Node,
        current_block: Block,
        is_false_path = False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None
    ):
        true_block = self.create_new_block(current_block, False, [node])
        self.build_cfg_recursive(node.son_true, true_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
        
        # avoid creating a new block if else case does not exist
        if node.son_false.type == NodeType.ENDIF:
            self.build_cfg_recursive(node.son_false, current_block, True)
            
        else:
            false_block = self.create_new_block(current_block, True)              
            self.build_cfg_recursive(node.son_false, false_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
                     
    def handle_end_if_case(
        self, 
        node: Node,
        current_block: Block,
        is_false_path = False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None
    ):
        if not node.sons:
            return
            
        if node.sons[0].type == NodeType.ENDIF:
            # avoid creating a new block if next instruction is the end of an if
            self.build_cfg_recursive(node.sons[0], current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
        
        else:       
            next_block = self.create_new_block(current_block, is_false_path)      
            self.build_cfg_recursive(node.sons[0], next_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
            
    def handle_start_loop_case(
        self, 
        node: Node,
        current_block: Block,
        is_false_path = False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None
    ):
        # currently ethereum only allows for 1 variable to be in the scope of the for loop
        # https://github.com/ethereum/solidity/issues/13212
        
        # FIXME this is not always needed
        init_node = node.fathers[0] # int i = 0

        # add instructions to current block
        current_block.add_instruction(init_node)
        current_block.add_instruction(node)
        
        # add current loops
        true_path_loop_depth.append(current_block)
        false_path_loop_depth.append(current_block)
        
        self.build_cfg_recursive(node.sons[0], current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
        
    def handle_if_loop_case(
        self, 
        node: Node,
        current_block: Block,
        is_false_path = False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None
    ):
        loop_true_block = self.create_new_block(current_block, False, [node])       
        self.build_cfg_recursive(node.son_true, loop_true_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
        
        if node.son_false.sons:           
            loop_false_block = self.create_new_block(current_block, True)
            self.build_cfg_recursive(node.son_false.sons[0], loop_false_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
            
    def handle_default_case(
        self, 
        node: Node,
        current_block: Block,
        is_false_path = False,
        true_path_loop_depth: list["Block"] = None,
        false_path_loop_depth: list["Block"] = None
    ):
        # add instruction to current block
        current_block.add_instruction(node)
        
        if node.type == NodeType.ENDLOOP:
            return
                
        if node.sons:   
            # found a loop
            if node.sons[0].type == NodeType.IFLOOP:
                
                if is_false_path:
                    current_block.true_path = false_path_loop_depth.pop()
                else:
                    current_block.true_path = true_path_loop_depth.pop()
                    
                self.build_cfg_recursive(node.sons[0].son_false, current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
                
            else:
                self.build_cfg_recursive(node.sons[0], current_block, is_false_path, true_path_loop_depth, false_path_loop_depth)
    
    def create_new_block(self, current_block: Block, is_false_path = False, instructions: list["Node"] = None):
        new_block =  Block()
        
        self.set_block_paths(current_block, new_block, is_false_path)
        
        if instructions:
            for instruction in instructions:
                current_block.add_instruction(instruction)
        
        return new_block
        
    def set_block_paths(self, current_block: Block, new_block: Block, is_false_path = False):
        if not is_false_path:
            current_block.true_path = new_block
        else:
            current_block.false_path = new_block
        new_block.prev_block = current_block
    
                
    def cfg_to_dot(self, filename: str):
        """
            Export the function to a dot file. Useful for debugging.
        Args:
            filename (str)
        """
        with open(filename, "w", encoding="utf8") as f:
            f.write("digraph{\n")
            self.cfg_to_dot_recursive(f, self.head)          
            f.write("}\n")
             
    def cfg_to_dot_recursive(self, file, block: Block):    
        if not block:
            return
        
        file.write(
            f'{str(block.id)}[label="{[str(instruction) for instruction in block.instructions]}"];\n'
        )

        if block.true_path:
            # FIXME this causes double arrows
            file.write(f'{block.id}->{block.true_path.id}[label="True"];\n')
            
            if not block.true_path.printed:
                block.true_path.printed = True
                self.cfg_to_dot_recursive(file, block.true_path)
            
        if block.false_path:
            file.write(f'{block.id}->{block.false_path.id}[label="False"];\n')
            self.cfg_to_dot_recursive(file, block.false_path)
            
        