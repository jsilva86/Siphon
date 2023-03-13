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
            
            
    def build_cfg_recursive(self, node: Node, current_block: Block, is_false_path = False):
        match node.type:
            case NodeType.IF:

                # create new block and set the next block in current block to it
                true_block = Block()
                current_block.true_path = true_block
                true_block.prev_block = current_block
                
                # add if check to current block 
                current_block.add_instruction(node)
                
                self.build_cfg_recursive(node.son_true, true_block, is_false_path)
                
                # avoid creating a new block if else case does not exist
                if node.son_false.type == NodeType.ENDIF:
                    self.build_cfg_recursive(node.son_false, current_block, True)
                    
                else:
                    false_block = Block()
                    current_block.false_path = false_block
                    false_block.prev_block = current_block
                    
                    self.build_cfg_recursive(node.son_false, false_block, is_false_path)
                    
            case NodeType.ENDIF:
                print(node.sons[0])                
                if not node.sons:
                    return
                    
                if node.sons[0].type == NodeType.ENDIF:
                    # avoid creating a new block if next instruction is the end of an if
                    self.build_cfg_recursive(node.sons[0], current_block, is_false_path)
                
                else:
                    new_block = Block()
                    new_block.prev_block = current_block
                    
                    # distinguish between end of if/else
                    if not is_false_path:
                        current_block.true_path = new_block
                    else:
                        current_block.false_path = new_block
                        
                    self.build_cfg_recursive(node.sons[0], new_block, is_false_path)
                        
            case NodeType.STARTLOOP:
                # currently ethereum only allows for 1 variable to be in the scope of the for loop
                # https://github.com/ethereum/solidity/issues/13212
                
                init_node = node.fathers[0] # int i = 0
                
                # add instructions to current block
                current_block.add_instruction(init_node)
                current_block.add_instruction(node)
                
                self.build_cfg_recursive(node.sons[0], current_block, is_false_path)
                
            case NodeType.IFLOOP:
                # create a block for the body of the loop
                loop_block = Block()
                current_block.true_path = loop_block
                loop_block.prev_block = current_block
                
                # add if check to current block 
                current_block.add_instruction(node)
                
                self.build_cfg_recursive(node.son_true, loop_block, is_false_path)
                
                if node.son_false.sons:
                    # create new block and set the next block in current block to it
                    end_block = Block()
                    current_block.false_path = end_block
                    end_block.prev_block = current_block
                    
                    self.build_cfg_recursive(node.son_false.sons[0], end_block, is_false_path)
                
            case NodeType.ENDLOOP:
                #print(node.sons[0])
                pass
            case _:
                # add instruction to current block
                current_block.add_instruction(node)
                        
                if node.sons:   
                    # found a loop
                    if node.sons[0].type == NodeType.IFLOOP:
                        current_block.true_path = current_block.prev_block
                            
                        self.build_cfg_recursive(node.sons[0].son_false, current_block, is_false_path)
                        
                    else:
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
        
        # print("----")
        # for instruction in block.instructions:
        #     print(instruction)
        
        if not block:
            return
        
        file.write(
            f'{str(block.id)}[label="{[str(instruction) for instruction in block.instructions]}"];\n'
        )

        if block.true_path:
            file.write(f'{block.id}->{block.true_path.id}[label="True"];\n')
            
            if block.true_path.instructions[-1].type != NodeType.IFLOOP: 
                self.cfg_to_dot_recursive(file, block.true_path)
            
        if block.false_path:
            file.write(f'{block.id}->{block.false_path.id}[label="False"];\n')
            self.cfg_to_dot_recursive(file, block.false_path)
            
        