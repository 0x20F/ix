import os, configparser, argparse
import re, threading, json, hashlib
import pathlib
from datetime import datetime



# Global verbosity check
# Get's changed by command line flag '-v'
verbose = False


# Colors
RED     = '\x1B[31;1m'
CYAN    = '\x1B[36m'
GREEN   = '\x1B[32;1m'
YELLOW  = '\x1B[33;1m'
RESET   = '\x1B[0m'
WHITE   = '\x1B[37;1m'
MAGENTA = '\x1B[35;1m'


#        _
#    ___| | __ _ ___ ___  ___  ___
#   / __| |/ _` / __/ __|/ _ \/ __|
#  | (__| | (_| \__ \__ \  __/\__ \
#   \___|_|\__,_|___/___/\___||___/
# -------------------------------------------------------------------------
class Parser:
    @staticmethod
    def get_config_key(key):
        '''
        Given a key of the format 'key.value', find out what the
        value for the variable of that format is within the ix config
        '''
        try:
            k, v = key.strip().split('.', 1)
            return config[k][v]
        except:
            return None



    @staticmethod
    def get_secondary_key_value(key):
        '''
        Unwrap whether or not a configuration value exists
        for the given key.

        Parameters:
            key (str): The key to look for

        Returns:
            str: The value, or null
        '''
        value = Parser.get_config_key(key)

        if not value:
            return None

        return os.path.expandvars(value)



    @staticmethod
    def get_main_key_value(key):
        '''
        Unwrap whether or not a configuration value exists
        for the given key, as well as making sure to unravel
        any helpers within the provided key.

        Parameters:
            key (str): The key to look for

        Returns:
            str: The value, or null
        '''
        stripped = key.strip()
        value = None

        if len(stripped.split(' ', 1)) == 1:
            value = Parser.get_config_key(key)
            if not value: return None

            return os.path.expandvars(value)

        # Check for helpers
        helper, parameters = stripped.split(' ', 1)
        parameters = [ param.strip() for param in parameters.split(';') ]
        
        # First argument doesn't have a name
        main = parameters.pop(0)
        main = Parser.get_config_key(main) or main

        modifier_keys = list()
        modifier_values = list()

        for param in parameters:
            name, value = param.split(':')

            name = name.strip()
            value = value.strip()

            modifier_keys.append(name)
            modifier_values.append(Parser.get_config_key(value) or value)

        modifiers = dict(zip(modifier_keys, modifier_values))
        value = Helpers.call(helper, main, modifiers)
            
        return os.path.expandvars(value)



    @staticmethod
    def parse_secondary_keys(string, prefix):
        '''
        Find secondary variables within a file ( these are variables within main variables ),
        denoted by '[]', and look whether or not they have a defined value inside the configuration
        file.

        If they do, replace the variable with the value from the configuration.

        Parameters:
            string (str): The data we want to look through for variables
            prefix (str): What prefix the parent variables are denoted by
        '''
        pattern = re.compile('%s{{.+\\[(.+?)\\].+}}' % re.escape(prefix), re.MULTILINE)
        items = set(re.findall(pattern, string))
        unmatched = None

        contents = string

        for key in items:
            value = Parser.get_secondary_key_value(key)

            if not value:
                if not unmatched: unmatched = []
                unmatched.append(f'[{key}]')
                continue

            contents = contents.replace(f'[{ key }]', value)

        return ( contents, unmatched )



    @staticmethod
    def parse_main_keys(string, prefix):
        '''
        Find main variables within a file ( something like ${{}} ) and look
        whether or not they have a defined value inside the configuration file.

        If they do, repalce the variable with the value from the configuration.

        Parameters:
            string (str): The data we want to look through for variables
            prefix (str): What prefix the variables are denoted by
        '''
        pattern = re.compile('%s{{(.+?)}}' % re.escape(prefix), re.MULTILINE)
        items = set(re.findall(pattern, string))
        unmatched = None

        contents = string

        for key in items:
            full_key = '{}{}{}{}'.format(prefix, sequence[0], key, sequence[1])
            value = Parser.get_main_key_value(key)

            if not value:
                if not unmatched: unmatched = []
                unmatched.append(full_key)
                continue

            contents = contents.replace(full_key, value)

        return (contents, unmatched)



    @staticmethod
    def expand_ix_vars(string, prefix):
        '''
        Look through a given string of data in a file and find every
        variable starting with the prefix defined for that specific file.

        Replace all thos variables with their related values inside the
        configuration file.

        Parameters:
            string (str): The string contents in which to look for variables
            prefix (str): The prefix used for including the variables in the given string

        Returns:
            contents (str): The original content with all the variables replaced
            unmatched (list): The keys for all the variables that couldn't be matched within the string
        '''
        contents, unmatched_secondary = Parser.parse_secondary_keys(string, prefix)
        contents, unmatched_main = Parser.parse_main_keys(contents, prefix)

        if not unmatched_secondary: unmatched_secondary = []
        if not unmatched_main: unmatched_main = []

        unmatched = unmatched_main + unmatched_secondary

        return (contents, unmatched)



    @staticmethod
    def wrap_file(file_path):
        '''
        Wrap a file and its contents in the custom File class
        to allow for easier handling.

        This finds whether or not a file is ix compatible, what
        comment type it uses, and makes sure to setup all the ix
        configuration found within the file.

        Parameters:
            file_path (str): The path to the file we want to wrap
        '''
        root, name = file_path.rsplit('/', 1)

        file = get_file_lines(file_path)
        if not file:
            return None

        lines = list(file)
        found = False
        current = None

        # Check the first few lines of the file for the trigger.
        # If the trigger isn't found, assume this file shouldn't
        # be processed.
        for idx, line in enumerate(lines):
            for entry in entries:
                start = '{}{}'.format(entry, notation)

                if line.startswith(start):
                    if trigger in line:
                        found = True
                        current = File(root, name, start)
                        continue

                    if not found:
                        continue

                    clean = line.replace(start, '').strip()

                    if clean.startswith(tuple(current.fields)):
                        current.load_field(clean)
                        continue

            if idx == 20 and not found:
                return None

        return current



    @staticmethod
    def find_ix(root):
        '''
        Find all files that contain the 'ix' trigger so we know what
        needs parsing.

        Parameters:
            root (str): The directory to look into for files

        Returns:
            list: All the files in the directory that contain the trigger
        '''
        ix_files = []

        for root, _, files in os.walk(root):
            for name in files:
                if name.endswith('.ix'): continue

                full_path = root + '/' + name
                file = Parser.wrap_file(full_path)

                if file:
                    ix_files.append(file)

        return ix_files



    @staticmethod
    def process_file(file):
        '''
        Go through the given file's contents and make sure to replace
        all the variables that have matches within the 'ixrc' configuration
        as well as making sure to remove every trace of 'ix' itself from
        the processed file, leaving it nice and clean, as well as making sure
        to add the processed file, to the lock file so we don't have to process
        it again unless it's contents change.

        Parameters:
            file (File): The file object to parse
        '''
        regex = re.compile('^{}.+[\\s\\S]$'.format(file.notation), re.MULTILINE)
        processed = file.parse()

        for line in re.findall(regex, processed):
            processed = processed.replace(line, '')

        try:
            with open(file.get_output_path(), 'w') as f:
                f.write(processed)
                f.close()

            if file.has_custom_access:
                os.chmod(file.get_output_path(), file.access)

            lock_file[file.original_path] = file.to_dict()
        except FileNotFoundError:
            error('Could not find output path: {}.\n\tUsed in file: {}'.format(file.get_output_path(), file.original_path), True)
            return

        success('Saved: {1}{2}{0} to {1}{3}'.format(WHITE, RESET, file.original_path, file.get_output_path()), True)



