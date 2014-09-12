#!/usr/bin/env python

import unittest
import sys
import os
import tempfile

base = os.path.abspath("../../../")
sys.path.append(base)
sys.path.append(base + "/PAV/special_pkgs")
sys.path.append(base + "/PAV/modules")

from PAV.special_pkgs.yapsy.IPlugin import IPlugin
import PAV.plugins.runTestSuitePlugin as RTP

class EnvironmentErrorTest(unittest.TestCase):
    def setUp(self):
        self.suite_runner = RTP.RunTestSuite()

    def test_permission_error(self):
        file_name = "invalid_permissions"
        with open(file_name, 'w+') as f:
            pass
        os.chmod(file_name, 0000)
        with self.assertRaises(SystemExit):
            self.suite_runner.cmd({'testSuite': 'invalid_permissions'})
        os.remove(file_name)

    def test_no_file_error(self):
        with self.assertRaises(SystemExit):
            self.suite_runner.cmd({'testSuite': 'non_existant.yaml'})

    def test_directory_error(self):
        file_path = tempfile.mkdtemp()
        with self.assertRaises(SystemExit):
            self.suite_runner.cmd({'testSuite': file_path})
        os.rmdir(file_path)

if __name__ == '__main__':
    unittest.main(verbosity=2)
