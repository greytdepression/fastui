from os import get_terminal_size
from sys import argv
import os
from tabulate import tabulate
import numpy as np
from math import ceil
from .styled_output import StyledOutput
from typing import Union, List, Iterable, Any, Iterator, Optional, Callable
from rich.console import Console
from .tables import SimplePlainTable
from .._utils import assert_type, assert_func, assert_iter, \
    assert_iter_types, from_dict


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

def parse_list(itr, delims, typ):
    assert_iter(delims, name='delims', min_len=2, options=False)

    args = []
    args.append(next(itr))

    # if type(delims[0]) in (list, tuple):
    if assert_iter(delims[0], 'delims[0]', stop=False):
        assert all(len(d) == 2 for d in delims), \
            'List delimiters must be given in pairs.'
        assert all(type(d[0]) == type(d[1]) == str for d in delims), \
            'List delimiters must be strings.'

        starts = [d[0] for d in delims]

        k = 0
        for i in range(len(args[0])):
            if args[0][i] in starts:
                k = starts.index(args[0][i])
                break

        delims = delims[k]

    assert len(delims) == 2, \
        'List delimiters must be given in pairs.'

    # Check whether there are parantheses
    assert any(b in args[0] for b in delims), \
        'Opening list delimiter must be present in first relevant argument.'

    # Check which argument is contains the closing paranthesis
    counter = args[0].count(delims[0])
    counter -= args[0].count(delims[1])

    while counter > 0:
        args.append(next(itr))

        counter += args[-1].count(delims[0])
        counter -= args[-1].count(delims[1])

    # Build the list
    string = ''.join(args)

    return parse_list_from_string(string, delims, typ)


