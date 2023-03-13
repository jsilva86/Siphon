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
                break
 
       
        self.cfg_to_dot("test.dot")
            
        #print(self.head.instructions[0],self.head.instructions[1], self.head.instructions[2])        
            
    def build_cfg_recursive(self, node: Node, current_block: Block, is_false_path = False):

        match node.type:
            case NodeType.IF:
                
                # create new block and set the next block in current block to it
                true_block = Block()
                current_block.true_path = true_block
                true_block.prev_block = current_block
                
                # add if check to current block 
                current_block.add_instruction(node)
                
                self.build_cfg_recursive(node.son_true, true_block)
                
                if node.son_false.type == NodeType.ENDIF:
                    # print(current_block.instructions[0], current_block.prev_block)
                    # false_block = Block()
                    # current_block.false_path = false_block
                    # false_block.prev_block = current_block
                    
                    self.build_cfg_recursive(node.son_false, current_block, True)
                    #current_block.false_path = node.son_false.sons[0]
                    
                #print(node.son_true, node.son_false)
                                
                # check for else case and avoid creating a block if no further instructions exist
                if node.son_false.type != NodeType.ENDIF:
                    false_block = Block()
                    current_block.false_path = false_block
                    false_block.prev_block = current_block
                    
                    self.build_cfg_recursive(node.son_false, false_block, is_false_path)
                    
                    
            # case NodeType.STARTLOOP:
            #     print("Entrei loop")
            case NodeType.STARTLOOP:
                # start block
                # need to verify sons[1] of if to get out of loop
                pass
            case NodeType.ENDIF:                
                # FIXME this causes empty blocks if there is no instruction after it
                if node.sons:
                    if node.sons[0].type != NodeType.ENDIF:
                        new_block = Block()
                        if not is_false_path:
                            current_block.true_path = new_block
                        else:
                            current_block.false_path = new_block
                        new_block.prev_block = current_block
                        self.build_cfg_recursive(node.sons[0], new_block, is_false_path)
                        
                    else:
                        self.build_cfg_recursive(node.sons[0], current_block, is_false_path)
            
            case NodeType.ENDLOOP:
                # go back to previous block
                pass
            case _:
                # add instruction to current block
                current_block.add_instruction(node)

                if node.sons:   
                    self.build_cfg_recursive(node.sons[0], current_block, is_false_path)
                
    def cfg_to_dot(self, filename: str):
        """
            Export the function to a dot file
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
            f'{str(block.id)}[label="{[[str(ir) for ir in instruction.irs] for instruction in block.instructions]}"];\n'
        )

        if block.true_path:
            file.write(f'{block.id}->{block.true_path.id}[label="True"];\n')
            
        if block.false_path:
            file.write(f'{block.id}->{block.false_path.id}[label="False"];\n')
            
        self.cfg_to_dot_recursive(file, block.true_path)
        self.cfg_to_dot_recursive(file, block.false_path)
            
    