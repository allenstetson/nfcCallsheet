#! /usr/local/bin/python

__author__ = 'astetson'

import os
import time
import uuid
import sqlite3

DB_LOCATION = './callsheet.db'

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class CallsheetDatabase(object):
    def __init__(self):
        self._initializeDB()

    def _initializeDB(self):
        if not os.path.isfile(DB_LOCATION):
            print("No DB found. Creating at %s" % DB_LOCATION)
            callsheetRecord = CallsheetRecord()
            qmarks = ",".join(callsheetRecord.keys())
            createCommand = "CREATE TABLE callsheet (%s)" % qmarks
            print(createCommand)
            self._executeDBCmd(createCommand)
        print("DB initialized")

    def _executeDBCmd(self, command):
        connection = sqlite3.connect(DB_LOCATION)
        connection.row_factory = dict_factory
        cur = connection.cursor()
        cur.execute(command)
        connection.commit()
        connection.close()

    def _fetchOneDBCmd(self, command):
        connection = sqlite3.connect(DB_LOCATION)
        connection.row_factory = dict_factory
        cur = connection.cursor()
        cur.execute(command)
        record = cur.fetchone()
        connection.close()
        return record

    def create(self, callsheetRecord):
        if not 'uuid' in callsheetRecord.keys():
            raise ValueError("Record for creation must contain a UUID.")
        sqlValues = ["'"+str(i)+"'" for i in callsheetRecord.values()]
        writeCommand = "INSERT INTO callsheet (%s) VALUES (%s)" % \
                       (",".join(callsheetRecord.keys()), ",".join(sqlValues))
        print("Writing: '%s'" % writeCommand)
        self._executeDBCmd(writeCommand)

    def update(self, callsheetRecord):
        for key in callsheetRecord.keys():
            updateCommand = "UPDATE callsheet SET %s='%s' WHERE uuid='%s'" %\
                            (key, callsheetRecord[key], callsheetRecord['uuid'])
            self._executeDBCmd(updateCommand)

    def getByUuid(self, uuid):
        loadCommand = "SELECT * FROM callsheet WHERE uuid = '%s'" % (uuid)
        record = self._fetchOneDBCmd(loadCommand)
        return record

    def getByName(self, name):
        loadCommand = "SELECT * FROM callsheet WHERE name = '%s'" % (name)
        record = self._fetchOneDBCmd(loadCommand)
        return record

class CallsheetRecord(dict):
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
        for keyname in record.keys():
            self[keyname] = record[keyname]

    def update(self, **kwargs):
        for (key, value) in kwargs.items():
            '''
            # This block won't work since we concatenated
            # the UUID to appease the NFC/Arduino byte limit
            if key == "uuid":
                #Validate UUID for v4 compliance
                uuid.UUID(value, version=4)
            '''
            self[key] = value
