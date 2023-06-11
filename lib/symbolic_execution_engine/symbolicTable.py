from typing import Dict
from z3 import *


class SymbolicTable:
    def __init__(self):
        # maps each symbol to its scope
        self._table: dict[int, list[Symbol]] = {}

    def __str__(self):
        """
        Returns a string representation of the Symbolic Table.

        Returns:
            String representation of the Symbolic Table.
        """
        symbols = []
        sorted_scopes = sorted(self._table.keys())  # Sort scopes in ascending order

        for scope in sorted_scopes:
            symbol_list = self._table[scope]
            symbols.extend(
                f"Scope: {scope}, Symbol: {symbol.name}, Value: {symbol.value}"
                for symbol in symbol_list
            )
        return "\n".join(symbols)

    def get_symbol(self, symbol_name: str) -> Symbol:
        # sourcery skip: remove-unnecessary-cast
        """
        Retrieve the symbol from the dictionary based on the given symbol name.

        Args:
            symbol_name: The name of the symbol to retrieve.

        Returns:
            The Symbol object corresponding to the given symbol name, or None if not found.
        """

        # Iterate from highest scope to lowest, since it's more likely that the symbol is in an higher scope
        scopes = range(max(self._table.keys(), default=0), -1, -1)

        for scope in scopes:
            symbol_list = self._table.get(scope, [])
            for symbol in symbol_list:
                if symbol.name == str(symbol_name):
                    return symbol

        return None

    def get_symbol_value(self, symbol_name: str):
        """
        Retrieve the value of the symbol from the dictionary based on the given symbol name.

        Args:
            symbol_name: The name of the symbol to retrieve.

        Returns:
            The value of the symbol corresponding to the given symbol name, or itself if not found.
        """
        return symbol.value if (symbol := self.get_symbol(symbol_name)) else symbol_name

    def update_symbol(self, symbol_name: str, value=None, scope: int = 0):
        """
        Create or update a symbol in the dictionary with the given symbol name, value, and scope.

        Args:
            symbol_name: The name of the symbol to create or update.
            value: The value to assign to the symbol. Defaults to None.
            scope: The key to identify the list in the dictionary where the symbol should be inserted or updated.
                   Defaults to 0.
        """
        if symbol := self.get_symbol(symbol_name):
            symbol.value = value
        else:
            symbol = Symbol(symbol_name, value)
            self._table.setdefault(scope, []).append(symbol)

    @property
    def table(self) -> Dict:
        """Returns the Symbolic Table

        Returns:
            Dict(vars): Dict of variables
        """
        return self._table


class Symbol:
    def __init__(self, name: str, value=None):
        # the name of the symbol
        self._name: str = name

        # the current value of the symbol
        self._value = value if value is not None else Int(name)

    @property
    def name(self):
        """
        Returns:
            Symbol's name
        """
        return self._name

    @property
    def value(self):
        """
        Returns:
            Symbol's current value
        """
        return self._value

    @value.setter
    def value(self, new_value):
        """
        Setter for the value of the symbol.

        Args:
            new_value: The new value to assign to the symbol.
        """
        self._value = new_value
