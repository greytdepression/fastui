from typing import Callable, TYPE_CHECKING, Iterable, List, NamedTuple, Optional, Tuple, Union
from rich.console import Console, ConsoleOptions
from rich.table import Table
from rich import box
from rich._pick import pick_bool

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, List, NamedTuple, Optional, Tuple, Union

from rich import box, errors
from rich._loop import loop_first_last, loop_last
from rich._pick import pick_bool
from rich._ratio import ratio_distribute, ratio_reduce
from rich.jupyter import JupyterMixin
from rich.measure import Measurement
from rich.padding import Padding, PaddingDimensions
from rich.protocol import is_renderable
from rich.segment import Segment
from rich.style import Style, StyleType
from rich.styled import Styled
from rich.text import Text, TextType



class SimplePlainTable:
    class Section:
        def __init__(self, title, data):
            self.title = title

            assert type(data) == list and \
                (len(data) == 0 or (type(data[0]) == list and \
                (len(data[0]) == 0 or type(data[0][0]) == str)))

            self._data = data
            self._table = None

            self._make_table()

        @property
        def width(self):
            return len(self.data[0]) \
                if len(self.data) > 0 else 0

        @property
        def height(self):
            return len(self.data)

        @property
        def size(self):
            return (self.width, self.height)

        @property
        def data(self):
            return self._data

        @data.setter
        def data(self, data):
            self._data = data
            self._make_table()

        @property
        def table(self):
            return self._table

        def _make_table(self):
            del self._table
            self._table = Table(show_header=False, show_footer=False)

            for row in self._data:
                self._table.add_row(*row)

        @classmethod
        def same_width(cls, sections):
            # print(list(type(s) for s in sections))
            # print(cls)
            assert all(type(s)==cls for s in sections)
            assert any(type(s)==cls for s in sections)
            return min(s.width for s in sections) == \
                max(s.width for s in sections)


    def __init__(
        self,
        *sections: Section,
        expanded_column: int = 1,
        indentation: int = 4,
        header_style: Optional[Callable[[str],str]] = None,
        highlight_rows: bool = True,
        console: Console = None
    ):
        assert self.Section.same_width(sections)
        assert header_style is None or callable(header_style)

        if header_style is None:
            header_style = lambda txt: txt

        self._expanded_column = expanded_column
        self._indentation = indentation
        self._header_style = header_style
        self._highlight_rows = highlight_rows

        self._sections = sections
        self._console = console if console is not None else Console()

    def _construct_temp_table(self):
        temp_table = DividableTable(0,-1,show_header=False, show_footer=False)
        temp_table.box = box.SIMPLE_HEAD

        for sec in self._sections:
            for row in sec.data:
                temp_table.add_row(*row)

        for col in temp_table.columns:
            col.justify = 'left'

        temp_table.width = self._console.width - self._indentation

        assert 0 <= self._expanded_column < len(temp_table.columns)
        temp_table.columns[self._expanded_column].expand = True

        if self._highlight_rows:
            temp_table.row_styles = ['none', 'dim']

        # width = lambda c: temp_table._measure_column(self._console, c,
        #   self._console.width).minimum

        # widths = [width(c) for c in temp_table.columns]

        # self._console.print(temp_table, justify='right')

        return temp_table

    def print(self):
        # tables = [s.table for s in self._sections]
        temp_table = self._construct_temp_table()
        width = self._console.width - self._indentation

        con = self._console

        # copts = con.options
        # copts.

        start = 0
        for k, sec in enumerate(self._sections):
            con.print(self._header_style(sec.title))

            temp_table.dt_select_rows(start, start+len(sec.data))
            start += len(sec.data)

            # t.box = box.SIMPLE_HEAD
            # t.width = temp_table.width
            # t.min_width = temp_table.min_width
            # t.padding = temp_table.padding
            # t.pad_edge = temp_table.pad_edge
            # t.expand = False
            # for i in range(len(widths)):
            #   t.columns[i].width = widths[i]

            con.print(temp_table, justify='right')