class Helpers:
    '''
    List of all the helpers that can be used within files when
    including variables and/or templating

    Helpers can only be used within main variables, aka. '${{ thing.thing }}'

    Parameters:
        helper (str): The name of the helper function to run
        value (str/int): The value to perform the function on
        modifiers (dict): Extra parameters passed to the helper to further tweak the value
    '''
    @staticmethod
    def call(helper, value, modifiers):
        '''
        Call a specific helper, if defined
        '''
        try:
            method = getattr(Helpers, helper)
            return method(value, **modifiers)
        except Exception as e:
            error(f'{e!r} ---- helper: {helper}')
            return ''


    @staticmethod
    def rgb(value, alpha = None):
        '''
        Take a hex string ( #181b21 ) and convert it to 'rgb'.
        If an rgb or rgba string is provided, if the opacity isn't
        overwritten, it'll just return the string that was passed in.
        If the opacity is overwritten, however, it'll replace the alpha
        field within the given string.

        Optionally, pass in opacity to override or add the alpha channel.
        '''
        # We got an rgb value
        if not value.startswith('#'):
            # Give it back as it is if no overrides are specified
            if not alpha: return value

            values = [ x.strip() for x in value.split('(', 1).pop().rstrip(')').split(',') ]

            r = values[0]
            g = values[1]
            b = values[2]
            a = alpha

            return f'rgba({r}, {g}, {b}, {a})'


        string = value.lstrip('#')
        r, g, b = tuple(int(string[i:i+2], 16) for i in (0, 2, 4))
        a = ''

        if len(string) == 8:
            a = round(int(string[6:6+2], 16) / 255, 2)

        if alpha:
            a = alpha

        if a != '': tag = f'rgba({r}, {g}, {b}, {a})'
        else:       tag = f'rgb({r}, {g}, {b})'

        return tag


    @staticmethod
    def hex(value, alpha = None, argb = None):
        '''
        Take an rgb/rgba string and convert it to a hex representation
        of the same color. If a hex string is provided, it'll return the exact
        same hex string unless the opacity is overwritten. If it is, it'll
        replace the alpha field within the given string.

        Optionally pass in opacity to override or add the alpha channel.
        '''
        if alpha:
            alpha = hex(round(float(alpha) * 255))[2:]
            
        # We got a hex string
        if value.startswith('#'):
            # Give it back as it is if no overrides are specified
            if not alpha: return value

            value = value[1:7]

            if argb:
                return f'#{alpha}{value}'

            return f'#{value}{alpha}'
            
        a = value.startswith('rgba')
        value = value.split('(', 1).pop().rstrip(')').split(',')

        r = hex(int(value[0]))[2:]
        g = hex(int(value[1]))[2:]
        b = hex(int(value[2]))[2:]
        a = hex(round(float(value[3]) * 255))[2:] if a else ''

        if alpha: a = alpha

        if argb:
            return f'#{a}{r}{g}{b}'
            
        return f'#{r}{g}{b}{a}'


    @staticmethod
    def include(path):
        '''
        Include a given file directly into the current file.
        This allows you to import/merge multiple files into one.

        If the file you're importing is an ix compatible file,
        it will be parsed, otherwise the plain text will be included.

        Environment variables work, as well as ix variables.
        '''
        path = os.path.expandvars(path)
        file = Parser.wrap_file(path)

        # If it's not an ix file just read the contents
        if not file:
            with open(path) as f:
                return f.read()

        contents, _ = Parser.expand_ix_vars(file)

        return contents


    @staticmethod
    def uppercase(string):
        '''
        Turn a given string to uppercase.

        Environment variables work, as well as ix variables.
        '''
        return string.upper()


    @staticmethod
    def lowercase(string):
        '''
        Turn a given string to lowercase.

        Environment variables work, as well as ix variables.
        '''
        return string.lower()



