#! /usr/local/bin/python

__author__ = 'astetson'

import os
import sys
sys.path.insert(0, '%s/Desktop/weta/NFC_Callsheet' % os.environ['USERPROFILE'])
import shellScriptBase
import nfcCallsheetSerial
import nfcCallsheetDB

class CallsheetCmdlineApp(shellScriptBase.BaseShellScript):
    def registerArgs(self):
        self.parser.add_argument('-read',
            help='start in "read" mode for reading NFC Tags',
            action='store_true',
            )

        self.parser.add_argument('-create',
            help='start in "create" mode for creating NFC Tags/Records',
            action='store_true',
            )

        self.parser.add_argument('-update',
            help='start in "update" mode for updating DB records',
            action='store_true',
            )

    def _queryUserForData(self):
        print("Enter comma-separated category:value to update (name:Xample, recordType:example): ")
        inputStr = input()
        pairs = inputStr.split(',')
        kwargs={}
        for pair in pairs:
            kwargs[pair.split(":")[0].strip()] = pair.split(":")[1].strip()
        return kwargs

    def run(self):
        super(CallsheetCmdlineApp, self).run()
        if self.args.create:
            print("I'm in Create Mode")
            self.createTagAndRecord()
        elif self.args.update:
            print("I'm in Update Mode.")
            self.updateRecordFromTag()
        else:
            print("I'm in Read Mode")
            self.readTag()

    def readTag(self):
        callsheetHandler = nfcCallsheetSerial.CallsheetHandler()
        record = callsheetHandler.getRecordFromTag()
        if not record:
            print("No record found that is associated with that tag.")
            return
        print("Record found:")
        print("---------- %s ----------" % record['name'])
        for key in record.keys():
            if key == 'name':
                continue
            print("%10s: %s" % (key, record[key]))
        return record


    def createTagAndRecord(self):
        args = self._queryUserForData()
        callsheetHandler = nfcCallsheetSerial.CallsheetHandler()
        callsheetHandler.createRecord(**args)

    def updateRecordFromTag(self):
        callsheetHandler = nfcCallsheetSerial.CallsheetHandler()
        record = callsheetHandler.getRecordFromTag()
        if not record:
            print("No record found that is associated with that tag.")
            return
        print("Record Retrieved:")
        for key in record.keys():
            print("%10s: %s" % (key, record[key]))
        print("------")
        kwargs = self._queryUserForData()
        record.update(kwargs)
        nfcCallsheetSerial.updateRecord(**record)
        print("Update complete")

    def assignNewTagtoRecord(self):
        ## GET RECORD EITHER BY TAG OR BY DB SEARCH
        ## READ TAG ID
        ## CREATE TAG
        ## UPDATE DB RECORD WITH NEW TAG ID
        pass

if __name__ == "__main__":
    app = CallsheetCmdlineApp()
    app.run()