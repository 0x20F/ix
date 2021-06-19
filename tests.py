import unittest
import os



test_directory = './tests'



class TestIxParsing(unittest.TestCase):

    def test_find_ix(self):
        import ix
        from ix import Parser

        ix.root_path = test_directory

        files = Parser.find_ix(test_directory + '/simple')
        self.assertEqual(len(files), 1)


    def test_read_config(self):
        import ix
        from ix import Parser

        ix.root_path = test_directory

        config = ix.read_config('./tests/test_read_config/ixrc')
        self.assertTrue(config['data'] is not None)


    def test_prefix(self):
        '''
        Test that the prefix configuration field does the following:
            1. Replaces the original prefix
            2. Does not replace variables that are included with the old prefix
            3. Does replace variables that are included with the new prefix
        '''
        import ix
        from ix import Parser

        ix.root_path = test_directory
        ix.config = ix.read_config('./tests/with_prefix/ixrc')

        files = Parser.find_ix(test_directory + '/with_prefix')
        file = files[0]

        self.assertEqual(file.prefix, '$')

        with open(file.original_path) as f:
            opened = f.read()
            self.assertTrue(opened.count('${{') == 3)
            self.assertTrue(opened.count('#{{') == 3)
            f.close()

        parsed = file.parse()

        self.assertTrue(parsed.count('${{') == 0)
        self.assertTrue(parsed.count('#{{') == 3)


    def test_output_directory(self):
        '''
        Test that the output configuration field does the following:
            1. Replaces bash environment variables
            2. Replaces ix variables
            3. When no name is specified, it will store the file under the same name
        '''
        import ix
        from ix import Parser

        ix.root_path = test_directory
        ix.config = ix.read_config('./tests/no_as/ixrc')

        files = Parser.find_ix(test_directory + '/no_as')
        file = files[0] # The only one
        
        self.assertTrue(file.get_output_path() != '')
        self.assertTrue('$HOME' not in file.get_output_path())

        self.assertFalse(any(x in file.get_output_path() for x in ['#{{', '}}', '#']))
        self.assertTrue('palace' in file.get_output_path())

        self.assertTrue(file.get_output_path().endswith('to'))


    def test_output_filename(self):
        '''
        Test that the filename configuration field does the following:
            1. Updates the original file name to the new one
            2. That new filename gets appended to the directory of the file
        '''
        import ix
        from ix import Parser

        ix.root_path = test_directory
        ix.config = ix.read_config('./tests/filename/ixrc')

        files = Parser.find_ix(test_directory + '/with_filename')
        file = files[0]

        name = file.name
        test_name = 'testName'

        self.assertEqual(name, test_name)
        self.assertEqual(file.get_output_path(), file.to + '/testName')


    def test_file_permissions(self):
        '''
        Test that the access configuration field updates the final file
        permissions
        '''
        import ix
        from ix import Parser

        ix.root_path = test_directory

        files = Parser.find_ix(test_directory + '/with_access')
        file = files[0]

        self.assertEqual(file.access, int('777', 8))
        output_path = file.get_output_path()

        Parser.process_file(file)
        self.assertTrue(os.access(output_path, os.X_OK))


    def test_ix_extension_when_in_the_same_directory(self):
        '''
        Make sure that the processed file gets saved with an '.ix'
        extension when no custom directory or filename is provided
        as to not overwrite anything in the current one.
        '''
        import ix
        from ix import Parser

        ix.root_path = test_directory
        ix.config = ix.read_config('./tests/no_to/ixrc')

        files = Parser.find_ix(test_directory + '/no_to')
        file = files[0]

        print(file.name)

        self.assertTrue(file.get_output_path().endswith('.ix'))


    def test_file_variable_expansion(self):
        '''
        Make sure ix variables get replaced throughout the
        entire file.
        '''
        import ix
        from ix import Parser

        ix.root_path = test_directory
        ix.config = ix.read_config('./tests/with_variables/ixrc')

        files = Parser.find_ix(test_directory + '/with_variables')
        file = files[0]

        # Check that there are variables within the file
        with open(file.original_path) as f:
            opened = f.read()
            self.assertTrue(opened.count('@{{') == 3)
            f.close()

        # Parse the file
        parsed = file.parse()

        # Check that there are no more variables within the file
        self.assertTrue(parsed.count('@{{') == 0)


    def test_helper_file_inclusion(self):
        import ix
        from ix import Parser

        ix.root_path = test_directory + '/helpers_inclusion'
        ix.config = ix.read_config(ix.root_path + '/ixrc')

        file = Parser.find_ix(ix.root_path).pop()
        parsed = file.parse()

        self.assertTrue('UNIQUE{ TEMPLATE_CONTENT }' in parsed)


    def test_helper_casing(self):
        import ix
        from ix import Parser

        ix.root_path = test_directory + '/helpers_casing'
        ix.config = ix.read_config(ix.root_path + '/ixrc')

        file = Parser.find_ix(ix.root_path).pop()
        parsed = file.parse()

        self.assertTrue('UPPERCASE' in parsed)
        self.assertTrue('lowercase' in parsed)

        self.assertTrue('#[[' not in parsed)


    def test_helper_colors(self):
        import ix
        from ix import Parser

        ix.root_path = test_directory + '/helpers_colors'
        ix.config = ix.read_config(ix.root_path + '/ixrc')

        file = Parser.find_ix(ix.root_path).pop()
        parsed = file.parse()

        # rgb
        self.assertTrue('rgb(24, 27, 33)' in parsed)

        # just rgb
        self.assertTrue('rgb(123, 123, 123)' in parsed)

        # just rgb override opacity
        self.assertTrue('rgba(123, 123, 123, 0.3)' in parsed)

        # rgba
        self.assertTrue('rgba(24, 27, 33, 0.5)' in parsed)

        # rgba from hexa
        self.assertTrue('rgba(24, 27, 33, 0.47' in parsed)

        # rgb from variable
        self.assertTrue('rgb(0, 0, 0)' in parsed)

        # rgb from variable with opacity
        self.assertTrue('rgba(0, 0, 0, 0.5)' in parsed)

        # rgb from hex alpha variable
        self.assertTrue('rgba(0, 0, 0, 0.3)' in parsed)

        # rgb hex alpha variable override
        self.assertTrue('rgba(0, 0, 0, 0.8)' in parsed)

        # hex
        self.assertTrue('#ffffff' in parsed)

        # just hex
        self.assertTrue('#7289da' in parsed)

        # just hex override opacity
        self.assertTrue('#7289da4c' in parsed)

        # hex with alpha
        self.assertTrue('#ffffffe6' in parsed)

        # hex with alpha from rgba
        self.assertTrue('#ffffff4c' in parsed)

        # hex from variable
        self.assertTrue('#f2f2f2' in parsed)

        # hex from variable with opacity
        self.assertTrue('#f2f2f280' in parsed)

        # hex from rgba variable
        self.assertTrue('#f2f2f24c' in parsed)

        # hex rgba variable override
        self.assertTrue('#f2f2f266' in parsed)

        # hex rgb to argb
        self.assertTrue('#66f2f2f2' in parsed)

        # hex rgba to argb
        self.assertTrue('#66000000' in parsed)


    def test_helper_variable_format(self):
        import ix
        from ix import Parser

        ix.root_path = test_directory + '/helpers'
        ix.config = ix.read_config(ix.root_path + '/ixrc')

        file = Parser.find_ix(ix.root_path).pop()
        parsed = file.parse()

        self.assertTrue('COOLVALUE' in parsed)
        self.assertTrue('coolvalue' in parsed)


if __name__ == '__main__':
    # Windows handles colors weirdly by default
    if os.name == 'nt':
        os.system('color')

    unittest.main()
