###############################################################################
# Copyright (c) 2019 Allen Stetson, allen.stetson@gmail.com
# All rights reserved. No duplication allowed.
#
# This file is part of nfdCallsheet.
#
# This software may not be copied and/or distributed without the express
# permission of Allen Stetson.
###############################################################################
"""
database.py - Module containing all code that interacts w/ the database.

Because this is a prototype, the chosen database is sqlite. In a production
situation, this was likely be a full relational database hosted at an official
location.

"""
###############################################################################
# IMPORTS
###############################################################################
import os
import time
import uuid
import sqlite3


###############################################################################
# GLOBALS
###############################################################################
DB_LOCATION = './callsheet.db'


__all__ = [
    "dictFactory",
    "CallsheetDatabase",
    "CallsheetRecord"
]
__author__ = 'astetson'


###############################################################################
# FUNCTIONS
###############################################################################
def dictFactory(cursor, row):
    """Takes database information and packs it into a dict for ease of use.

    Args:
        cursor (sqlite3.Cursor): The cursor from the sqlite connection.

        row (object): The row from the database, could be a tuple or whatever
            value was written into the database.

    Returns:
        dict: The information from the database, in dict form.

    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

###############################################################################
# CLASSES
###############################################################################
class CallsheetDatabase(object):
    """Object providing an interface for interacting with the database."""
    def __init__(self):
        self._initializeDB()

    def _initializeDB(self):
        """Makes the database at the expected location if one doesn't exist."""
        if not os.path.isfile(DB_LOCATION):
            print("No DB found. Creating at {}".format(DB_LOCATION))
            callsheetRecord = CallsheetRecord()
            qmarks = ",".join(callsheetRecord.keys())
            createCommand = "CREATE TABLE callsheet ({})".format(qmarks)
            print(createCommand)
            self._executeDBCmd(createCommand)
        print("DB initialized")

    def _executeDBCmd(self, command):
        """Executes a given command in sqlite3 for the database.

        Establishes the connection with the DB, creates a cursor, executes the
        command, and closes the connection.

        Args:
            command (str): The command to execute in sqlite3.

        """
        connection = sqlite3.connect(DB_LOCATION)
        connection.row_factory = dictFactory
        cur = connection.cursor()
        cur.execute(command)
        connection.commit()
        connection.close()

    def _fetchOneDBCmd(self, command):
        """Runs a fetchone operation with given command.

        This is used for pulling information about one single object from the
        database.

        Args:
            command (str): The command to execute in sqlite3.

        """
        connection = sqlite3.connect(DB_LOCATION)
        connection.row_factory = dictFactory
        cur = connection.cursor()
        cur.execute(command)
        record = cur.fetchone()
        connection.close()
        return record

    def create(self, callsheetRecord):
        """Creates a new record in the database. Uses the uuid as the key.

        Args:
            callsheetRecord (dict): The dict of data to write into the database
                for this record.

        """
        if not 'uuid' in callsheetRecord.keys():
            raise ValueError("Record for creation must contain a UUID.")
        sqlValues = ["'"+str(i)+"'" for i in callsheetRecord.values()]
        writeCommand = "INSERT INTO callsheet ({}) VALUES ({})"
        writeCommand = writeCommand.format(
            ",".join(callsheetRecord.keys()),
            ",".join(sqlValues)
            )
        print("Writing: '{}'".format(writeCommand))
        self._executeDBCmd(writeCommand)

    def update(self, callsheetRecord):
        """Updates an existing record in the DB. Uses uuid as the key.

        Args:
            callsheetRecord (dict): The dict of data to update the record with.

        """
        for key in callsheetRecord.keys():
            updateCommand = "UPDATE callsheet SET {}='{}' WHERE uuid='{}'"
            updateCommand = updateCommand.format(
                key,
                callsheetRecord[key],
                callsheetRecord['uuid']
                )
            self._executeDBCmd(updateCommand)

    def getByUuid(self, recordUuid):
        """Fetches a record from the database using the uuid for the search.

        The uuid is the primary key and would only ever match one record.

        """
        loadCommand = "SELECT * FROM callsheet WHERE uuid = '{}'"
        loadCommand = loadCommand.format(recordUuid)
        record = self._fetchOneDBCmd(loadCommand)
        return record

    def getByName(self, name):
        """Fetches a record from the database using the name for the search.

        The name is not guaranteed to be unique and may match more than one
        record. Because this uses a fetchone, only one of those will be
        returned. It's up to the user to validate the result for the correct
        match.

        """
        loadCommand = "SELECT * FROM callsheet WHERE name = '{}'".format(name)
        record = self._fetchOneDBCmd(loadCommand)
        return record

class CallsheetRecord(dict):
    """Object representing one record.

    Contains all expected attributes for a complete record, and fills some of
    those in with defaults.

    Args:
        **kwargs: Arbitrary keyword arguments, to be added to this record.

    """
    def __init__(self, **kwargs):
        super(CallsheetRecord, self).__init__()
        #self['uuid'] = str(uuid.uuid4())
        self['uuid'] = str(uuid.uuid4())[:5] #To appease Arduino byte limit -- for now
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

    def update(self, **kwargs):
        """Update this object with new values, provided by the user.

        Args:
            **kwargs: Arbitrary keyword arguments, to be added or updated
                within this record.

        """
        for (key, value) in kwargs.items():
            self[key] = value
