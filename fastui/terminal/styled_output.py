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

	# def indent(self, txt, amount=None):
	# 	if amount is None:
	# 		amount = self.indent

	# 	atype(amount, int)

	# 	if type(txt) == list:
	# 		txt = os.linesep.join(txt)

	# 	txt = str(txt)

	# 	lines = os.linesep.join(map(lambda e: e.rjust(len(e) + amount), \
	# 		txt.split(os.linesep)))

	# 	return lines