class Command:

    def __init__(
        self, 
        names: Iterable[str], 
        arg_parser: 'ArgumentParser',
        help_text: Optional[str] = None, 
        usage: Optional[str] = None, 
        commands: Optional[Iterable['Command']] = None,
        parameters: Optional[Iterable['Parameter']] = None, 
        options: Optional[Iterable['Option']] = None, 
        callback: Optional[Callable[...,None]] = None,
        std_help: bool = True
    ) -> None:
        assert_iter_types(names, str, name='names', min_len=1)
        assert_type(help_text, str, name='help_text', optional=True)
        assert_type(usage, str, name='usage', optional=True)
        assert_iter_types(commands, self.__class__, name='commands', allow_none=True)
        assert_iter_types(parameters, self.__class__.Parameter, name='parameters', allow_none=True)
        assert_iter_types(options, self.__class__.Option, name='options', allow_none=True)
        assert_func(callback, name='callback', optional=True)
        assert_type(arg_parser, ArgumentParser, name='arg_parser', optional=False)
        assert_type(std_help, bool, name='std_help', optional=False)

        self._names = names
        self.help_text = help_text if help_text is not None else ''
        self.usage = usage if usage is not None else ''

        self._parameters = parameters if parameters is not None else []
        self._callback = callback if callback is not None else lambda *args, **kwargs: None
        self._arg_parser = arg_parser
        self._std_help = std_help

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
        arg_parser: 'ArgumentParser',
        help_text: Optional[str] = None, 
        usage: Optional[str] = None, 
        commands: Optional[Iterable['Command']] = None,
        parameter_interpreters: Iterable[Callable[[Iterator],Iterable]] = tuple(), 
        parameter_descriptors: Iterable[str] = tuple(),
        options: Optional[Iterable['Option']] = None, 
        callback: Optional[Callable[...,None]] = None,
        std_help: bool = True
    ) -> None:
        self.__init__(
            names=names, 
            arg_parser=arg_parser,
            help_text=help_text, 
            usage=usage, 
            commands=commands,
            parameters=Command.Parameter(
                list(parameter_interpreters),
                list(parameter_descriptors)
            ),
            options=options, 
            callback=callback,
            std_help=std_help
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

    def command(self, key: str) -> 'Command':
        assert key in self._command_keys, \
            'Command key must exist.'

        return self._command_list[self._command_keys[name]]

    def option(self, key: str) -> 'Option':
        assert key in self._option_keys, \
            'Option key must exist.'

        return self._option_list[self._option_keys[name]]

    def add_command(
        self, 
        command: 'Command', 
        index: Optional[int] = None
    ) -> None:
        # Check commands are of the correct type
        assert_type(command, self.Command, name='command', optional=False)
        assert_type(index, int, name='index', optional=True)

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
        commands: Optional[Iterable['Command']] = None,
        parameter_interpreters: Iterable[Callable[[Iterator],Iterable]] = tuple(), 
        parameter_descriptors: Iterable[str] = tuple(),
        options: Optional[Iterable['Option']] = None, 
        callback: Optional[Callable[...,None]] = None,
        index: Optional[int] = None
    ) -> None:
        cmd = Command(
            names=names,
            arg_parser=self._arg_parser,
            help_text=help_text,
            usage=usage,
            commands=commands,
            parameter_interpreters=parameter_interpreters,
            parameter_descriptors=parameter_descriptors,
            options=options,
            callback=callback,
            std_help=self._std_help
        )

        self.add_command(cmd, index)

    def add_option(
        self, 
        option: 'Option', 
        index: Optional[int] = None
    ) -> None:

        # Check options are of the correct type
        assert_type(option, self.Option, name='option', optional=False)
        assert_type(index, int, name='index', optional=True)

        # Option key must not have been chosen yet!
        assert option.key not in self._option_data, \
            f'The key `{option.key}` is already in use. Option keys must be unique.'

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
        key: str, 
        help_text: Optional[str], 
        shortcuts: Iterable[str],
        parameter_interpreters: Iterable[Callable[[Iterator], Iterable]],
        parameter_descriptors: Iterable[str], 
        callback: Callable[..., None],
        index: Optional[int] = None
    ) -> None:
        opt = self.Option(
            key=key, 
            help_text=help_text, 
            shortcuts=shortcuts, 
            parameter_interpreters=parameter_interpreters, 
            parameter_descriptors=parameter_descriptors,
            callback=callback
        )

        self.add_option(opt, index)

    def __help_option__(self) -> None:
        def output(slf):
            # Usage section
            if slf.usage is not None:
                con.print(slf.style.header('usage'))
                con.print(slf.style.indent(slf.usage))


            sections = []

            # Commands section
            command_table = []

            for k in slf._command_order:
                cmd = slf._command_list[k]
                lhs = ' '.join([slf.style.list(cmd.names_str),
                    slf.style.parameters(cmd.parameter_descriptors)])
                command_table.append([lhs, cmd.help_text])

            if len(command_table) > 0:
                cmd_sec = SimplePlainTable.Section(
                    slf.style.header('commands'),
                    command_table
                )
                sections.append(cmd_sec)
            
            # Options section
            options_table = []

            for k in slf._option_order:
                opt = slf._option_list[k]
                lhs = ' '.join(
                    (
                        slf.style.list(opt.shortcuts_str), 
                        slf.style.parameters(opt.parameter_descriptors)
                    )
                )
                options_table.append([lhs, opt.help_text])

            if len(options_table) > 0:
                cmd_sec = SimplePlainTable.Section(
                    slf.style.header('options'),
                    options_table
                )
                sections.append(cmd_sec)

            table = SimplePlainTable(
                *sections, 
                indentation=slf._arg_parser.style.std_indent,
                highlight_rows=slf._arg_parser.style.table_alternate_rows,
                header_style=slf._arg_parser.style.header,
                console=slf._arg_parser.console
            )
            table.print()

        _callback = lambda *args, **kwargs: output(self)
        self.add_option(
            key = 'help', 
            help_text = 'Show help.', 
            shortcuts = ['h', 'help'], 
            parameter_interpreters = tuple(), 
            parameter_descriptors = tuple(), 
            callback = _callback,
            index = 0
        )

    def add_simple_option(
        self, 
        key: str, 
        help_text: Optional[str],
        *shortcuts: str, 
        callback: Callable[..., None],
        index: Optional[int] = None
    ) -> None:
        self.add_option(
            key = key, 
            help_text = help_text, 
            shortcuts = shortcuts, 
            parameter_interpreters = tuple(), 
            parameter_descriptors = tuple(), 
            callback = callback,
            index = index
        )

    def add_int_option(
        self, 
        key: str, 
        help_text: Optional[str],
        *shortcuts: str, 
        parameter_descriptor: str,
        callback: Callable[..., None], 
        index: Optional[int] = None
    ) -> None:
        self.add_option(
            key = key, 
            help_text = help_text, 
            shortcuts = shortcuts, 
            parameter_interpreters = (lambda itr: int(next(itr)),), 
            parameter_descriptors = (parameter_descriptor,), 
            callback = callback,
            index = index
        )

    def add_float_option(
        self, 
        key: str, 
        help_text: Optional[str],
        *shortcuts: str, 
        parameter_descriptor: str,
        callback: Callable[..., None], 
        index: Optional[int] = None
    ) -> None:
        self.add_option(
            key = key, 
            help_text = help_text, 
            shortcuts = shortcuts, 
            parameter_interpreters = (lambda itr: float(next(itr)),), 
            parameter_descriptors = (parameter_descriptor,), 
            callback = callback,
            index = index
        )

    def add_string_option(
        self, 
        key: str, 
        help_text: Optional[str],
        *shortcuts: str, 
        parameter_descriptor: str,
        callback: Callable[..., None], 
        index: Optional[int] = None
    ) -> None:
        self.add_option(
            key=key,
            help_text=help_text,
            shortcuts=shortcuts,
            parameter_interpreters=(
                lambda itr: next(itr),
            ),
            parameter_descriptors=(parameter_descriptor,),
            callback=callback,
            index=index
        )

    def add_list_option(
        self, 
        key: str, 
        help_text: Optional[str],
        *shortcuts: str, 
        list_delimiters: Optional[Iterable[Union[str, Iterable[str]]]],
        element_parser: Callable[[str], Any],
        parameter_descriptor: str,
        callback: Callable[..., None], 
        index: Optional[int] = None
    ) -> None:
        if list_delimiters is None:
            list_delimiters = (('[', ']'), ('(', ')'), ('{', '}'))
        self.add_option(
            key=key,
            help_text=help_text,
            shortcuts=shortcuts,
            parameter_interpreters=(
                lambda itr: parse_list(itr, list_delimiters, element_parser),
            ),
            parameter_descriptors=(parameter_descriptor,),
            callback=callback,
            index=index
        )

    def add_selection_option(
        self, 
        key: str, 
        help_text: Optional[str],
        *shortcuts: str, 
        valid_parameters: Iterable[str],
        parameter_descriptors: Iterable[str],
        callback: Callable[..., None], 
        index: Optional[int] = None
    ) -> None:
        valid_parameters = tuple(map(str, valid_parameters))
        self.add_option(
            key=key,
            help_text=help_text,
            shortcuts=shortcuts,
            parameter_interpreters=(
                lambda itr: valid_parameters.index(next(itr)),
            ),
            parameter_descriptors=parameter_descriptors,
            callback=callback,
            index=index
        )        


    class Option:
        def __init__(
            self, 
            key: str, 
            help_text: Optional[str], 
            shortcuts: Iterable[str],
            parameters: Iterable['Parameter'], 
            callback: Callable[..., None]
        ) -> None:
            assert_type(key, str, name='key', optional=False)
            assert_type(help_text, str, name='help_text', optional=True)
            assert_iter_types(shortcuts, str, name='shortcuts', min_len=1)
            assert_iter_types(parameters, self.__class__.Parameter, name='parameters')
            assert_func(callback, name='callback')

            self.key = key
            self.help_text = help_text
            self._shortcuts = shortcuts
            self._parameters = self.__class__.Parameter(
                parameter_interpreters, parameter_descriptors
            )
            self._callback = callback

        def __init__(
            self, 
            key: str, 
            help_text: Optional[str], 
            shortcuts: Iterable[str],
            parameter_interpreters: Iterable[Callable[[Iterator], Iterable]],
            parameter_descriptors: Iterable[str], 
            callback: Callable[..., None]
        ) -> None:
            self.__init__(
                key, 
                help_text, 
                shortcuts,
                self.__class__.Parameter(parameter_interpreters, parameter_descriptors),
                callback
            )

        @property
        def shortcuts(self): return self._shortcuts

        @property
        def shortcuts_str(self):
            return ['-' + sc if len(sc) == 1 else '--' + sc \
                for sc in self._shortcuts]

        def parse(self, args: Iterator[str]):
            k = 0
            output = []

            for itp in self._parameters.interpreters:
                _out = itp(args)
                output.append(_out)

            return _out

    class Parameter:
        # Add support for multiple parameter options

        def __init__(
            self, 
            parameter_interpreters: Iterable[Callable[[Iterator], Iterable]],
            parameter_descriptors: Iterable[str]
        ) -> None:
            assert len(parameter_interpreters) == len(parameter_descriptors), \
                'There must be the same number of parameter interpreters as descriptors.'
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
        version: str,
        callback: Callable[..., None], 
        console: Optional[Console] = None,
        help_text: Optional[str] = None,
        style: StyledOutput = None,
        std_help: bool = True
    ) -> None:
        super().__init__(
            names=[program_name],
            arg_parser=self,
            help_text=help_text,
            usage=program_name,
            commands=None,
            parameters=None,
            options=None,
            callback=callback,
            std_help=std_help
        )
        self.program_name = program_name
        self.version = version
        self.console = console if console is not None else Console()
        assert_type(style, StyledOutput, name='style', optional=True)
        self.style = style if style is not None else StyledOutput()
        self._std_help = std_help
        self._arg_parser = self
        if std_help:
            self.__help_option__()

    def add_version_option(
        self,
        text: Optional[str] = None, 
        index: Optional[int] = 1
    ) -> None:
        assert_type(text, str, name='text', optional=True)
        assert_type(index, int, name='index', optional=True)

        self.add_option(
            key = 'version',
            help_text = 'Display the program\'s version',
            shortcuts = ('V', 'version'),
            parameters = (),
            callback = lambda *args, **kwargs: self.console.print(
                text.format(
                    name = self.program_name, 
                    version = self.version
                )
            ),
            index = index
        )

    def parse(start_index: int = 1) -> None:
        args = argv[start_index:]

        super().parse(start_index=0, argument_list=args)


