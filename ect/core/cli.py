"""
Module Description
==================

This module provides ECT's command-line interface (CLI) API and the CLI executable.

To use the CLI executable, invoke the module file as a script, type ``python3 cli.py [ARGS] [OPTIONS]``. Type
`python3 cli.py --help`` for usage help.

The CLI operates on sub-commands. New sub-commands can be added by inheriting from the :py:class:`Command` class
and extending the ``Command.REGISTRY`` list of known command classes.


Module Reference
================
"""

import argparse
import os.path
import os.path
import sys
from abc import ABCMeta
from collections import OrderedDict
from typing import Tuple, Optional

from ect.core.monitor import ConsoleMonitor, Monitor
from ect.version import __version__

#: Name of the ECT CLI executable.
CLI_NAME = 'ect'

_COPYRIGHT_INFO = """
ECT - The ESA CCI Toolbox, Copyright (C) 2016 by European Space Agency (ESA)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.

Type "ect license" for details.
"""

_LICENSE_INFO_PATH = os.path.dirname(__file__) + '/../../LICENSE'

_DOCS_URL = 'http://ect-core.readthedocs.io/en/latest/'


class Command(metaclass=ABCMeta):
    """
    Represents (sub-)command for ECT's command-line interface.
    If a plugin wishes to extend ECT's CLI, it may append a new call derived from ``Command`` to the list
    ``REGISTRY``.
    """

    #: Success value to be returned by :py:meth:`execute`. Its value is ``(0, None)``.
    STATUS_OK = (0, None)

    @classmethod
    def name_and_parser_kwargs(cls):
        """
        Return a tuple (*command_name*, *parser_kwargs*) where *command_name* is a unique command name
        and *parser_kwargs* are the keyword arguments passed to a ``argparse.ArgumentParser(**parser_kwargs)`` call.

        For the possible keywords in *parser_kwargs*,
        refer to https://docs.python.org/3.5/library/argparse.html#argparse.ArgumentParser.

        :return: A tuple (*command_name*, *parser_kwargs*).
        """

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser):
        """
        Configure *parser*, i.e. make any required ``parser.add_argument(*args, **kwargs)`` calls.
        See https://docs.python.org/3.5/library/argparse.html#argparse.ArgumentParser.add_argument

        :param parser: The command parser to configure.
        """

    def execute(self, command_args: argparse.Namespace) -> Optional[Tuple[int, str]]:
        """
        Execute this command and return a tuple (*status*, *message*) where *status* is the CLI executable's
        exit code and *message* a text to be printed before the executable
        terminates. If *status* is zero, the message will be printed to ``sys.stdout``, otherwise to ``sys.stderr``.
        Implementors may can return ``STATUS_OK`` on success.

        The command's arguments in *command_args* are attributes namespace returned by
        ``argparse.ArgumentParser.parse_args()``.
        Also refer to to https://docs.python.org/3.5/library/argparse.html#argparse.ArgumentParser.parse_args


        :param command_args: The command's arguments.
        :return: `None`` (= status ok) or a tuple (*status*, *message*) of type (``int``, ``str``)
                 where *message* may be ``None``.
        """


