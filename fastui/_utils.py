from collections.abc import Iterable
from math import inf
from typing import Any, Iterable, Type, Union, Dict, TypeVar

T = TypeVar('T')
S = TypeVar('S')

def _str_list_or(
    items: Iterable[Any]
) -> str:
    if not isinstance(items, Iterable) or type(items) == str:
        items = (items,)

    items = tuple(map(str, items))

    output = ', '.join(items[:-1])

    if len(items) >= 3: output += ','

    return ' or '.join((output, items[-1])) if len(items) > 1 else items[0]


def assert_type(
    arg: Any, 
    *typs: Type, 
    name: str = 'item', 
    optional: bool = False, 
    stop: bool = True
) -> bool:
    b = type(arg) in typs or (arg is None and optional)
    if stop: 
        assert b, \
            f'`{name}` must be of type {_str_list_or(typs)}' + \
            (' or None.' if optional else '.')
    return b

# def assert_optional_type(arg, typs, name='item'):
#     assert type(arg) in typs or arg is None, \
#         f'`{name}` must be of type {_str_list_or(typ)} or None.'

def assert_func(
    arg: Any, 
    name: str = 'func', 
    optional: bool = False, 
    stop: bool = True
) -> bool:
    b = callable(arg) or (arg is None and optional)
    if stop:
        assert b, \
            f'`{name}` must be a function' + \
            (' or None.' if optional else '.')
    return b

# def is_iter_type(lst, typ, name='item', min_len=0, max_len=inf):
#     assert
#     is_iter_types(lst, ())

def assert_iter(
    lst: Any, 
    name: str = 'item', 
    min_len: Union[int, float] = 0, 
    max_len: Union[int, float] = inf, 
    optional: bool = False, 
    stop: bool = True
) -> bool:
    if optional and lst is None:
        return True

    b = isinstance(lst, Iterable)
    b &= min_len <= len(lst) <= max_len

    if stop:
        assert b, \
            f'`{name}` must be iterable' + \
            (f' or None.' if allow_none else '.') + \
            (f' `{name}` must be of length ' if min_len > 0 or max_len < inf else '') + \
            (f'at least {min_len}' if min_len > 0 else '') + \
            (' and ' if min_len > 0 and max_len < inf else '') + \
            (f'at most {max_len}.' if max_len < inf else '.')
    return b


def assert_iter_types(
    lst: Any, 
    *typs: Type, 
    name: str = 'item', 
    min_len: Union[int, float] = 0, 
    max_len: Union[int, float] = inf, 
    allow_none: bool = False, 
    stop: bool = True
) -> bool:
    b = isinstance(Iterable)
    b &= isinstance(Iterable)

    if b:
        b &= min_len <= len(lst) <= max_len

        for e in lst:
            b &= (type(e) in typs) or (e is None and allow_none)

    if stop:
        assert b, \
            f'`{name}` must be iterable, containging {_str_list_or(typ)}-type elements' + \
            (f' or None elements.' if allow_none else '.') + \
            (f' `{name}` must be of length ' if min_len > 0 or max_len < inf else '') + \
            (f'at least {min_len}' if min_len > 0 else '') + \
            (' and ' if min_len > 0 and max_len < inf else '') + \
            (f'at most {max_len}.' if max_len < inf else '.')
    return b

def from_dict(
    dic: Dict[T, S], 
    key: T, 
    default: S
) -> S:
    if key in dic:
        return dic[key]

    return default