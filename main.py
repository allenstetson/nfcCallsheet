###############################################################################
# Copyright (c) 2019 Allen Stetson, allen.stetson@gmail.com
# All rights reserved. No duplication allowed.
#
# This file is part of nfcCallsheet.
#
# This software may not be copied and/or distributed without the express
# permission of Allen Stetson.
###############################################################################
"""The main entry point for the python portion of nfcCallsheet, run on PC.

This software was designed for use on the motion capture stage at MBS Studios,
and represents a prototype. Rather than having a stage operator manually add
various props to the motion capture callsheet in the capture software (done by
manually entering an ID number found on a sticker attached to each prop), this
software makes it possible for an NFC sticker to be attached to props, and for
those stickers to be scanned at the start of a mocap session, thereby resulting
in the automatic inclusion of the correct prop in the capture software.

nfcCallsheet runs a python portion as well as an arduino portion. The arduino
detects an NFC sticker placed on its reader, and has the capability of writing
data to NFC stickers. In either case, it communicates with the PC portion
(this) to prompt the user for information, or to issue commands on the network
which result in the update of the Callsheet.

"""
###############################################################################
# IMPORTS
###############################################################################
# local imports:
from . import records
from . import shellscript_base
from . import serial_connection


__all__ = [
    "CallsheetCmdlineApp"
]
__author__ = 'astetson'


###############################################################################
# FUNCTIONS
###############################################################################
def queryUserForData():
    """Prompts the user for commandline input to be written to an NFC tag.

    Returns:
        dict: The keys and values that the user provided on the cmdline.

    """
    msg = ("Enter category:value to update - comma-separate multiple "
           "values (name:Xample, recordType:example): ")
    inputStr = input(msg)
    if not ":" in inputStr:
        print("INPUT ERROR: A colon-separated category and value "
              "was expected. (such as family:canine)")
        return {}
    pairs = inputStr.split(',')
    kwargs = {}
    for pair in pairs:
        kwargs[pair.split(":")[0].strip()] = pair.split(":")[1].strip()
    return kwargs


###############################################################################
# CLASSES
###############################################################################
class CallsheetCmdlineApp(shellscript_base.BaseShellScript):
    """A simple implementation of software that can read/write NFC tags.

    In production, this would be a standalone GUI or potentially a plugin to
    the capture software presenting an interface to the user. Because this is
    a prototype, a commandline interface is easiest for a proof of concept.

    """
    def registerArgs(self):
        """Registers the commandline arguments for this tool."""
        self.parser.add_argument(
            '-read',
            help='read NFC Tag, and pull associated record from DB',
            action='store_true',
            )

        self.parser.add_argument(
            '-create',
            help='create a new NFC Tags/DB Record',
            action='store_true',
            )

        self.parser.add_argument(
            '-update',
            help='Updating an existing DB record/tag with new data',
            action='store_true',
            )

        self.parser.add_argument(
            '-assign',
            help='assign a new NFC tag to an existing record',
            action='store_true',
            )

    def run(self):
        """Runs the app.

        Reports the mode in which the app is running based on arguments that
        were provided by the user. As this is a prototype, the app allows for
        that mode to be set once, and then must be exited before restarting in
        a separate mode. Ideally, the mode would be changed by the user as the
        tool was running in a GUI of some sort.

        The correct function is then called based on the current mode.

        """
        super(CallsheetCmdlineApp, self).run()
        if self.args.create:
            print("I'm in Create Mode")
            self.createTagAndRecord()
        elif self.args.update:
            print("I'm in Update Mode.")
            self.updateRecordFromTag()
        elif self.args.assign:
            print("I'm in Assign Mode.")
            self.assignNewTagtoRecord()
        else:
            print("I'm in Read Mode")
            self.readTag()

    def readTag(self):
        """Reads an NFC tag scanned by the user.

        This calls a serial interface which waits for a serial signal from an
        attached Arduino, outfitted with an NFC reader.  When the signal is
        received (and confirmed as an NFC tag data transmission), the payload
        is read and turned into a record.

        This record is printed out for the user to read, in this prototype, but
        in production, the record would be broadcast to the RabbitMQ stream
        that is listening for incoming prop data, thereby adding the prop to
        the callsheet.

        returns:
            dict: The record of keys and values that define this prop.

        """
        record = records.CallsheetRecord()
        record.populateFromTag()
        record.populateFromDatabase()

        print("Record found:")
        print("---------- {} ----------".format(record['name']))
        for key in record.keys():
            if key == 'name':
                continue
            print("{}: {}".format(key.rjust(13), record[key]))
        print("\n")
        return record

    def createTagAndRecord(self):
        """Writes record data to an NFC tag.

        This calls a method to query the user for relevant tag record data,
        then calls a method that writes that data to a serial interface to an
        Arduino which intercepts the serial signal and writes that record to
        an NFC tag.

        """
        args = queryUserForData()
        record = records.CallsheetRecord(**args)
        record.writeToDatabase()
        record.writeToTag()

    def updateRecordFromTag(self):
        """Allows a user to supplement an existing record with new data.

        To accomodate changes to a record, this allows a user to supplement
        an existing record with new keys or different values.

        """
        record = self.readTag()
        print("------")
        kwargs = queryUserForData()
        record.update(kwargs)
        record.writeToDatabase()
        print("Update complete")

    def assignNewTagtoRecord(self):
        """Allows a user to copy a record from one tag to another.

        If a prop gets replaced, or if a user wishes to get a head-start on
        some record data from an existing record, this allows a user to read
        a record from an existing NFC tag, and then write that record to a new
        tag. Alternatively, a user can provide a record name and have that
        record read from a database and then applied to a tag.

        """
        msg = ("Assigning new tag to existing record.  "
               "How would you like to load the record?:\n"
               "  1 - Load record from existing tag\n"
               "  2 - Load record by name\n")
        answer = input(msg).strip()
        if answer == "1":
            # Load record from tag
            record = self.readTag()
            # Give the user time to swap the old tag out with the new one:
            msg = "Hit enter when ready with new tag or type \"cancel\""
            ready = input(msg).strip()
            if ready.lower() == "cancel":
                print("Canceling")
                return
            self._updateRecordWithSwipedTag(record)
        elif answer == "2":
            name = input("Enter name of desired record: ")
            record = records.CallsheetRecord()
            record['name'] = name
            record.populateFromDatabaseByName()
            print("Record for {} retrieved.".format(record['name']))
            self._updateRecordWithSwipedTag(record)
        else:
            print("I did not understand your input. Quitting.")

    def _updateRecordWithSwipedTag(self, record):
        """Writes the a record to a new tag.

        Begins the process of listening for a serial signal from the Arduino,
        indicating that the new tag is ready for write. Then writes data to
        the new NFC tag.

        Args:
            record (dict): The data to write to the NFC tag.

        """
        print("Swipe new tag to associate with this record.")
        nfcSerialHandler = serial_connection.NfcSerialHandler()
        newTagId = nfcSerialHandler.getTagIdFromTag()
        kwargs = {"nfcTagId": newTagId}
        record.update(**kwargs)
        record.writeToDatabase()
        record.writeToTag()


###############################################################################
# EXECUTE
###############################################################################
if __name__ == "__main__":
    app = CallsheetCmdlineApp()
    app.run()