class Run(Command):
    CMD_NAME = 'run'

    @classmethod
    def name_and_parser_kwargs(cls):
        help_line = 'Run an operation OP with given arguments.'
        return cls.CMD_NAME, dict(help=help_line,
                                  description='%s Type "list ops" to list all available operations.' % help_line)

    @classmethod
    def configure_parser(cls, parser):
        parser.add_argument('--monitor', '-m', action='store_true',
                            help='Display progress information during execution.')
        parser.add_argument('op_name', metavar='OP', nargs='?',
                            help="Fully qualified operation name or alias")
        parser.add_argument('op_args', metavar='...', nargs=argparse.REMAINDER,
                            help="Operation arguments. Use '-h' to print operation details.")

    def execute(self, command_args):
        op_name = command_args.op_name
        if not op_name:
            return 2, "error: command '%s' requires OP argument" % self.CMD_NAME
        is_graph_file = op_name.endswith('.json') and os.path.isfile(op_name)

        op_args = []
        op_kwargs = OrderedDict()
        for arg in command_args.op_args:
            kwarg = arg.split('=', maxsplit=1)
            kw = None
            if len(kwarg) == 2:
                kw, arg = kwarg
                if not kw.isidentifier():
                    return 2, "error: command '%s': keyword '%s' is not a valid identifier" % (self.CMD_NAME, kw)
            try:
                # try converting arg into a Python object
                arg = eval(arg)
            except (SyntaxError, NameError):
                # If it fails, we stay with default type (str)
                pass
            if not kw:
                op_args.append(arg)
            else:
                op_kwargs[kw] = arg

        if is_graph_file:
            return self._invoke_graph(command_args.op_name, command_args.monitor, op_args, op_kwargs)
        else:
            return self._invoke_operation(command_args.op_name, command_args.monitor, op_args, op_kwargs)

    @staticmethod
    def _invoke_operation(op_name: str, op_monitor: bool, op_args: list, op_kwargs: dict):
        from ect.core.op import OP_REGISTRY as OP_REGISTRY
        op = OP_REGISTRY.get_op(op_name)
        if op is None:
            return 1, "error: command '%s': unknown operation '%s'" % (Run.CMD_NAME, op_name)
        print('Running operation %s with args=%s and kwargs=%s' % (op_name, op_args, dict(op_kwargs)))
        if op_monitor:
            monitor = ConsoleMonitor()
        else:
            monitor = Monitor.NULL
        return_value = op(*op_args, monitor=monitor, **op_kwargs)
        print('Output: %s' % return_value)
        return None

    @staticmethod
    def _invoke_graph(graph_file: str, op_monitor: bool, op_args: list, op_kwargs: dict):
        if op_args:
            return 1, "error: command '%s': can't run graph with arguments %s, please provide keywords only" % \
                   (Run.CMD_NAME, op_args)

        from ect.core.graph import Graph
        graph = Graph.load(graph_file)

        for name, value in op_kwargs.items():
            if name in graph.input:
                graph.input[name].value = value

        print('Running graph %s with kwargs=%s' % (graph_file, dict(op_kwargs)))
        if op_monitor:
            monitor = ConsoleMonitor()
        else:
            monitor = Monitor.NULL
        graph.invoke(monitor=monitor)
        for graph_output in graph.output[:]:
            print('Output: %s = %s' % (graph_output.name, graph_output.value))
        return None


class DataSource(Command):
    CMD_NAME = 'ds'

    @classmethod
    def name_and_parser_kwargs(cls):
        help_line = 'Data source operations.'
        return cls.CMD_NAME, dict(help=help_line, description=help_line)

    @classmethod
    def configure_parser(cls, parser):
        parser.add_argument('ds_names', metavar='DS_NAME', nargs='+', default='op',
                            help='Data source name. Type "ect list ds" to show all possible names.')
        parser.add_argument('--info', '-i', action='store_true', default=True,
                            help="Display information about the data source DS_NAME.")
        parser.add_argument('--sync', '-s', action='store_true', default=False,
                            help="Synchronise a remote data source DS_NAME with its local version.")

    def execute(self, command_args):
        from ect.core.io import CATALOG_REGISTRY
        catalog = CATALOG_REGISTRY.get_catalog('default')

        for ds_name in command_args.ds_names:
            data_sources = catalog.query(name=ds_name)
            if not data_sources or len(data_sources) == 0:
                print("Unknown data source '%s'" % ds_name)
                continue
            data_source = data_sources[0]
            if command_args.info and not command_args.sync:
                print(data_source.info_string)
            if command_args.sync:
                print("Synchronising data source '%s'" % data_source)
                data_source.sync(monitor=ConsoleMonitor())


