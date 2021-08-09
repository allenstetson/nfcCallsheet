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
serial.py - Module containing logic that utilizes a serial COM port connection.

nfcCallsheet utilizes a serial connection over a COM port to an Arduino.
Through this connection, serial commands are sent to the Arduino, preparing it
to read from or write to an NFC tag. The arduino then utilizes the serial
connection in order to deliver records from those NFC tags after a scan.

"""
###############################################################################
# IMPORTS
###############################################################################
# stdlib imports
import sys
import uuid
import time
import signal

# extended imports
import serial

# local imports
from . import database


###############################################################################
# GLOBALS
###############################################################################
__all__ = [
    "signalHandler",
    "CallsheetHandler",
    "SerialConnection"
]
__author__ = 'astetson'


###############################################################################
# FUNCTIONS
###############################################################################
def signalHandler(signalCode, frame):  #pylint: disable=unused-argument
    """Register the Cntrl+C key combo as an exit for this software.

    This software uses while loops to wait for serial data from an attached
    Arduino. If ever the user wishes to exit this software while it is waiting,
    this key combo will be what is used.

    Args:
        signalCode (int): The signal number

        frame (frame): The current stack frame

    """
    print('You pressed Ctrl+C. Shutting down.')
    sys.exit(0)
# immediately register the function above as a valid signal handler:
signal.signal(signal.SIGINT, signalHandler)


###############################################################################
# CLASSES
###############################################################################
class CallsheetHandler(object):
    """Object with methods to interact with the callsheet and the NFC reader.

    """
    def __init__(self):
        #TODO: Remove all knowledge of a database from the handler and move
        #  that logic into the record object.
        self.callsheetDB = database.CallsheetDatabase()
        print("Starting serial connection.")
        self.serialConnection = SerialConnection().connection

    def _monitorNfcForTagRead(self):
        """Monitor the serial connection for tag information.

        The attached device could send potentially unwanted messages over the
        serial connection. This reads incoming serial data and detects if the
        incoming message begins with "nfc2py:", our clue that the incoming data
        is meant for us.  That data then goes on to define the type of message
        contained in the payload. For a read operation, the predefined
        transmission type is "01". If that is the case, the ndef data is then
        collected. Otherwise, we just keep listening.

        """
        while True:
            currentLine = self.serialConnection.readline().decode('utf-8')
            currentLine = currentLine.strip()
            if currentLine.startswith("nfc2py:"):
                print("--> Signal Received")
                (_, transmissionType) = currentLine.split(":")[1:]
                if transmissionType == "01":
                    # Receiving NDEF Data
                    print("--> receiving ndef data")
                    break
                else:
                    msg = "Unexpected Transmission Type: '{}'"
                    print(msg.format(transmissionType))
            else:
                #if the serial data isn't intended for us, I still like to print it:
                print(currentLine)
        ndefData = self._collectNdefData(self.serialConnection)
        return ndefData

    def _monitorNfcForTagWrite(self, recordUuid):
        """Monitors serial connection for a write command then writes a record.

        The attached device could send potentially unwanted messages over the
        serial connection. This reads incoming serial data and detects if the
        incoming message begins with "nfc2py:", our clue that the incoming data
        is meant for us.  That data then goes on to define the type of message
        contained in the payload. For a write operation, the predefined
        transmission type is "03". If that is the case, the uuid for the record
        is written to the NFC tag.  The serial connection continues to be
        monitored until a code of "02" arrives, indicating that the write is
        finished.

        Args:
            recordUuid (str): The ID of the tag

        """
        while True:
            currentLine = self.serialConnection.readline().decode('utf-8')
            currentLine = currentLine.strip()
            if currentLine.startswith("nfc2py:"):
                print("--> Signal Received")
                #TODO: Maybe useful to have a serial parsing object that
                #  extracts prefix, deviceID, and transmissionType in addition
                #  to payload...
                (_, transmissionType) = currentLine.split(":")[1:]
                if transmissionType == "03":
                    # The serial bus gets overwhelmed easily, let it flush:
                    time.sleep(0.1)
                    # Ready to write data
                    print("<-- writing ndef data")
                    print("  {}".format(recordUuid))
                    self.serialConnection.write(
                        ("uuid:{}$".format(recordUuid)).encode('ascii')
                        )
                elif transmissionType == "02":
                    print("DONE: You may remove the tag from the reader.")
                    break
                else:
                    msg = "Unexpected Transmission Type: '{}'"
                    print(msg.format(transmissionType))
            else:
                #if the serial data isn't intended for us, I still like to print it:
                print(currentLine)

    def _collectNdefData(self, serialConnection):
        """
        Monitors serial bus until information from an NFC tag is broadcast.

        The predefined code for an end of transmission is "02". When that code
        is received, we stop listening to the serial connection. Until then,
        we monitor incoming serial data that begins with "nfc2py:", our signal
        to begin storing information.

        NDEF Information will be broadcasted over Serial in this format:
          nfc2py:1001:01
          uid:0x04 0xBC 0xF9 0x0A 0x43 0x3D 0x80

          num_ndef_records:1
          payload:#name:Allen:
          nfc2py:1001:02

        That data is then returned.

        Args:
            serialConnection (SerialConnection): The serial connection to
                monitor.

        Returns:
            dict: The ndef data (data from the NFC tag) defining a record.

        """
        ndefData = {}
        numNdefRecords = 0
        while True:
            currentLineBytes = serialConnection.readline()
            currentLine = currentLineBytes.decode('utf-8').strip()
            # Listen for end signal:
            if currentLine.startswith("nfc2py:"):
                (_, transmissionType) = currentLine.split(":")[1:]
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
                    msg = ("Unexpected data line received; no "
                           "key/value delineation: {}")
                    print(msg.format(currentLine))
                    continue
                if currentLine.split(":")[0] == "num_ndef_records":
                    numNdefRecords = int(currentLine.split(":")[1])
                    msg = "Receiving {} records from the payload."
                    print(msg.format(numNdefRecords))
                elif currentLine.split(":")[0] == "payload":
                    try:
                        key = currentLine.split(":")[1]
                        val = currentLine.split(":")[2]
                    except IndexError:
                        msg = ("WARNING: Malformed payload encountered; "
                               "skipping: {}").format(currentLine)
                        print(msg)
                        continue
                    if key.startswith("#"):
                        #Clean "#" from some ndef data
                        key = key[1:]
                    ndefData[key] = val
                else:
                    ndefData[currentLine.split(":")[0]] = \
                    currentLine.split(":")[1]
        return ndefData

    def createRecord(self, **kwargs):
        """Creates a record in the database for an NFC tag that was scanned.

        Args:
            **kwargs: Arbitrary keyword args to write to the database.

        """
        #Read tag for its ID
        tagId = self.getIdFromTag()
        #Create database record with info
        dbRecord = database.CallsheetRecord()
        dbRecord['nfcTagId'] = tagId
        for key, value in kwargs.items():
            dbRecord[key] = value
        #TODO: Move this logic into the Record object:
        self.callsheetDB.create(dbRecord)
        #Update tag with db record uuid
        self.writeTag(dbRecord['uuid'])

    def getIdFromTag(self):
        """Reads an NFC tag to derive its ID.

        Returns:
            str: The ID of the tag that was scanned.

        """
        ndefData = self.readTag()
        return ndefData['uid']

    def getRecordFromTag(self):
        """Reads an NFC tag and pulls the associated record from the DB.

        Returns:
            dict: The record associated with the scanned NFC tag.

        """
        ndefData = self.readTag()
        if "uuid" not in ndefData:
            raise ValueError("No UUID was found in this record.")
        #TODO: Cast this as a CallsheetRecord before returning.
        #TODO: Even better, use a populate method on a record object.
        callsheetRecord = self.callsheetDB.getByUuid(ndefData['uuid'])
        if not callsheetRecord:
            msg = "No record with that uuid ({}) found."
            raise ValueError(msg.format(uuid))
        return callsheetRecord

    def getRecordByName(self, name):
        """Pulls the record associated with a given name from the DB.

        Returns:
            dict: The record associated with the provided name.

        """
        #TODO: Cast this as a CallsheetRecord before returning.
        #TODO: Even better, use a populate method on a record object.
        callsheetRecord = self.callsheetDB.getByName(name)
        if not callsheetRecord:
            msg = "No record with that name ({}) found.".format(name)
            raise ValueError(msg)
        return callsheetRecord

    def readTag(self):
        """Informs serial bus that we're waiting for NFC tag read, then wait.

        When a read signal is received, the data from that serial signal is
        then printed to the shell. In a production world, that would likely be
        broadcast to a RabbitMQ message queue to be picked up on and used by
        the callsheet software.

        Returns:
            dict: The ndef data (data from the UFC tag).

        """
        print("-> Listening for NDEF data.")
        # Signal for a tag Read
        startListening = b":read:"
        self.serialConnection.write(startListening)
        ndefData = self._monitorNfcForTagRead()
        msg = "-> NDEF data retrieved from {} with payload {}"
        msg = msg.format(ndefData['uid'], ndefData.keys())
        print(msg)
        return ndefData

    def updateRecord(self, **kwargs):
        """Update a record with provided attributes. One attr must be UUID.

        Uses the provided ID to pull a record from the database, then update
        that record with attributes provided.

        """
        if 'uuid' not in kwargs:
            raise KeyError("A uuid must be provided when updating a record.")
        callsheetRecord = database.CallsheetRecord()
        callsheetRecord.update(**kwargs)
        #TODO: Use an update method on a record object.
        self.callsheetDB.update(callsheetRecord)

    def writeTag(self, recordUuid):
        """Inform the serial connection that we desire to write a new tag.

        The serial connection (the attached Arduino) will switch into a write
        mode, awaiting the scan of an NFC tag. Once scanned, the UUID for the
        record is written to the tag.

        Args:
            recordUuid (str): The record ID to write to the tag.

        """
        # Signal for a tag Read
        writeSignal = b":new:"
        self.serialConnection.write(writeSignal)
        self._monitorNfcForTagWrite(recordUuid)


class SerialConnection:
    """A singleton serial connection to the attached Arduino.

    This defaults to COM port 2. Baud rate is 9600 to accommodate Arduino.

    Args:
        comPort (int): The COM port over which to establish a serial connection
            (optional).

    Raises:
        SerialException: if a connection could not be established.

    """
    # pylint: disable=invalid-name
    class __SerialConnection:
        """The singleton object to be issued once and only once."""
        def __init__(self, comPort=2):
            self.comPort = comPort
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
    def __init__(self, comPort=2):
        if not SerialConnection.instance:
            SerialConnection.instance = \
                SerialConnection.__SerialConnection(comPort=comPort)

    def __getattr__(self, name):
        """Allow access to the singleton's attributes."""
        return getattr(self.instance, name)
