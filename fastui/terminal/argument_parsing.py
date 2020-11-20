from os import get_terminal_size
from sys import argv
import os
from tabulate import tabulate
import numpy as np
from math import ceil
from .styled_output import StyledOutput
from typing import Union, List, Iterable, Any
from rich.console import Console
from .tables import SimplePlainTable


def atype(arg, typ):
	return type(arg) == typ

def atype_or_none(arg, typ):
	return type(arg) == typ or arg is None

def afunc(arg):
	return callable(arg)

def alisttype(lst, typ):
	b = type(lst) in (list, tuple)

	for e in lst:
		b &= type(e) == typ

	return b

def alisttypes(lst, typs, allow_none=False):
	b = type(lst) in (list, tuple)
	b &= type(typs) in (list, tuple)

	if not b: return False

	for e in lst:
		b &= (type(e) in typs) or (e is None and allow_none)

	return b

def from_dict(dic, key, default):
	if key in dic:
		return dic[key]

	return default

def print_indented(indent, *args):
	if indent == 0:
		print(*args)
	else:
		print(''.rjust(indent - 1, ' '), *args)

def parse_list_from_string(string, delims, typ):
	if delims[0] not in string:
		return typ(string)

	start = string.find(delims[0])
	end = str(string[::-1]).find(delims[1])

	string = string[start+1:end]

	elements = string.split(',') if ',' in string else string

	_list = []

	for e in elements:
		_list.append(parse_list_from_string(e, delims, typ))

	return _list

def parse_list(args, delims, typ):
	assert type(delims) in (list, tuple)

	if type(delims[0]) in (list, tuple):
		assert all(len(d) == 2 for d in delims)
		assert all(type(d[0]) == type(d[1]) == str for d in delims)

		starts = [d[0] for d in delims]

		k = 0
		for i in range(len(args[0])):
			if args[0][i] in starts:
				k = starts.index(args[0][i])
				break

		delims = delims[k]

	assert len(delims) == 2

	# Check whether there are parantheses
	assert any(b in args[0] for b in delims)

	# Check which argument is contains the closing paranthesis
	counter = args[0].count(delims[0])
	counter -= args[0].count(delims[1])

	end = 0
	while counter > 0:
		end += 1
		assert end < len(args)

		counter += args[end].count(delims[0])
		counter -= args[end].count(delims[1])
	end += 1

	# Build the list
	string = ''.join(args[:end])

	return parse_list_from_string(string, delims, typ), end


