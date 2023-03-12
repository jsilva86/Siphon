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
                #print(node, node.sons[0].sons[0].sons[0].sons[0])
                break
        print("------")
        for instruction in self.head.true_path.instructions:
            print(instruction)
        
        self.cfg_to_dot("test.dot")
            
        #print(self.head.instructions[0],self.head.instructions[1], self.head.instructions[2])        
            
    def build_cfg_recursive(self, node: Node, current_block: Block, is_false_path: bool = False):
        #print("exploring", node)

        match node.type:
            case NodeType.IF:
                
                # create new block and set the next block in current block to it
                true_block = Block()
                current_block.true_path = true_block
                true_block.prev_block = current_block
                
                # add if check to current block 
                current_block.add_instruction(node)
                                
                self.build_cfg_recursive(node.son_true, true_block)

                # check for else case
                if node.son_false and node.son_false.type != NodeType.ENDIF:
                    false_block = Block()
                    current_block.false_path = false_block
                    false_block.prev_block = current_block
                    
                    self.build_cfg_recursive(node.son_false, false_block, True)
                    
            # case NodeType.STARTLOOP:
            #     print("Entrei loop")
            case NodeType.STARTLOOP:
                # start block
                # need to verify sons[1] of if to get out of loop
                pass
            case NodeType.ENDIF:
                #print("sair if", node, current_block)
                
                # FIXME this causes empty blocks if their is no instruction after it
                new_block = Block()
                current_block.true_path = new_block
                new_block.prev_block = current_block
                
                # avoid processing the same block after finishing if and else block
                if not is_false_path:
                    self.build_cfg_recursive(node.sons[0], new_block)    
            
            case NodeType.ENDLOOP:
                # go back to previous block
                pass
            case _:
                # add instruction to current block
                current_block.add_instruction(node)

                if not node.sons:
                    return
                self.build_cfg_recursive(node.sons[0], current_block, is_false_path)
                
    def cfg_to_dot(self, filename: str):
        """
            Export the function to a dot file
        Args:
            filename (str)
        """
        with open(filename, "w", encoding="utf8") as f:
            f.write("digraph{\n")
            block = self.head
            while block != None:
                f.write(
                    f'{str(block.id)}[label="{[[str(ir) for ir in instruction.irs] for instruction in block.instructions]}"];\n'
                )

                if block.true_path:
                    f.write(f'{block.id}->{block.true_path.id}[label="True"];\n')
                    
                if block.false_path:
                    f.write(f'{block.id}->{block.false_path.id}[label="False"];\n')
                    
                # TODO missing false path    
                block = block.true_path          

            f.write("}\n")
             
             
    