class File:
    '''
    Structured class to keep track of everything about each
    file that needs parsing. Such as the comment type,
    the paths, the ix-configuration, and so on.
    '''
    def __init__(self, root, name, notation = '#') -> None:
        self.original_path = root + '/' + name
        self.name = name
        self.notation = notation
        self.hash = ''

        # Flags
        self.has_custom_dir = False
        self.has_custom_name = False
        self.has_custom_access = False

        # Config fields
        self.to = root
        self.prefix = '#'
        self.access = ''

        self.fields = {
            'to': self.__set_to,
            'out': self.__set_to,

            'as': self.__set_as,
            'name': self.__set_as,

            'prefix': self.__set_prefix,

            'access': self.__set_access
        }



    def get_output_path(self) -> str:
        '''
        Get the full (directory + filename) path for the current file.
        Making sure to account for the location, and add an '.ix' extension
        to the filename if the directory is the same as the original file.

        We do not want to overwrite the original file.

        Parameters:
            self (File): The current file object
        '''
        extension = ''

        # If no custom directory was defined
        # and no custom filename was defined
        # we add '.ix' to the original file name
        # when saving so we don't overwrite the original
        if not self.has_custom_dir:
            if not self.has_custom_name:
                extension = '.ix'

        # If we have a custom directory
        # we write to that directory, with whatever the current
        # name is.
        return self.to + '/' + self.name + extension



    def load_field(self, field):
        '''
        Parse a given 'ix' configuration field. Usually comes in the following
        format `out: /path/to/whatever`. Find out what item this configuration
        field refers to and run the expected actions for said item.

        Parameters:
            self (File): The current file object
            field (str): The field line directly from a file, with the comment stripped
        '''
        field, data = field.split(':', 1)

        parse = self.fields.get(field, lambda: 'No such field: ' + field)
        parse(data.strip())



    def __set_to(self, data):
        '''
        Update the directory that the processed file should be saved
        to once done, making sure to create said directory if it
        doesn't exist already and to expand any environment variables
        or 'ix' variables within it.

        This is used to parse a specific field from the ix configuration.

        Parameters:
            self (File): The current file object
            data (str): The new output directory
        '''
        expanded = os.path.expandvars(data)
        expanded = self.__unwrap_parse(Parser.expand_ix_vars(expanded, self.prefix))

        # If the given directory does not exist
        # we want to create it.
        if not os.path.isdir(expanded):
            info('{} does not exist, creating it for the following file: {}'.format(expanded, self.name), True)
            os.makedirs(expanded)

        self.has_custom_dir = True
        self.to = expanded



    def __set_as(self, data):
        '''
        Update the name that the processed file should have when it
        gets saved to the file system.

        This is used to parse a specific field from the ix configuration.

        Parameters:
            self (File): The current file object
            data (str): The new file name + extension (if any)
        '''
        self.has_custom_name = True
        self.name = self.__unwrap_parse(Parser.expand_ix_vars(data, self.prefix))



    def __set_prefix(self, data):
        '''
        Replace the default prefix for this specific file.

        This is used to parse a specific field from the ix configuration.

        Parameters:
            self (File): The current file object
            data (str): The new prefix
        '''
        expanded = self.__unwrap_parse(Parser.expand_ix_vars(data, self.prefix))
        self.prefix = expanded



    def __set_access(self, data):
        '''
        Take in a decimal string of permissions in 'chmod' format
        and turn them into an octal value instead since that is the
        only format the python implementation of chmod will accept.

        This is used to parse a specific field from the ix configuration.

        Parameters:
            self (File): The current file object
            data (str): The permissions in 'chmod' format
        '''
        self.has_custom_access = True
        # Turn the perms to octal since chmod only accepts that
        expanded = self.__unwrap_parse(Parser.expand_ix_vars(data, self.prefix))
        self.access = int(expanded, 8)



    def __unwrap_parse(self, parsed):
        '''
        Spread the tuple returned from an expansion of ix variables and making
        sure to display a message if some variables were not found.

        Parameters:
            self (File): The current instance
            parsed (tuple): (parsed contents, unmatched variables)
        '''
        contents, unmatched = parsed

        if unmatched:
            variables = '\n\t'.join(unmatched)
            warn(f'Could not find\n\t{ variables }\n in { self.original_path }\n', True)

        return contents



    def to_dict(self):
        '''
        Put everything about this file that we want to store in
        the lock file within a dictionary

        Parameters:
            self (File): The current file object
        '''
        return {
            'hash': self.hash_contents(),
            'output': self.get_output_path(),
            'created_at': str(datetime.now())
        }



    def hash_contents(self):
        '''
        Hash the entire file contents, not all at once of course,
        do it in chunks in case we hit some massive files we don't want to
        eat up all the RAM.

        The hash is later used to create unique identifiers for different purposes.
        One of which is to store the hash in the lock file and later compare when
        checking whether or not a file should be parsed again.

        The hashing is done in md5 since it's fast and we really don't have to
        worry about colisions. The chances of the same file colliding are extremely
        small.

        Parameters:
            self (File): The current file object
        '''
        if self.hash != '':
            return self.hash

        md5 = hashlib.md5()

        with open(self.original_path, 'rb') as bytes:
            while True:
                data = bytes.read(65536)

                if not data:
                    break

                md5.update(data)

        digest = md5.hexdigest()
        self.hash = digest

        return digest



    def parse(self):
        '''
        Parse the contents of the file, replacing
        all variables with their defined values.

        Parameters:
            self (File): The current file obejct
        '''
        file = open(self.original_path)
        contents = self.__unwrap_parse(Parser.expand_ix_vars(file.read(), self.prefix))
        file.close()

        return contents



