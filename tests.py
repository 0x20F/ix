import unittest
import os
import ix



test_directory = './tests'
test_config = './tests/ixrc'

# Setup ix
ix.config_path = test_config
ix.root_path = test_directory
ix.config = ix.read_config(test_config)


class TestIxParsing(unittest.TestCase):

    def test_find_ix(self):
        files = ix.find_ix(test_directory + '/simple')
        self.assertEqual(len(files), 1)


    def test_read_config(self):
        config = ix.read_config(test_config)
        self.assertTrue(config['random_test_section'] is not None)


    def test_prefix(self):
        '''
        Test that the prefix configuration field does the following:
            1. Replaces the original prefix
            2. Does not replace variables that are included with the old prefix
            3. Does replace variables that are included with the new prefix
        '''
        files = ix.find_ix(test_directory + '/with_prefix')
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
        files = ix.find_ix(test_directory + '/no_as')
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
        files = ix.find_ix(test_directory)
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
        files = ix.find_ix(test_directory + '/with_access')
        file = files[0]

        self.assertEqual(file.access, int('777', 8))
        output_path = file.get_output_path()

        ix.process_file(file)
        self.assertTrue(os.access(output_path, os.X_OK))


    def test_ix_extension_when_in_the_same_directory(self):
        '''
        Make sure that the processed file gets saved with an '.ix'
        extension when no custom directory or filename is provided
        as to not overwrite anything in the current one.
        '''
        files = ix.find_ix(test_directory + '/no_to')
        file = files[0]

        self.assertTrue(file.get_output_path().endswith('.ix'))


    def test_file_variable_expansion(self):
        '''
        Make sure ix variables get replaced throughout the
        entire file.
        '''
        files = ix.find_ix(test_directory)
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



if __name__ == '__main__':
    unittest.main()
