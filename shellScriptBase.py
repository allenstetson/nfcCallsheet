#! /usr/bin/env python
import argparse

class BaseShellScript(object):
    def __init__(self):
        '''
        Initialization which sets up variable and calls argument registrations
        '''
        self.args = None
        self.parser = None
        self.verbose = False
        self.debug = 0
        self._addDefaultArgs()
        self.registerArgs()

    def _addDefaultArgs(self):
        '''
        Adds arguments which all shell scripts will have.
        '''
        self.parser = argparse.ArgumentParser(description='Base class for shell script <change this description>')
        self.parser.add_argument('-v', '--verbose',
                        	action='store_true',
                        	help='verbose output',
                        	)
        self.parser.add_argument('-d', '--debug',
                        	nargs='?',
                        	const='0',
                        	default='0',
                        	help='debug output level',
                        	)

    def registerArgs(self):
        '''
        This is here as a placeholder for children to add their own arguments to self.parser
        '''
        pass

    def _processArgs(self):
        '''
        Processes the contents of self.parser, assigns some class variables
        '''
        self.args = self.parser.parse_args()
        self.verbose = self.args.verbose
        self.debug = self.args.debug

    def run(self):
        '''
        Meat and potatoes, where the actual script happens
        '''
        self._processArgs()
        self.printTestOutput()  # Fun test

    def printv(self, string):
        '''
        Prints string provided, as long as verbose is True
        '''
        if self.verbose: print(string)

    def printDebug(self, level, string):
        '''
        Prints string provided, as long as the debug level is greater than or equal to the number specified
        '''
        if int(self.debug) >= level: print(string)

    def printTestOutput(self):
        '''
        Fun test output.
        '''
        print(self.args)
        self.printv("I like toast.")
        self.printDebug(3, "Toast is made of bread.")
        self.printDebug(5, "Bread is made of wheat that has been processed.")

if __name__ == "__main__":
    thing = BaseShellScript()
    thing.run()