#    __                  _   _
#   / _|_   _ _ __   ___| |_(_) ___  _ __  ___
#  | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#  |  _| |_| | | | | (__| |_| | (_) | | | \__ \
#  |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
# -------------------------------------------------------------------------
def out(message, forced = False):
    if forced or verbose:
        print(message)

def info(message, f = False):      out(CYAN + 'ℹ ' + WHITE + message + RESET, f)
def error(message, f = False):     out(RED + '✖ ' + message + RESET, f)
def warn(message, f = False):      out(YELLOW + '⚠ ' + WHITE + message + RESET, f)
def success(message, f = False):   out(GREEN + '✔ ' + WHITE + message + RESET, f)
def log(message, f = False):       out(MAGENTA + '~ ' + WHITE + message + RESET, f)



def get_file_lines(file_path):
    '''
    Try and open a file as a normal text file.
    If succeeded, return an array of all the lines
    inside that file.
    '''
    try:
        # Try and open the file as a normal text file
        # Abort if it's binary or something else
        file = open(file_path, 'r')
        lines = list(file)
        file.close()

        return lines
    except PermissionError:
        info('No permission to access file, ignoring: ' + file_path)
        return None
    except:
        info('Found non-text file, ignoring: ' + file_path)
        return None



def read_config(at):
    '''
    Read the 'ix' configuration from it's specific path.
    Either user defined, or the default one. Use config parser
    to load and resolve all the magic that the .ini format provides.

    Parameters:
        at (str): The exact path to the config file
    '''
    config = configparser.ConfigParser()
    config._interpolation = configparser.ExtendedInterpolation()
    config.read(at)

    return config