class List(Command):
    CMD_NAME = 'list'

    @classmethod
    def name_and_parser_kwargs(cls):
        help_line = 'List items of a various categories.'
        return cls.CMD_NAME, dict(help=help_line, description=help_line)

    @classmethod
    def configure_parser(cls, parser):
        parser.add_argument('category', metavar='CAT', choices=['op', 'ds', 'pi'], nargs='?', default='op',
                            help="Category to list items of. "
                                 "'op' lists operations, 'ds' lists data sources, 'pi' lists plugins")
        parser.add_argument('--pattern', '-p', metavar='PAT', nargs='?', default=None,
                            help="A wildcard pattern to filter listed items. "
                                 "'*' matches zero or many characters, '?' matches a single character. "
                                 "The comparison is case insensitive.")

    def execute(self, command_args):
        if command_args.category == 'pi':
            from ect.core.plugin import PLUGIN_REGISTRY as PLUGIN_REGISTRY
            List.list_items('plugin', 'plugins', PLUGIN_REGISTRY.keys(), command_args.pattern)
        elif command_args.category == 'ds':
            from ect.core.io import CATALOG_REGISTRY
            catalog = CATALOG_REGISTRY.get_catalog('default')
            if catalog is None:
                return 2, "error: command '%s': no catalog named 'default' found" % self.CMD_NAME
            List.list_items('data source', 'data sources', [data_source.name for data_source in catalog.query()],
                            command_args.pattern)
        elif command_args.category == 'op':
            from ect.core.op import OP_REGISTRY as OP_REGISTRY
            List.list_items('operation', 'operations', OP_REGISTRY.op_registrations.keys(), command_args.pattern)

    @staticmethod
    def list_items(category_singular_name: str, category_plural_name: str, names, pattern: str):
        if pattern:
            # see https://docs.python.org/3.5/library/fnmatch.html
            import fnmatch
            pattern = pattern.lower()
            names = [name for name in names if fnmatch.fnmatch(name.lower(), pattern)]
        item_count = len(names)
        if item_count == 1:
            print('One %s found' % category_singular_name)
        elif item_count > 1:
            print('%d %s found' % (item_count, category_plural_name))
        else:
            print('No %s found' % category_plural_name)
        no = 0
        for item in names:
            no += 1
            print('%4d: %s' % (no, item))


class Copyright(Command):
    @classmethod
    def name_and_parser_kwargs(cls):
        help_line = 'Print copyright information.'
        return 'copyright', dict(help=help_line, description=help_line)

    def execute(self, command_args):
        print(_COPYRIGHT_INFO)


class License(Command):
    @classmethod
    def name_and_parser_kwargs(cls):
        help_line = 'Print license information.'
        return 'license', dict(help=help_line, description=help_line)

    def execute(self, command_args):
        with open(_LICENSE_INFO_PATH) as fp:
            content = fp.read()
            print(content)


class Docs(Command):
    @classmethod
    def name_and_parser_kwargs(cls):
        help_line = 'Display documentation in a browser window.'
        return 'docs', dict(help=help_line, description=help_line)

    def execute(self, command_args):
        import webbrowser
        webbrowser.open_new_tab(_DOCS_URL)


#: List of sub-commands supported by the CLI. Entries are classes derived from :py:class:`Command` class.
#: ECT plugins may extend this list by their commands during plugin initialisation.
COMMAND_REGISTRY = [
    List,
    Run,
    DataSource,
    Copyright,
    License,
    Docs,
]


# TODO (forman, 20160526): cli.main() should never exit the interpreter, configure argparse parser accordingly

def main(args=None):
    """
    The CLI's entry point function.

    :param args: list of command-line arguments of type ``str``.
    :return: A tuple (*status*, *message*)
    """

    if not args:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(prog=CLI_NAME,
                                     description='ESA CCI Toolbox command-line interface, version %s' % __version__)
    parser.add_argument('--version', action='version', version='%s %s' % (CLI_NAME, __version__))
    subparsers = parser.add_subparsers(
        dest='command_name',
        metavar='COMMAND',
        help='One of the following commands. Type "COMMAND -h" to get command-specific help.'
    )

    for command_class in COMMAND_REGISTRY:
        command_name, command_parser_kwargs = command_class.name_and_parser_kwargs()
        command_parser = subparsers.add_parser(command_name, **command_parser_kwargs)
        command_class.configure_parser(command_parser)
        command_parser.set_defaults(command_class=command_class)

    args_obj = parser.parse_args(args)

    if args_obj.command_name and args_obj.command_class:
        assert args_obj.command_name and args_obj.command_class
        status_and_message = args_obj.command_class().execute(args_obj)
        if not status_and_message:
            status_and_message = Command.STATUS_OK
        status, message = status_and_message
    else:
        parser.print_help()
        status, message = 0, None

    if message:
        if status:
            sys.stderr.write("%s: %s\n" % (CLI_NAME, message))
        else:
            sys.stdout.write("%s\n" % message)

    return status


if __name__ == '__main__':
    sys.exit(main())
