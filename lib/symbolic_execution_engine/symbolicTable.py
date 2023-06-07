from typing import Dict
from z3 import *


class SymbolicTable:
    def __init__(self):
        self._table: dict = {}

    def get(self, var_name: str):
        """Fetch the value of a symbol"""
        return self.table.get(var_name, var_name)

    def update(self, var_name: str, value=None):
        """Update the value of a symbol"""
        self._table[var_name] = value if value is not None else Int(var_name)

    @property
    def table(self) -> Dict:
        """Returns the Symbolic Table

        Returns:
            Dict(vars): Dict of variables
        """
        return self._table