def read_lock_file(path):
    '''
    Read a JSON file into a dictionary allowing us to do
    quick lookups for specific files whenever we need to check
    if one was already parsed or not, allowing us to skip part of the
    process.

    Parameters:
        path (str): The directory of the lock file
    '''
    try:
        file = open(path + '/ix.lock')
        contents = json.loads(file.read())
        file.close()
        return contents
    except FileNotFoundError:
        # Start fresh if the file doesn't exist
        return {}



def save_lock_file(path, data):
    '''
    Save a dictionary full of all parsed files to a file.
    This will be used later on when 'ix' runs again in order
    to check which files have changed and only re-process those files.

    Giving a bit of a performance boost in very large directories.

    Parameters:
        path (str): The directory of the lock file
        data (dict): Dictionary full of all the file data that we care about saving
    '''
    if not os.path.isdir(path):
        os.makedirs(path)

    with open(path + '/ix.lock', 'w') as lock:
        lock.write(json.dumps(data))



def cleanup():
    '''
    Attempt to remove all the files that were previously
    processed and stored in the cache, making sure to 
    clear the cache when done so we're starting fresh.
    '''
    lock = read_lock_file(lock_path)

    info('Purging all previous builds before...', True)

    if lock == {}:
        log('Found no items in cache, exiting...', True)

    for _, entry in lock.items():
        file = entry['output']

        try:
            os.remove(file)
        except Exception as e:
            error(f"Couldn't remove: {file} - {e!r}")

    save_lock_file(lock_path, {})
    success('Done', True)



