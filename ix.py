import os
import configparser
import argparse
import re
import threading


class File:
    def __init__(self, root, name, notation) -> None:
        self.path = root + '/' + name
        self.name = name
        self.root = root
        self.notation = notation
        self.out = ''
        self.fields = {
            'out': self.__set_out
        }
    

    def get_out(self) -> str:
        if self.out == '':
            return self.path + '.ix'
        
        return self.out


    def __set_out(self, data):
        expanded = os.path.expandvars(data)
        expanded = expand_ix_vars(expanded)

        if os.path.isdir(expanded):
            expanded += '/' + self.name

        self.out = expanded

    
    def parse_field(self, field):
        field, data = field.split(':', 1)

        parse = self.fields.get(field, lambda: 'No such field: ' + field)
        parse(data.strip())


    def parse(self, config):
        file = open(self.path)
        lines = list(file)

        to_replace = set()

        # Find all the keys that need replacing
        for line in lines:
            items = re.findall(pattern, line)

            if len(items) == 0:
                continue

            [ to_replace.add(item) for item in items ]

        file_contents = ''.join(lines)

        # Replace all the available variables
        for key in to_replace:
            k, v = key.strip().split('.', 1)

            try:
                resolved = config[k][v]
                full_key = '{}{}{}'.format(sequence[0], key, sequence[1])

                file_contents = file_contents.replace(full_key, resolved)
            except:
                print('Did not find any items with the name {} in the configuration'.format(key))
                continue

        return file_contents




def find_ix(root, files):
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

    for name in files:
        if name.endswith('.ix'):
            print('Found ix file, skipping...')
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
            print('No permission to access file, ignoring: ' + full_path)
            continue
        except:
            print('Found non-text file, ignoring: ' + full_path)
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

                    if clean.startswith(tuple(data_fields)):
                        current.parse_field(clean)
                        continue

            if i == 20 and not found:
                break
        
        if found:
            ix_files.append(current)


    return ix_files



def expand_ix_vars(string):
    items = re.findall(pattern, string)

    if len(items) == 0:
        return string

    contents = string

    for key in items:
        k, v = key.strip().split('.', 1)

        try:
            resolved = config[k][v]
            full_key = '{}{}{}'.format(sequence[0], key, sequence[1])

            contents = contents.replace(full_key, resolved)
        except:
            print('Did not find any items with the name {} in the configuration'.format(key))
            continue

    return contents



def read_config(at):
    config = configparser.ConfigParser()
    config._interpolation = configparser.ExtendedInterpolation()
    config.read(at)

    return config


def process_file(file):
    regex = re.compile('^{}.+[\s\S]$'.format(file.notation), re.MULTILINE)
    processed = file.parse(config)

    for line in re.findall(regex, processed):
        processed = processed.replace(line, '')

    with open(file.get_out(), 'w') as f:
        f.write(processed)
        f.close()

    print('Saving: ' + file.get_out())


def main():
    threads = list()

    for root, _, files in os.walk(root_path):
        files = find_ix(root, files)

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
data_fields = [ 'out' ]
sequence = [ '#{{', '}}' ]
pattern = re.compile(r'#{{(.+?)}}')

# Directory configurations
root_path = os.path.expandvars('$HOME/dots')
config_path = os.path.expandvars('$HOME/.config/ix/ixrc')
config = read_config(config_path)

# Commandline arguments
parser = argparse.ArgumentParser(description='Find and replace variables in files within a given directory')
parser.add_argument('-c', '--config', help='The path where the .ix configuration is located. Default $HOME/.config/ix/ixrc')
parser.add_argument('-d', '--directory', help='The directory to parse. Default $HOME/dots')

args = parser.parse_args()

if args.directory:
    root_path = args.directory

if args.config:
    config_path = args.config


# Run
main()
