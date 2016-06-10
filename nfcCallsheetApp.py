#! /usr/local/bin/python

__author__ = 'astetson'

import sys
sys.path.insert(0, './')
import shellScriptBase
import nfcCallsheetSerial

class CallsheetCmdlineApp(shellScriptBase.BaseShellScript):
    def registerArgs(self):
        self.parser.add_argument('-read',
            help='read NFC Tag, and pull associated record from DB',
            action='store_true',
            )

        self.parser.add_argument('-create',
            help='create a new NFC Tags/DB Record',
            action='store_true',
            )

        self.parser.add_argument('-update',
            help='Updating an existing DB record/tag with new data',
            action='store_true',
            )

        self.parser.add_argument('-assign',
            help='assign a new NFC tag to an existing record',
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
        elif self.args.assign:
            print("I'm in Assign Mode.")
            self.assignNewTagtoRecord()
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
        print("\n")
        return record


    def createTagAndRecord(self):
        args = self._queryUserForData()
        callsheetHandler = nfcCallsheetSerial.CallsheetHandler()
        callsheetHandler.createRecord(**args)

    def updateRecordFromTag(self):
        record = self.readTag()
        print("------")
        kwargs = self._queryUserForData()
        record.update(kwargs)
        callsheetHandler = nfcCallsheetSerial.CallsheetHandler()
        callsheetHandler.updateRecord(**record)
        print("Update complete")

    def assignNewTagtoRecord(self):
        print("Assigning new tag to existing record.  "\
              "How would you like to load the record?:")
        answer = input("  1 - Load record from existing tag\n"
              "  2 - Load record by name\n")
        if answer == "1":
            # Load record from tag
            record = self.readTag()
            ready = input("Hit enter when ready with new tag or type \"cancel\"")
            if ready.lower() == "cancel":
                return
            self._updateRecordWithSwipedTag(record)
        elif answer == "2":
            name = input("Enter name of desired record: ")
            callsheetHandler = nfcCallsheetSerial.CallsheetHandler()
            record = callsheetHandler.getRecordByName(name)
            print("Record for %s retrieved." % record['name'])
            self._updateRecordWithSwipedTag(record)
        else:
            print("I did not understand your input. Quitting.")

    def _updateRecordWithSwipedTag(self, record):
        print("Swipe new tag to associate with this record.")
        callsheetHandler = nfcCallsheetSerial.CallsheetHandler()
        newTagId = callsheetHandler.getIdFromTag()
        record.update(nfcTagId=newTagId)
        callsheetHandler.updateRecord(**record)
        callsheetHandler.writeTag(record['uuid'])

if __name__ == "__main__":
    app = CallsheetCmdlineApp()
    app.run()