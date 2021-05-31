import os
import configparser
import argparse
import re
import threading
import json
import hashlib
from datetime import datetime

# Windows handles colors weirdly by default
if os.name == 'nt':
    os.system('color')


# Colors
RED = "\x1B[31;1m"
CYAN = "\x1B[36m"
GREEN = "\x1B[32;1m"
YELLOW = "\x1B[33;1m"
RESET = "\x1B[0m"
WHITE = '\x1B[37;1m'
MAGENTA = '\x1B[35;1m'

def info(message):      print(CYAN + 'ℹ' + WHITE, message, RESET)
def error(message):     print(RED + '✖', message, RESET)
def warn(message):      print(YELLOW + '⚠' + WHITE, message, RESET)
def success(message):   print(GREEN + '✔' + WHITE, message, RESET)
def log(message):       print(MAGENTA + '~' + WHITE, message, RESET)



class File:
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
        self.has_custom_name = True
        self.name = data


    def __set_prefix(self, data):
        self.prefix = data


    def __set_access(self, data):
        self.has_custom_access = True
        # Turn the perms to octal since chmod only accepts that
        self.access = int(data, 8)


    def to_dict(self):
        return {
            'hash': self.hash_contents(),
            'output': self.get_output_path(),
            'created_at': str(datetime.now())
        }


    def hash_contents(self):
        if self.hash != '':
            return self.hash

        md5 = hashlib.md5()

        # Hash the template contents so we can lock the file
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
        field, data = field.split(':', 1)

        parse = self.fields.get(field, lambda: 'No such field: ' + field)
        parse(data.strip())


    def parse(self):
        file = open(self.original_path)
        parsed = self.expand_ix_vars(file.read())

        file.close()
        return parsed


    def expand_ix_vars(self, string):
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
    config = configparser.ConfigParser()
    config._interpolation = configparser.ExtendedInterpolation()
    config.read(at)

    return config


def read_lock_file(path):
    try:
        file = open(path + '/ix.lock')

        return json.loads(file.read())
    except FileNotFoundError:
        # Start fresh if the file doesn't exist
        return {}


def save_lock_file(path, data):
    if not os.path.isdir(path):
        os.makedirs(path)

    with open(path + '/ix.lock', 'w') as lock:
        lock.write(json.dumps(data))


def process_file(file):
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
    main()
