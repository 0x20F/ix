import os
import configparser
import argparse
import re
import threading

os.system('color')


# Colors
RED = "\x1B[31;1m"
CYAN = "\x1B[36m"
GREEN = "\x1B[32;1m"
YELLOW = "\x1B[33;1m"
RESET = "\x1B[0m"
WHITE = '\x1B[37;1m'

def info(message):
    print(CYAN + 'ℹ' + WHITE, message, RESET)

def error(message):
    print(RED + '✖', message, RESET)

def warn(message):
    print(YELLOW + '⚠' + WHITE, message, RESET)

def success(message):
    print(GREEN + '✔' + WHITE, message, RESET)



class File:
    def __init__(self, root, name, notation) -> None:
        self.path = root + '/' + name
        self.name = name
        self.root = root
        self.notation = notation
        
        self.out = ''
        self.prefix = '#'
        
        self.fields = {
            'out': self.__set_out,
            'prefix': self.__set_prefix
        }    


    def get_out(self) -> str:
        if self.out == '':
            return self.path + '.ix'
        
        return self.out


    def __set_out(self, data):
        expanded = os.path.expandvars(data)
        expanded = self.expand_ix_vars(expanded)

        if os.path.isfile(expanded):
            # if it's a file, we save as that file
            pass
        elif os.path.isdir(expanded):
            # If it's a directory, we add the file to that directory
            expanded += '/' + self.name
        else:
            # If it's not a file, and not a directory, then it doesn't exist
            # so we create a directory and assume we want the file to be stored in
            # that directory under the same name
            info('{} does not exist, creating it for the following file: {}'.format(expanded, self.name))
            os.makedirs(expanded)

        self.out = expanded


    def __set_prefix(self, data):
        self.prefix = data


    def parse_field(self, field):
        field, data = field.split(':', 1)

        parse = self.fields.get(field, lambda: 'No such field: ' + field)
        parse(data.strip())


    def parse(self):
        file = open(self.path)
        parsed = self.expand_ix_vars(file.read())

        file.close()
        return parsed


    def expand_ix_vars(self, string):
        pattern = re.compile('%s{{(.+?)}}' % self.prefix, re.MULTILINE)
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
                warn(message.format(full_key, self.path))
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

    for root, _, files in os.walk(root_path):

        for name in files:

            if name.endswith('.ix'):
                info('Found ix file, skipping...')
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


def process_file(file):
    # Regex to find all comments that have something to do with ix
    # so we can remove them in the processed file
    regex = re.compile('^{}.+[\s\S]$'.format(file.notation), re.MULTILINE)
    processed = file.parse()

    for line in re.findall(regex, processed):
        processed = processed.replace(line, '')

    try:
        with open(file.get_out(), 'w') as f:
            f.write(processed)
            f.close()
    except FileNotFoundError:
        error('Could not find output path: {}.\n\tUsed in file: {}'.format(file.get_out(), file.path))
        return

    success('Saving: ' + file.get_out())


def main():
    threads = list()

    files = find_ix(root_path)

    if len(files) > 0:
        info('Found total of {} ix compatible files'.format(len(files)))
        info('Parsing...\n\n')
    else:
        warn('Found no ix compatible files in the given directory: {}'.format(root_path))
        return

    for file in files:
        thread = threading.Thread(target=process_file, args=(file,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()



# Symbol configurations
notation = ':'
trigger = 'ix-config'
entries = [ '//', '#', '--', '--[', '/*', '*' ]
sequence = [ '{{', '}}' ]

# Directory configurations
root_path = os.path.expandvars('$HOME/dots')
config_path = os.path.expandvars('$HOME/.config/ix/ixrc')

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


# Run
if __name__ == '__main__':
    main()