class Command:

	def __init__(
		self, 
		names: Iterable[str], 
		help_text: Optional[str] = None, 
		usage: Optional[str] = None, 
		commands: Optional[Iterable[Command]] = None,
		parameters: Optional[Iterable[Parameter]] = None, 
		options: Optional[Iterable[Option]] = None, 
		callback: Optional[Callable[[],]] = None,
		arg_parser: ArgumentParser
	) -> None:

		assert alisttype(names, str) and len(names) >= 1
		assert atype_or_none(help_text, str)
		assert atype_or_none(usage, str)
		assert alisttype(commands, Command) or commands is None
		assert alisttype(parameters, Command.Parameter) or parameters is None
		assert alisttype(options, Command.Option) or options is None
		assert afunc(callback) or callback is None
		assert atype(arg_parser, ArgumentParser)

		self._names = names
		self.help_text = help_text if help_text is not None else ''
		self.usage = usage if usage is not None else ''

		self._parameters = parameters if parameters is not None else []
		self._callback = callback if callback is not None else lambda *args, **kwargs: None
		self._arg_parser = arg_parser

		self._command_list = commands if commands is not None else []
		self._command_order = list(range(len(self._command_list)))
		self._command_keys = {}

		for k, cmd in enumerate(self._command_list):
			for name in cmd.names:
				self._command_keys[name] = k

		self._option_list = options
		self._option_order = list(range(len(options)))
		self._option_shortcuts = {}
		self._option_keys = {}
		self._option_data = {}

		for k, opt in enumerate(options):
			self._option_keys[opt.key] = k
			for sc in opt.shortcuts:
				self._option_shortcuts[sc] = k

	def __init__(
		self,
		names: Iterable[str], 
		help_text: Optional[str] = None, 
		usage: Optional[str] = None, 
		commands: Optional[Iterable[Command]] = None,
		parameter_interpreters: Optional[Iterable[Callable]], 
		parameter_descriptors: Optional[Iterable[str]],
		options: Optional[Iterable[Option]] = None, 
		callback: Optional[Callable[[],]] = None,
		arg_parser: ArgumentParser
	) -> None:
		self.__init__(
			names, 
			help_text, 
			usage, 
			commands,
			Command.Parameter(
				list(parameter_interpreters),
				list(parameter_descriptors)
			),
			options, 
			callback
		)

	@property
	def names(self):
		return self._names

	@property
	def names_str(self):
		return ', '.join(self._names)

	def parse(
		self, 
		start_index: int = 1, 
		argument_string: str = None,
		argument_list: str = None
	) -> None:

		# Clear out all option data
		self._option_data.clear()

		args = []
		if argument_string is None and argument_list is None:
			args = argv[start_index:]
		elif argument_list is not None:
			args = argument_list[start_index:]
		else:
			args = argument_string.split(' ')[start_index:]

		# There are more arguments to be parsed
		if len(args) > 0:
			# Check whether we start with a command
			for c in commands:
				if c.name == args[0]:
					c.parse(argument_list=args)
					return

			# Now the rest of the arguments should all be options!
			k = start_index
			while k < len(args):
				# This is an option
				if args[k].startswith('-'):
					opt_sc = args[k].replace('-', '')
					opt = self._option_list[self._option_shortcuts[opt_sc]]

					data, l = opt.parse(args[k+1:])

					self._option_data[opt.key] = data

					k += l
					k += 1

		# Call the callback function
		self._callback(**self._option_shortcuts)

	def command(self, name: str) -> 'Command':
		assert name in self._command_keys

		return self._command_list[self._command_keys[name]]

	def option(self, name: str) -> 'Option':
		assert name in self._option_keys

		return self._option_list[self._option_keys[name]]

	def add_command(self, command, index=None):

		# Check commands are of the correct type
		atype(command, self.Command)
		atype_or_none(index, int)

		# Add command to the list
		command_index = len(self._command_list)
		self._command_list.append(command)

		# Add command name to the dictionary
		self._command_keys[command.name] = command_index

		# Set the arguments index in the list of all arguments
		if index is None or index < 0 or index > command_index:
			self._command_order.append(command_index)
		else:
			self._command_order.insert(index, command_index)

	def add_command(
		self,
		names: Iterable[str], 
		help_text: Optional[str] = None, 
		usage: Optional[str] = None, 
		commands: Optional[Iterable[Command]] = None,
		parameter_interpreters: Optional[Iterable[Callable]], 
		parameter_descriptors: Optional[Iterable[str]],
		options: Optional[Iterable[Option]] = None, 
		callback: Optional[Callable[[],]] = None,
		index: Optional[int] = None
	) -> None:
		cmd = Command(
			names,
			help_text,
			usage,
			commands,
			parameter_interpreters,
			parameter_descriptors,
			options,
			callback,
			self._arg_parser
		)

		self.add_command(cmd, index)

	def add_option(self, option, index=None):

		# Check options are of the correct type
		atype(option, self.Option)
		atype_or_none(index, int)

		# Option key must not have been chosen yet!
		assert option.key not in self._option_data

		# Add option to the list
		option_index = len(self._option_list)
		self._option_list.append(option)

		# Add option shortcuts to the dictionary
		for key in option.shortcuts:
			self._option_shortcuts[key] = option_index

		# Set the option's index in the list of all options
		if index is None or index < 0 or index > option_index:
			self._option_order.append(option_index)
		else:
			self._option_order.insert(index, option_index)

		# Add option to the data dictionary
		self._option_data[option.key] = None

	def add_option(
		self,

	) -> None:
		pass

	def __help_option__(self):
		def output(self):
			# Usage section
			if self.usage is not None:
				con.print(self.style.header('usage'))
				con.print(self.style.indent(self.usage))


			sections = []

			# Commands section
			command_table = []

			for k in self._command_order:
				cmd = self._command_list[k]
				lhs = ' '.join([self.style.list(cmd.names_str),
					self.style.parameters(cmd.parameter_descriptors)])
				command_table.append([lhs, cmd.help_text])

			if len(command_table) > 0:
				cmd_sec = SimplePlainTable.Section(
					self.style.header('commands'),
					command_table
				)
				sections.append(cmd_sec)
			
			# Options section
			options_table = []

			for k in self._option_order:
				opt = self._option_list[k]
				lhs = ' '.join([self.style.list(opt.shortcuts_str), \
					self.style.parameters(opt.parameter_descriptors)])
				options_table.append([lhs, opt.help_text])

			if len(options_table) > 0:
				cmd_sec = SimplePlainTable.Section(
					self.style.header('options'),
					options_table
				)
				sections.append(cmd_sec)

			table = SimplePlainTable(
				*sections, 
				indentation=self._arg_parser.style.std_indent,
				highlight_rows=self._arg_parser.style.table_alternate_rows,
				header_style=self._arg_parser.style.header
			)
			table.print()

		callback = lambda *args, **kwargs: output(self)
		help_option = self.Option(
			'help', 
			'Show help.', 
			['h', 'help'], [], [], callback
		)

		self.add_option(help_option)

	def add_version_option(
		self, 
		name: str, 
		version: str,
		text: str = '{name} - version {version}', 
		index: int =1
	):
		atype(name, str)
		atype(version, str)
		atype(text, str)
		atype_or_none(index, int)

		opt = self.Option(
			'version', 
			'V', 'version',
			lambda *args, **kwargs: print(text.format(name=name, version=version))
		)

		self.add_option(opt, index)

	def add_simple_option(
		self, 
		name: str, 
		*shortcuts: str, 
		callback: Callable, 
		help_text: str
	):
		opt = Command.Option(
			name, 
			help_text, 
			shortcuts, 
			[], 
			[],
			callback
		)
		self.add_option(opt)

	def add_int_option(
		self, 
		name: str, 
		*shortcuts: str, 
		callback: Callable, 
		parameter_descriptor: str,
		help_text: str
	):
		opt = Command.Option(
			name, 
			help_text, 
			shortcuts,
			[lambda args: int(args[0].strip()), 1],
			[parameter_descriptor], 
			callback
		)
		self.add_option(opt)

	def add_float_option(
		self, 
		name: str, 
		*shortcuts: str,
		callback: Callable,
		parameter_descriptor: str,
		help_text: str
	):
		opt = Command.Option(
			name, 
			help_text, 
			shortcuts,
			[lambda args: float(args[0].strip()), 1],
			[parameter_descriptor], 
			callback
		)
		self.add_option(opt)

	def add_string_option(
		self, 
		name: str, 
		*shortcuts: str, 
		callback: Callable, 
		parameter_descriptor: str,
		help_text: str
	):
		opt = Command.Option(
			name, 
			help_text, 
			shortcuts,
			[lambda args: args[0].strip(), 1],
			[parameter_descriptor], 
			callback
		)
		self.add_option(opt)

	def add_list_option(
		self, 
		name: str, 
		*shortcuts: str, 
		element_parser: Callable[[List[str]], Any],
		callback: Callable, 
		parameter_descriptor: str, 
		help_text: str
	):
		opt = Command.Option(
			name, 
			help_text, 
			shortcuts,
			[lambda args: parse_list(args, element_parser)],
			[parameter_descriptor], 
			callback
		)
		self.add_option(opt)

	def add_selection_option(self, name, shortcuts, valid_parameters, \
		parameter_descriptors, callback, help_text):
		


	class Option:
		def __init__(
			self, 
			key: str, 
			help_text: Optional[str], 
			shortcuts: Iterable[str],
			parameters: Iterable[Command.Parameter], 
			callback: Callable
		) -> None:
			atype(key, str)
			atype_or_none(help_text, str)
			atype(shortcuts, list)
			alisttype(parameters, Command.Parameter)
			afunc(callback)
			# atype(command, Command)

			self.key = key
			self.help_text = help_text
			self._shortcuts = shortcuts
			self._parameters = \
				Command.Parameter(parameter_interpreters, \
					parameter_descriptors)
			self._callback = callback
			# self._command = command

			# assert key not in self._command._option_data

			# self._command._option_data[key] = None

		def __init__(
			self, 
			key: str, 
			help_text: Optional[str], 
			shortcuts: Iterable[str],
			parameter_interpreters: Iterable[Callable],
			parameter_descriptors: Iterable[str], 
			callback: Callable
		):
			self.__init__(
				key, 
				help_text, 
				shortcuts,
				Command.Parameter(parameter_interpreters, parameter_descriptors),
				callback
			)

		@property
		def shortcuts(self): return self._shortcuts

		@property
		def shortcuts_str(self):
			return ['-' + sc for sc in self._shortcuts \
				if len(sc) == 1 else '--' + sc]

		def parse(self, args):
			k = 0
			output = []

			for itp in self._parameters.interpreters:
				_out, k = itp(args[k:])
				output.append(_out)

			return _out, k


	class Parameter:

		# Add support for multiple parameter options

		def __init__(
			self, 
			parameter_interpreters: Iterable[Callable],
			parameter_descriptors: Iterable[str]
		):
			assert len(parameter_interpreters) == \
				len(parameter_descriptors)
			self._para_ints = [parameter_interpreters]
			self._para_descs = [parameter_descriptors]

		@property
		def interpreters(self):
			assert len(self._para_ints) == 1
			return self._para_ints[0]

		@property
		def descriptions(self):
			assert len(self._para_descs) == 1
			return self._para_descs[0]


class ArgumentParser(Command):

	def __init__(
		self, 
		program_name: str, 
		help_text: Optional[str], 
		callback: Callable, 
		style: StyledOutput = None,
		std_help: bool = True
	):
		super().__init__(program_name, help_text, \
			None, None, None, None, callback)
		atype_or_none(style, StyledOutput)


		self.style = style if style is not None else StyledOutput()

		self._std_help = std_help

		if std_help:
			self.__help_option__()

	def build(self):
		pass

	def parse(start_index=1):
		args = argv[start_index:]

		# First, we check whether the next input is a valid command


	


