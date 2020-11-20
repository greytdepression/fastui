import os
from typing import Callable

class StyledOutput:

    def __init__(
        self,
        header: Callable[[str], str] = lambda txt: f'{txt.title()}:',
        indent: int = 2,
        list: Callable[[str], str] = lambda lst: ', '.join(map(str, lst)),
        parameter: Callable[[str], str] = lambda txt: f'<{txt.lower()}>',
        table_alternate_rows: bool = True,
    ):
        self.header = header
        self.indent = indent
        self.list = list
        self.parameter = parameter
        self.parameters = lambda names: ' '.join(map(self.parameter, names))
        self.table_alternate_rows = table_alternate_rows

