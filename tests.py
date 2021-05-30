import unittest
import ix



test_directory = './tests'
test_config = './tests/ixrc'

# Setup ix
ix.config_path = test_config
ix.root_path = test_directory
ix.config = ix.read_config(test_config)


class TestIxParsing(unittest.TestCase):

    def test_find_ix(self):
        files = ix.find_ix(test_directory)
        self.assertEqual(len(files), 1)

    
    def test_read_config(self):
        config = ix.read_config(test_config)
        self.assertTrue(config['random_test_section'] is not None)


    def test_file_processing_prefix(self):
        files = ix.find_ix(test_directory)
        file = files[0]

        # Make sure it loaded the custom prefix
        self.assertEqual(file.prefix, '@')


    def test_file_processing_output_path(self):
        files = ix.find_ix(test_directory)
        file = files[0] # The only one

        # Make sure it found the right output path
        self.assertTrue(file.out != '')

        # Make sure it expanded the variables correctly
        # and didn't leave any traces
        self.assertTrue('$HOME' not in file.out)
        self.assertFalse(any(x in file.out for x in ['@{{', '}}', '@']))


    def test_file_variable_expansion(self):
        files = ix.find_ix(test_directory)
        file = files[0]

        # Check that there are variables within the file
        with open(file.path) as f:
            opened = f.read()
            self.assertTrue(opened.count('@{{') == 3)
            f.close()

        # Parse the file
        parsed = file.parse()

        # Check that there are no more variables within the file
        self.assertTrue(parsed.count('@{{') == 0)




if __name__ == '__main__':
    unittest.main()
    