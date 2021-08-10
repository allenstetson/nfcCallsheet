###############################################################################
# Copyright (c) 2019 Allen Stetson, allen.stetson@gmail.com
# All rights reserved. No duplication allowed.
#
# This file is part of nfcCallsheet.
#
# This software may not be copied and/or distributed without the express
# permission of Allen Stetson.
###############################################################################
"""
shellscript_base.py - A simple tool framework for creating shell scripts.

This is technically not part of this tool, but since it lived outside of this
package, and was leveraged by this code, I'm rolling it into the same github
repo.

"""
import argparse

class BaseShellScript(object):
    """A basic shell script tool framework which provides some args.

    Using argparse, this framework provides toggleable verbose printing,
    debug level printing, and a default parser to which subclasses can
    add their own commandline arguments.

    """
    def __init__(self):
        """
        Initialization which sets up variable and calls argument registrations
        """
        self.args = None
        self.parser = None
        self.verbose = False
        self.debug = 0
        self._addDefaultArgs()
        self.registerArgs()
        self._processArgs()

    def _addDefaultArgs(self):
        """
        Adds arguments which all shell scripts will have.

        """
        self.parser = argparse.ArgumentParser(
            description='Base class for shell script <change this description>'
            )
        self.parser.add_argument(
            '-v',
            '--verbose',
            action='store_true',
            help='verbose output',
            )
        self.parser.add_argument(
            '-d', '--debug',
            nargs='?',
            const='0',
            default='0',
            help='debug output level',
            )

    def registerArgs(self):
        """
        Placeholder for subclass to add their own arguments to self.parser.

        Does not need to be implemented if there are no additional args, so
        NotImplemented is not raised here.

        """
        pass

    def _processArgs(self):
        """
        Processes the contents of self.parser, assigns some class variables.

        """
        self.args = self.parser.parse_args()
        self.verbose = self.args.verbose
        self.debug = self.args.debug

    def run(self):
        """
        Meat and potatoes, where the actual script happens. Required.
        """
        raise NotImplementedError

    def printv(self, printString):
        """
        Prints string provided, as long as verbose is True.

        Args:
            printString (str): The verbose string to print.

        """
        if self.verbose:
            print(printString)

    def printDebug(self, level, printString):
        """
        Prints string provided if debug level is >= level number specified.

        Args:
            printString (str): The string to print if debug level is met.

        """
        if int(self.debug) >= level:
            print(printString)
