from typing import Dict
from enum import Enum

from z3 import *


class SymbolType(Enum):
    PRIMITIVE = 1
    MAPPING = 2
    ARRAY = 3


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
            print(scope)
            symbol_list = self._table[scope]
            symbols.extend(
                f"Scope: {scope}, Symbol: {symbol.name}, Value: {symbol.value}, Type: {symbol.type}"
                for symbol in symbol_list
            )
        return "\n".join(symbols)

    def push_symbol(self, symbol_name: str, type: SymbolType, loop_scope: int = 0):
        """
        Initialize a symbol in the dictionary with the given symbol name, type, and scope.

        Args:
            symbol_name: The name of the symbol to initialize.
            type: The type of the symbol. Defaults to None.
            scope: The key to identify the list in the dictionary where the symbol should be inserted.
                Defaults to 0.
        """
        if existing_symbol := self.get_symbol(symbol_name):
            # Symbol already exists, move it to the correct key in the table
            old_scope = existing_symbol.loop_scope
            if old_scope != loop_scope:
                self._table[old_scope].remove(existing_symbol)
                self._table.setdefault(loop_scope, []).append(existing_symbol)
                existing_symbol.loop_scope = loop_scope
                existing_symbol.is_loop_bounded = bool(loop_scope)
        else:
            symbol = Symbol(symbol_name, type, loop_scope)
            self._table.setdefault(loop_scope, []).append(symbol)

    def update_symbol(self, symbol_name: str, value=None):
        """
        Update the value of a symbol in the dictionary with the given symbol name and scope.

        Args:
            symbol_name: The name of the symbol to update.
            value: The new value to assign to the symbol. Defaults to None.
            scope: The key to identify the list in the dictionary where the symbol is located.
                   Defaults to 0.
        """

        if symbol := self.get_symbol(symbol_name):
            symbol.value = value if value is not None else Int(symbol_name)

    def get_symbol(self, symbol_name: str) -> Symbol:
        # sourcery skip: remove-unnecessary-cast
        """
        Retrieve the symbol from the dictionary based on the given symbol name.

        Args:
            symbol_name: The name of the symbol to retrieve.

        Returns:
            The Symbol object corresponding to the given symbol name, or None if not found.
        """

        # Iterate from highest to lowest scope, since it's more likely that the symbol is in an higher scope
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
        return (
            symbol.value
            if (symbol := self.get_symbol(symbol_name))
            else Int(symbol_name)
        )

    @property
    def table(self) -> Dict:
        """Returns the Symbolic Table

        Returns:
            Dict(vars): Dict of variables
        """
        return self._table


class Symbol:
    def __init__(self, name: str, type: SymbolType, loop_scope: int = 0):
        # the name of the symbol
        self._name: str = name

        # the current value of the symbol
        self._value = Int(name)

        # symbol type
        self._type: SymbolType = type

        # Symbol was declared in the scope of a loop
        self._is_loop_bounded: bool = bool(loop_scope)

        # Scope where Symbol was declared
        self._loop_scope: int = loop_scope

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

    @property
    def type(self):
        """
        Returns:
            Symbol's type
        """
        return self._type

    @property
    def loop_scope(self):
        """
        Returns:
            Returns the scope where the Symbol was declared
        """
        return self._loop_scope

    @property
    def is_loop_bounded(self):
        """
        Returns:
            True if the Symbol is declared within a loop
        """
        return self._is_loop_bounded

    @value.setter
    def value(self, new_value):
        """
        Setter for the value of the symbol.

        Args:
            new_value: The new value to assign to the symbol.
        """
        self._value = new_value

    @type.setter
    def type(self, new_type):
        """
        Setter for the type of the symbol.

        Args:
            new_type: The new type of the symbol.
        """
        self._type = new_type

    @loop_scope.setter
    def loop_scope(self, new_scope):
        """
        Setter for the scope of the symbol.

        Args:
            new_scope: The new scope of the symbol.
        """
        self._loop_scope = new_scope

    @is_loop_bounded.setter
    def is_loop_bounded(self, is_loop_bounded):
        """
        Setter for the scope of the symbol.

        Args:
            new_scope: The new scope of the symbol.
        """
        self._is_loop_bounded = is_loop_bounded

    def is_primitive(self):
        return self.type is SymbolType.PRIMITIVE

    def is_mapping(self):
        return self.type is SymbolType.MAPPING

    def is_array(self):
        return self.type is SymbolType.ARRAY
