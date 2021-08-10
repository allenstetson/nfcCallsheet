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
records.py - Object representing a DB record, a prop on the mocap stage.

"""
###############################################################################
# IMPORTS
###############################################################################
import time
import uuid

# local imports
from . import database
from . import serial_connection


###############################################################################
# GLOBALS
###############################################################################
CALLSHEET_DB = database.CallsheetDatabase()


__all__ = [
    "CallsheetRecord"
]
__author__ = 'astetson'


###############################################################################
# FUNCTIONS
###############################################################################
def create(**kwargs):
    """Create a record based on incoming data, write it to DB and to a tag.

    Args:
        **kwargs: Arbitrary keyword arguments, to be written to the record.

    """
    record = CallsheetRecord(**kwargs)
    record.populateTagIdFromTag()
    record.writeToDatabase()
    record.writeToTag()


###############################################################################
# CLASSES
###############################################################################
class CallsheetRecord(dict):
    """Object representing one record.

    Contains all expected attributes for a complete record, and fills some of
    those in with defaults.

    Args:
        **kwargs: Arbitrary keyword arguments, to be added to this record.

    """
    def __init__(self, **kwargs):
        super(CallsheetRecord, self).__init__()
        # To appease Arduino byte limit, truncate ID to 5 characters:
        self['uuid'] = str(uuid.uuid4())[:5]
        self['name'] = ""
        self['nfcTagId'] = ""
        self['recordType'] = ""
        self['scale'] = 1
        self['location'] = "mbsStage26"
        self['created'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.update(**kwargs)

    def loadFromDBRecord(self, record):
        """Given a DB record, populate this object with its keys and values.

        Args:
            record (dict): The record from the database.

        """
        for keyname in record.keys():
            self[keyname] = record[keyname]

    def populateFromDatabase(self):
        """Populate the attributes of this object by pulling up a DB entry.

        This object's uuid attribute is used as the key to query the DB.

        """
        recordData = CALLSHEET_DB.getByUuid(self['uuid'])
        self.update(recordData)

    def populateFromDatabaseByName(self):
        """Populate the attrs of this object by pulling up a DB entry by name.

        This object's name attribute is used as the key to query the DB.

        """
        recordData = CALLSHEET_DB.getByName(self['name'])
        self.update(recordData)

    def populateTagIdFromTag(self):
        """Populates the nfcTagId attr of this object by reading an NFC tag."""
        ndefData = serial_connection.NfcSerialHandler().readTag()
        self['nfcTagId'] = ndefData['uid']

    def populateFromTag(self):
        """Populate the attributes of this object by reading an NFC tag."""
        ndefData = serial_connection.NfcSerialHandler().readTag()
        self['nfcTagId'] = ndefData['uid']
        self.populateTagIdFromTag()
        for key, value in ndefData:
            if key == "nfcTagId":
                pass
            self[key] = value

    def update(self, **kwargs):
        """Update this object with new values, provided by the user.

        Args:
            **kwargs: Arbitrary keyword arguments, to be added or updated
                within this record.

        """
        for (key, value) in kwargs.items():
            self[key] = value

    def writeToDatabase(self):
        """Write this record to the database."""
        CALLSHEET_DB.create(self)

    def writeToTag(self):
        """Write this record to an NFC tag."""
        serial_connection.NfcSerialHandler().writeTag(self['uuid'])
