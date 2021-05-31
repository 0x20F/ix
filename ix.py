import os, configparser, argparse
import re, threading, json, hashlib
from datetime import datetime




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
class File:
    '''
    Structured class to keep track of everything about each
    file that needs parsing. Such as the comment type,
    the paths, the ix-configuration, and so on.
    '''
    def __init__(self, root, name, notation) -> None:
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
        expanded = self.expand_ix_vars(expanded)

        # If the given directory does not exist
        # we want to create it.
        if not os.path.isdir(expanded):
            info('{} does not exist, creating it for the following file: {}'.format(expanded, self.name))
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
        self.name = self.expand_ix_vars(data)



    def __set_prefix(self, data):
        '''
        Replace the default prefix for this specific file.

        This is used to parse a specific field from the ix configuration.

        Parameters:
            self (File): The current file object
            data (str): The new prefix
        '''
        self.prefix = self.expand_ix_vars(data)



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
        self.access = int(self.expand_ix_vars(data), 8)



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
    


    def parse_field(self, field):
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



    def parse(self):
        '''
        Parse the contents of the file, replacing
        all variables with their defined values.

        Parameters:
            self (File): The current file obejct
        '''
        file = open(self.original_path)
        parsed = self.expand_ix_vars(file.read())

        file.close()
        return parsed



    def expand_ix_vars(self, string):
        '''
        Look through a given string of data in a file and find every
        variable starting with the prefix defined for that specific file.

        Replace all those variables with their related values inside the
        configuration file.

        Parameters:
            self (File): The current file object
            string (str): The string contents in which to look for variables

        Returns:
            contents (str): The original content with all the variables replaced
        '''
        pattern = re.compile('%s{{(.+?)}}' % re.escape(self.prefix), re.MULTILINE)
        items = re.findall(pattern, string)
        items = set(items)

        if len(items) == 0:
            return string

        contents = string

        for key in items:
            k, v = key.strip().split('.', 1)
            full_key = '{}{}{}{}'.format(self.prefix, sequence[0], key, sequence[1])

            try:
                resolved = config[k][v]
                
                contents = contents.replace(full_key, resolved)
            except:
                message = 'Did not find any items with the name {} in the configuration.\n\tUsed in file: {}\n'
                warn(message.format(full_key, self.original_path))
                continue

        return contents


#    __                  _   _
#   / _|_   _ _ __   ___| |_(_) ___  _ __  ___
#  | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#  |  _| |_| | | | | (__| |_| | (_) | | | \__ \
#  |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
# -------------------------------------------------------------------------
def info(message):      print(CYAN + 'ℹ' + WHITE, message, RESET)
def error(message):     print(RED + '✖', message, RESET)
def warn(message):      print(YELLOW + '⚠' + WHITE, message, RESET)
def success(message):   print(GREEN + '✔' + WHITE, message, RESET)
def log(message):       print(MAGENTA + '~' + WHITE, message, RESET)



def find_ix(root):
    '''
    Find all files that contain the 'ix' trigger so we know what 
    needs parsing.

    Parameters:
        root (str): The directory we're currently in
        files (list): The list of files in the directory we're in

    Returns:
        list: All the files in the directory that contain the trigger
    '''

    ix_files = []

    for root, _, files in os.walk(root):

        for name in files:

            if name.endswith('.ix'):
                continue

            full_path = root + '/' + name
            file = None
            current = None
            found = False

            # Try and open the file as a normal text file
            # Abort if it's binary or something else
            try:
                file = open(full_path, 'r')        
            except PermissionError:
                info('No permission to access file, ignoring: ' + full_path)
                continue
            except:
                info('Found non-text file, ignoring: ' + full_path)
                continue

            lines = []

            # Try and read all the lines from the file
            # Abort if characters can't be parsed
            try:
                lines = list(file)
            except:
                #print('Couldnt parse all characters in file: ' + full_path)
                continue            
            
            # Check the first few lines of the file for the
            # trigger otherwise assume this file is not to be 
            # processed.
            for i, line in enumerate(lines):
                for entry in entries:
                    start = "{}{}".format(entry, notation)
                    
                    if line.startswith(start):
                        if trigger in line:
                            found = True
                            current = File(root, name, start)
                            continue

                        if not found:
                            continue

                        clean = line.replace(start, '').strip()

                        if clean.startswith(tuple(current.fields)):
                            current.parse_field(clean)
                            continue

                if i == 20 and not found:
                    break
            
            if found:
                ix_files.append(current)

            file.close()

    return ix_files



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

        return json.loads(file.read())
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



def process_file(file):
    '''
    Go through the given file's contents and make sure to replace
    all the variables that have matches within the 'ixrc' configuration
    as well as making sure to remove every trace of 'ix' itself from
    the processed file, leaving it nice and clean, as well as making sure
    to add the processed file to the lock file so we don't have to process
    it again unless it's contents change.

    Parameters:
        file (File): The file object to parse
    '''
    # Regex to find all comments that have something to do with ix
    # so we can remove them in the processed file
    regex = re.compile('^{}.+[\s\S]$'.format(file.notation), re.MULTILINE)
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
        error('Could not find output path: {}.\n\tUsed in file: {}'.format(file.get_output_path(), file.original_path))
        return

    success('Saved: {1}{2}{0} to {1}{3}'.format(WHITE, RESET, file.original_path, file.get_output_path()))



def main():
    '''
    The main entrypoint for the program.
    Initializes everything that needs to happen.
    From finding all the 'ix' files to creating new Threads for
    parsing each of the available files, as well as saving and updating
    the lock file once everything has been processed.
    '''
    threads = list()

    files = find_ix(root_path)
    unchanged = 0
    saved = 0

    if len(files) > 0:
        info('Found {} ix compatible files'.format(len(files)))
    else:
        log('Found no ix compatible files in: {}.'.format(root_path))
        log('Exiting.')
        return

    for file in files:
        # Don't run for files that haven't changed
        hash = file.hash_contents()
        lock = lock_file[file.original_path]

        if hash == lock['hash']:
            unchanged += 1
            continue

        thread = threading.Thread(target=process_file, args=(file,))
        threads.append(thread)
        thread.start()

        saved += 1

    for thread in threads:
        thread.join()

    # Logging
    if saved > 0:
        success('Saved {} files'.format(saved))
    
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

# Commandline arguments
parser = argparse.ArgumentParser(description='Find and replace variables in files within a given directory')
parser.add_argument('-c', '--config', help='The path where the .ix configuration is located. Default $HOME/.config/ix/ixrc')
parser.add_argument('-d', '--directory', help='The directory to parse. Default $HOME/dots')

args = parser.parse_args()

if args.directory:
    root_path = args.directory

if args.config:
    config_path = args.config

# Load in the config
config = read_config(config_path)

# Load in the cache
lock_file = read_lock_file(lock_path)


# Run
if __name__ == '__main__':
    # Windows handles colors weirdly by default
    if os.name == 'nt':
        os.system('color')

    main()