def main():
    '''
    The main entrypoint for the program.
    Initializes everything that needs to happen.
    From finding all the 'ix' files to creating new Threads for
    parsing each of the available files, as well as saving and updating
    the lock file once everything has been processed.
    '''
    threads = list()

    files = Parser.find_ix(root_path)
    unchanged = 0
    saved = 0

    if len(files) > 0:
        info('Found {} ix compatible files'.format(len(files)))
    else:
        log('Found no ix compatible files in: {}.'.format(root_path))
        log('Exiting.')
        return

    for file in files:
        if file.original_path in lock_file:
            hash = file.hash_contents()
            lock = lock_file[file.original_path]

            # Don't run for files that haven't changed
            if lock and hash == lock['hash']:
                unchanged += 1
                continue

        thread = threading.Thread(target=Parser.process_file, args=(file,))
        threads.append(thread)
        thread.start()

        saved += 1

    for thread in threads:
        thread.join()

    # Logging
    if saved > 0:
        success('Saved {} files'.format(saved), True)

    if unchanged > 0:
        log('Skipped {} files because they were unchanged'.format(unchanged))

    # Cache all the parsed files
    save_lock_file(lock_path, lock_file)



#                    __ _                       _   _
#    ___ ___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __
#   / __/ _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \
#  | (_| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |
#   \___\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|
#                         |___/
# -------------------------------------------------------------------------
# Symbol configurations
notation = ':'
trigger = 'ix-config'
entries = [ '//', '#', '--', '--[', '/*', '*' ]
sequence = [ '{{', '}}' ]

# Directory configurations
root_path = os.path.expandvars('$HOME/dots')
config_path = os.path.expandvars('$HOME/.config/ix/ixrc')
lock_path = os.path.expandvars('$HOME/.cache/ix')
lock_file = None
config = None

# Commandline arguments
parser = argparse.ArgumentParser(description='Find and replace variables in files within a given directory')
parser.add_argument('-c', '--config', help='The path where the .ix configuration is located. Default $HOME/.config/ix/ixrc')
parser.add_argument('-d', '--directory', help='The directory to parse. Default $HOME/dots')
parser.add_argument('-f', '--field', help='Get a specific field value from the config')
parser.add_argument('--full', help='Skip looking at the cache and parse everything', action='store_false')
parser.add_argument('--reverse', help='Remove all the parsed files (everything defined in the cache)', action='store_true')
parser.add_argument('-v', '--verbose', help='Output extra information about what is happening', action='store_true')

args = parser.parse_args()

if args.verbose:
    verbose = True;

if args.config:
    config_path = args.config

if args.field:
    config = read_config(config_path)
    contents = Parser.get_main_key_value(args.field)
    print(contents)

    # The whole thing doesn't need to run
    # if only one field is needed
    exit()

if args.directory:
    root_path = pathlib.Path(args.directory).absolute()

# Load in the cache if not specified
# otherwise.
if not args.full:
    lock_file = {}
else:
    lock_file = read_lock_file(lock_path)


# Load in the config
config = read_config(config_path)


# Run
if __name__ == '__main__':
    # Windows handles colors weirdly by default
    if os.name == 'nt':
        os.system('color')

    if not args.full:
        info('Skipping cache, doing a full parse...', True)
        cleanup()
    
    if args.reverse:
        cleanup()

    main()