class DividableTable(Table):
    def __init__(self, start=0, end=-1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dt_rows_start = start
        self._dt_rows_end = end

    def dt_select_rows(self, start: int, end: int) -> None:
        self._dt_rows_start = start
        self._dt_rows_end = end

    def _render(
        self, console: "Console", options: "ConsoleOptions", widths: List[int]
    ) -> "RenderResult":

        if self._dt_rows_end < 0:
            self._dt_rows_end = self.row_count

        table_style = console.get_style(self.style or "")

        border_style = table_style + console.get_style(self.border_style or "")
        rows: List[Tuple[_Cell, ...]] = list(
            zip(
                *(
                    self._get_cells(column_index, column)
                    for column_index, column in enumerate(self.columns)
                )
            )
        )
        _box = (
            self.box.substitute(
                options, safe=pick_bool(self.safe_box, console.safe_box)
            )
            if self.box
            else None
        )

        # _box = self.box
        new_line = Segment.line()

        columns = self.columns
        show_header = self.show_header
        show_footer = self.show_footer
        show_edge = self.show_edge
        show_lines = self.show_lines
        leading = self.leading

        _Segment = Segment
        if _box:
            box_segments = [
                (
                    _Segment(_box.head_left, border_style),
                    _Segment(_box.head_right, border_style),
                    _Segment(_box.head_vertical, border_style),
                ),
                (
                    _Segment(_box.foot_left, border_style),
                    _Segment(_box.foot_right, border_style),
                    _Segment(_box.foot_vertical, border_style),
                ),
                (
                    _Segment(_box.mid_left, border_style),
                    _Segment(_box.mid_right, border_style),
                    _Segment(_box.mid_vertical, border_style),
                ),
            ]
            if show_edge:
                yield _Segment(_box.get_top(widths), border_style)
                yield new_line
        else:
            box_segments = []

        get_row_style = self.get_row_style
        get_style = console.get_style

        start = self._dt_rows_start
        end = self._dt_rows_end

        for index, (first, last, row) in enumerate(loop_first_last(rows)):

            # Hope this does the trick
            if index < start or index >= end:
                continue

            header_row = first and show_header
            footer_row = last and show_footer
            max_height = 1
            cells: List[List[List[Segment]]] = []
            if header_row or footer_row:
                row_style = Style.null()
            else:
                row_style = get_style(
                    get_row_style(index - 1 if show_header else index)
                )
            for width, cell, column in zip(widths, row, columns):
                render_options = options.update(
                    width=width,
                    justify=column.justify,
                    no_wrap=column.no_wrap,
                    overflow=column.overflow,
                )
                cell_style = table_style + row_style + get_style(cell.style)
                lines = console.render_lines(
                    cell.renderable, render_options, style=cell_style
                )
                max_height = max(max_height, len(lines))
                cells.append(lines)

            cells[:] = [
                _Segment.set_shape(_cell, width, max_height, style=table_style)
                for width, _cell in zip(widths, cells)
            ]

            if _box:
                if last and show_footer:
                    yield _Segment(
                        _box.get_row(widths, "foot", edge=show_edge), border_style
                    )
                    yield new_line
                left, right, _divider = box_segments[0 if first else (2 if last else 1)]

                # If the column divider is whitespace also style it with the row background
                divider = (
                    _divider
                    if _divider.text.strip()
                    else _Segment(
                        _divider.text, row_style.background_style + _divider.style
                    )
                )
                for line_no in range(max_height):
                    if show_edge:
                        yield left
                    for last_cell, rendered_cell in loop_last(cells):
                        yield from rendered_cell[line_no]
                        if not last_cell:
                            yield divider
                    if show_edge:
                        yield right
                    yield new_line
            else:
                for line_no in range(max_height):
                    for rendered_cell in cells:
                        yield from rendered_cell[line_no]
                    yield new_line
            if _box and first and show_header:
                yield _Segment(
                    _box.get_row(widths, "head", edge=show_edge), border_style
                )
                yield new_line
            if _box and (show_lines or leading):
                if (
                    not last
                    and not (show_footer and index >= len(rows) - 2)
                    and not (show_header and header_row)
                ):
                    if leading:
                        for _ in range(leading):
                            yield _Segment(
                                _box.get_row(widths, "mid", edge=show_edge),
                                border_style,
                            )
                    else:
                        yield _Segment(
                            _box.get_row(widths, "row", edge=show_edge), border_style
                        )
                    yield new_line

        if _box and show_edge:
            yield _Segment(_box.get_bottom(widths), border_style)
            yield new_line





if __name__ == '__main__':
    sec_cmds = SimplePlainTable.Section(
        'Commands', 
        [
            ['install', 'Install packages.'],
            ['download', 'Download packages.'],
            ['uninstall', 'Uninstall packages.'],
            ['freeze', 'Output installed packages in requirements format.'],
            ['list', 'List installed packages.'],
            ['show', 'Show information about installed packages.'],
            ['check', 'Verify installed packages have compativle dependencies.'],
            ['config', 'Manage local and global configuration.'],
            ['search', 'Search PyPI for packages.'],
            ['cache', 'Inspect and manage pip\'s wheel cache.'],
            ['wheel', 'Build wheels from your requirements.'],
            ['hash', 'Compute hashes of package archives.'],
            ['completion', 'A helper command used for command completion.'],
            ['debug', 'Show information useful for debugging.'],
            ['help', 'Show help for commands.']
        ] 
    )
    sec_gen_opts = SimplePlainTable.Section(
        'General Options', 
        [
            ['-h, --help', 'Show help.'],
            ['--isolated', 'Run pip in an isolated mode, ignoring enivironment variables and user configuration.'],
            ['-v, --verbose', 'Give more output. Option is additive, and can be used up to 3 times.'],
            ['-V, --version', 'Show version and exit.'],
            ['-q, --quiet', 'Give less output. Option is additive, and can be used up to 3 times (corresponding to WARNING, ERROR, and CRITICAL logging levels).'],
            ['--log <path>', 'Path to a verbose appending log.'],
            ['--no-input', 'Disable prompting for input.'],
            ['--proxy <proxy>', 'Specift a proxy in the form \[user:passswd@] proxy.server:port'],
            ['--timeout <sec>', 'Set the socket timout (default 15 seconds).'],\
            ['--exists-action <action>', 'Default action when a path already exists: (s)witch, (i)gnore, (w)ipe, (b)ackup, (a)bort.'],
            ['--trusted-host <hostname>', 'Mark this host or host:port pair as trusted, even though it does not have valid or any HTTPS.'],
            ['--cert <path>', 'Path to alternate CA bundle.'],
            ['--client-cert <path>', 'Path to SSL client vertificate, a single file containing the preivate key and the certification in PEM format.'],
            ['--cache-dir <dir>', 'Store the cache data in <dir>.'],
            ['--no-cache-dir', 'Disable the cache.'],
            ['--disable-pip-version-check', 'Don\'t periodically check PyPI to determine whether a new version of pip is available for download. Implied with --no-index.'],
            ['--no-color', 'Suppress colored output.'],
            ['--no-python-version-warning', 'Silence deprecation warnings for upcoming unsupported Pythons.'],
            ['--use-feature <feature>', 'Enable new functionality, that may be backward incompatible.'],
            ['--use-deprecated <feature>', 'Enable deprecated functionality, that will be removed in the future.'],
        ] 
    )

    table = SimplePlainTable(sec_cmds, sec_gen_opts, header_style=lambda txt: f'{txt}:')

    table.print()