from typing import Dict


class SymbolicTable:

    def __init__(self):
        self._table = {}

    def get(self, var_name):
        """Fetch the value of a symbol
        """
        return self._table[var_name]

    def update(self, var_name, value=None):
        """Update the value of a symbol
        """
        self._table[var_name] = value if value is not None else var_name

    @property
    def table(self) -> Dict:
        """Returns the Symbolic Table

        Returns:
            Dict(vars): Dict of variables
        """
        return dict(self._table)
