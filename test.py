from fastui.terminal.argument_parsing import ArgumentParser
from fastui import _utils







def main_loop():
	print('All Done!')








dummy_callback = lambda *args, **kwargs: None
dummy_interpreter = lambda itr: (next(itr),)


cmds = [
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

opts = [
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

def get_cmd_keys(lst):
	return lst[0].split(', ')

def get_help_text(lst):
	return lst[1]

def get_opt_keys(lst):
	return list(map(lambda txt: txt.split(' ')[0].replace('-', ''), get_cmd_keys(lst)))

def get_opt_parameters(lst):
	_opt = get_cmd_keys(lst)[0]
	desc = list(map(lambda txt: txt.split('>')[0], _opt.split('<')))
	return desc


arg_parser = ArgumentParser(
	program_name = 'my-program',
	version = '0.0.1',
	callback = main_loop,
	help_text = 'This is my program uwu',
)

for raw_cmd in cmds:
	arg_parser.add_command(
		names = get_cmd_keys(raw_cmd), 
	    help_text = get_help_text(raw_cmd), 
	    usage = None, 
	    commands = None,
	    parameter_interpreters = tuple(), 
	    parameter_descriptors = tuple(),
	    options = None, 
	    callback = dummy_callback,
	    index = None
	)

for k, raw_opt in enumerate(opts):
	arg_parser.add_option(
		key =  str(k),
		help_text = get_help_text(raw_opt), 
		shortcuts = get_opt_keys(raw_opt),
		parameter_interpreters = 
			[dummy_callback for _ in range(get_opt_parameters(raw_opt))],
		parameter_descriptors = get_opt_parameters(raw_opt), 
		callback = dummy_callback,
		index = None
	)

arg_parser.parse()


