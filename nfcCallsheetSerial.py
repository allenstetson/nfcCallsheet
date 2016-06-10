#! /usr/local/bin/python

__author__ = 'astetson'

import sys
import uuid
import time
import serial
import signal
sys.path.insert(0, './')
import nfcCallsheetDB

def signal_handler(signal, frame):
    print('You pressed Ctrl+C. Shutting down.')
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

class CallsheetHandler(object):
    def __init__(self):
        self.callsheetDB = nfcCallsheetDB.CallsheetDatabase()
        print("Starting serial connection.")
        self.serialConnection = SerialConnection().connection

    def _monitorNfcForTagRead(self):
        '''Monitor the serial connection for tag information'''
        while True:
            currentLine = self.serialConnection.readline().decode('utf-8').lstrip().rstrip()
            if currentLine.startswith("nfc2py:"):
                print("--> Signal Received")
                (deviceId, transmissionType) = currentLine.split(":")[1:]
                if transmissionType == "01":
                    # Receiving NDEF Data
                    print("--> receiving ndef data")
                    break
                else:
                    print("Unexpected Transmission Type: '%s'" % transmissionType)
            else:
                #if the serial data isn't intended for us, I still like to print it:
                print(currentLine)
        ndefData = self._collectNdefData(self.serialConnection)
        return ndefData

    def _monitorNfcForTagWrite(self, uuid):
        # Monitor the serial connection for tag information
        while True:
            currentLine = self.serialConnection.readline().decode('utf-8').lstrip().rstrip()
            if currentLine.startswith("nfc2py:"):
                print("--> Signal Received")
                (deviceId, transmissionType) = currentLine.split(":")[1:]
                if transmissionType == "03":
                    time.sleep(0.1)
                    # Ready to write data
                    print("<-- writing ndef data")
                    print("  %s" % uuid)
                    #self.serialConnection.write(b"fish$")
                    self.serialConnection.write(("uuid:%s$" % uuid).encode('ascii'))
                elif transmissionType == "02":
                    print("DONE: You may remove the tag from the reader.")
                    break
                else:
                    print("Unexpected Transmission Type: '%s'" % transmissionType)
            else:
                #if the serial data isn't intended for us, I still like to print it:
                print(currentLine)

    def _collectNdefData(self, serialConnection):
        '''
        NDEF Information will be broadcasted over Serial in the following format:
          nfc2py:1001:01
          uid:0x04 0xBC 0xF9 0x0A 0x43 0x3D 0x80

          num_ndef_records:1
          payload:#name:Allen:
          nfc2py:1001:02
        '''
        ndefData = {}
        numNdefRecords = 0
        while True:
            currentLineBytes = serialConnection.readline()
            currentLine = currentLineBytes.decode('utf-8').lstrip().rstrip()
            # Listen for end signal:
            if currentLine.startswith("nfc2py:"):
                (deviceId, transmissionType) = currentLine.split(":")[1:]
                if transmissionType == "02":
                    # Finished with NDEF Data
                    print("--> Done receiving ndef data.")
                    break
            # Process incoming serial (ndef) data
            else:
                if not currentLine.strip():
                    #Skip over any blank lines
                    continue
                if not ":" in currentLine:
                    print("Unexpected data line received; no key/value delineation: %s"\
                          % currentLine)
                    continue
                if currentLine.split(":")[0] == "num_ndef_records":
                    numNdefRecords = int(currentLine.split(":")[1])
                elif currentLine.split(":")[0] == "payload":
                    try:
                      key = currentLine.split(":")[1]
                      val = currentLine.split(":")[2]
                    except IndexError:
                        print("WARNING: Malformed payload encountered; skipping: %s" % currentLine)
                        continue
                    if key.startswith("#"):
                        #Clean "#" from some ndef data
                        key = key[1:]
                    ndefData[key] = val
                else:
                    ndefData[currentLine.split(":")[0]] = currentLine.split(":")[1]
        return ndefData

    def createRecord(self, **kwargs):
        #Read tag for its ID
        tagId = self.getIdFromTag()
        #Create database record with info
        dbRecord = nfcCallsheetDB.CallsheetRecord()
        dbRecord['nfcTagId'] = tagId
        for key,value in kwargs.items():
            dbRecord[key] = value
        self.callsheetDB.create(dbRecord)
        #Update tag with db record uuid
        self.writeTag(dbRecord['uuid'])

    def getIdFromTag(self):
        ndefData = self.readTag()
        return ndefData['uid']

    def getRecordFromTag(self):
        ndefData = self.readTag()
        if not "uuid" in ndefData:
            raise ValueError("No UUID was found in this record.")
        callsheetRecord = self.callsheetDB.getByUuid(ndefData['uuid'])
        if not callsheetRecord:
            raise ValueError("No record with that uuid (%s) found." % uuid)
        return callsheetRecord

    def getRecordByName(self, name):
        callsheetRecord = self.callsheetDB.getByName(name)
        if not callsheetRecord:
            raise ValueError("No record with that name (%s) found." % name)
        return callsheetRecord

    def readTag(self):
        print("-> Listening for NDEF data.")
        # Signal for a tag Read
        startListening = b":read:"
        self.serialConnection.write(startListening)
        ndefData = self._monitorNfcForTagRead()
        print("-> NDEF data retrieved from %s with payload %s" %\
                (ndefData['uid'], ndefData.keys()))
        return ndefData

    def updateRecord(self, **kwargs):
        if not 'uuid' in kwargs:
            raise KeyError("A uuid must be provided when updating a record.")
        callsheetRecord = nfcCallsheetDB.CallsheetRecord()
        callsheetRecord.update(**kwargs)
        self.callsheetDB.update(callsheetRecord)

    def writeTag(self, uuid):
        # Signal for a tag Read
        writeSignal = b":new:"
        self.serialConnection.write(writeSignal)
        self._monitorNfcForTagWrite(uuid)

class SerialConnection:
    class __SerialConnection:
        def __init__(self):
            self.comPort = 2
            self.connection = self._startSerialConnection()

        def _startSerialConnection(self):
            try:
                serialConnection = serial.Serial(self.comPort, baudrate=9600)
            except serial.SerialException as e:
                msg = "No Serial connection found. Is the NFC Reader plugged in?\n"\
                      "Is it being used by another program?"
                raise type(e)(str(e) + msg).with_traceback(sys.exc_info()[2])
            time.sleep(2)
            return serialConnection

        def __del__(self):
            print("Closing serial connection.")
            self.connection.close()

    instance = None
    def __init__(self):
        if not SerialConnection.instance:
            SerialConnection.instance = SerialConnection.__SerialConnection()
    def __getattr__(self, name):
        return getattr(self.instance, name)