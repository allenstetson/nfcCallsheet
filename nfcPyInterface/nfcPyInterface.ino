#include <Wire.h>
#include <SPI.h>
#include <Adafruit_PN532.h>

// Default Adafruit device library, best for writing:
// shield with I2C, define pins connected to the IRQ and reset lines:
#define PN532_IRQ   (2)
#define PN532_RESET (3)  // Not connected by default on the NFC Shield
Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);

// Device Library with *much* more convenient read method:
#include <PN532_I2C.h>
#include <PN532.h>
#include <NfcAdapter.h>
PN532_I2C pn532_i2c(Wire);
NfcAdapter nfcReader = NfcAdapter(pn532_i2c);


int incomingByte = 0;
char serialBuffer[10];
void readNFC(void);
void writeNewRecord(void);
void formatNewTag(void);

String inputString = "";

void setup(void) {
  Serial.begin(9600);
  Serial.println("NFC Callsheet Python Interface launched. Awaiting command...");
  nfc.begin();
}

void loop(void) {
  if (Serial.available() > 0){
    incomingByte = Serial.read();
    //Serial.println(incomingByte, DEC);
    if(incomingByte == 58){
      Serial.readBytesUntil(58, serialBuffer, 10);
      if(strcmp(serialBuffer,"read")==0){
        Serial.println("Read.");
        delay(10);
        readNFC();
      } else if(strcmp(serialBuffer,"new")==0){
        Serial.println("New record.");
        delay(10);
        writeNewRecord();
      }
      memset(serialBuffer, 0, sizeof(serialBuffer));
    }
  }
}

void readNFC(void) {
  Serial.println("Ready to read. Place NFC tag on reader.");
  Serial.flush();
  delay(10);
  uint8_t success;
  uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  // Buffer to store the returned UID
  uint8_t uidLength;                        // Length of the UID (4 or 7 bytes depending on ISO14443A card type)

  // Wait for an NTAG203 card.  When one is found 'uid' will be populated with
  // the UID, and uidLength will indicate the size of the UUID (normally 7)
  success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength);
  if (success) 
  {
    // Display some basic information about the card
    Serial.println("Found an ISO14443A card");
    Serial.print("  UID Length: ");Serial.print(uidLength, DEC);Serial.println(" bytes");
    Serial.print("  UID Value: ");
    nfc.PrintHex(uid, uidLength);
    Serial.println("");
    Serial.flush();
    
    if (uidLength == 7)
    {
      uint8_t data[32];  
      // We probably have an NTAG2xx card (though it could be Ultralight as well)
      Serial.println("Seems to be an NTAG2xx tag (7 byte UID)");    
      Serial.println("nfc2py:1001:01"); // signal the start of a data transmission
      Serial.print("uid:");
      nfc.PrintHex(uid, uidLength);
      Serial.flush();

      NfcTag tag = nfcReader.read();
      if (tag.hasNdefMessage()) // every tag won't have a message
      {
        NdefMessage message = tag.getNdefMessage();
        // Report number of NDEF records:
        Serial.print("num_ndef_records:");
        Serial.println(message.getRecordCount());
        
        // cycle through the records, printing some info from each
        int recordCount = message.getRecordCount();
        for (int i = 0; i < recordCount; i++)
        {
          NdefRecord record = message.getRecord(i);
          int payloadLength = record.getPayloadLength();
          byte payload[payloadLength];
          record.getPayload(payload);
          // Print the payload to the serial buffer
          String payloadAsString = "";
          for (int c = 0; c < payloadLength; c++) {
            payloadAsString += (char)payload[c];
          }
          Serial.print("payload:");
          Serial.println(payloadAsString);
        } // for each record
      } // if has message
    } // UID length = 7
    else
    {
      Serial.println("This doesn't seem to be an NTAG203 tag (UUID length != 7 bytes)!");
    }
  }
  Serial.println("nfc2py:1001:02"); // signal the end of a data transmission
  Serial.flush();
}

void writeNewRecord(void){
  Serial.println("\nPlace a Mifare NDEF tag on the reader.");
  uint8_t success;
  uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  // Buffer to store the returned UID
  uint8_t uidLength;                        // Length of the UID (4 or 7 bytes depending on ISO14443A card type)
  uint8_t dataLength;
  bool loopMe;
  // 1.) Wait for an read tag
  success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength);
  // It seems we found a valid ISO14443A Tag!
  if (success) 
  {
    // 2.) Display some basic information about the card
    Serial.println("Found an ISO14443A card");
    Serial.print("  UID Length: ");Serial.print(uidLength, DEC);Serial.println(" bytes");
    Serial.print("  UID Value: ");
    nfc.PrintHex(uid, uidLength);
    Serial.println("");
    
    if (uidLength != 7)
    {
      Serial.println("This doesn't seem to be an NTAG203 tag (UUID length != 7 bytes)!");
    }
    else
    {
      uint8_t data[32];
      // We probably have an NTAG2xx card (though it could be Ultralight as well)
      Serial.println("Seems to be an NTAG2xx tag (7 byte UID)");    
      // 3.) Check if the NDEF Capability Container (CC) bits are already set
      // in OTP memory (page 3)
      memset(data, 0, 4);
      success = nfc.ntag2xx_ReadPage(3, data);
      if (!success)
      {
        Serial.println("Unable to read the Capability Container (page 3)");
        return;
      }
      else
      {
        // If the tag has already been formatted as NDEF, byte 0 should be:
        // Byte 0 = Magic Number (0xE1)
        // Byte 1 = NDEF Version (Should be 0x10)
        // Byte 2 = Data Area Size (value * 8 bytes)
        // Byte 3 = Read/Write Access (0x00 for full read and write)
        if (!((data[0] == 0xE1) && (data[1] == 0x10)))
        {
          Serial.println("This doesn't seem to be an NDEF formatted tag.");
          Serial.println("Page 3 should start with 0xE1 0x10.");
        }
        else
        {
          // 4.) Determine and display the data area size
          dataLength = data[2]*8;
          Serial.print("Tag is NDEF formatted. Data area size = ");
          Serial.print(dataLength);
          Serial.println(" bytes");
          
          // 5.) Erase the old data area
          Serial.print("Erasing previous data area ");
          for (uint8_t i = 4; i < (dataLength/4)+4; i++) 
          {
            memset(data, 0, 4);
            success = nfc.ntag2xx_WritePage(i, data);
            Serial.print(".");
            if (!success)
            {
              Serial.println(" ERROR!");
              return;
            }
          }
          Serial.println(" Done erasing.");

          // 6.) Send word to python lib that we are ready,
          // and need the message to write
          Serial.println("nfc2py:1001:03");
          delay(1000);
          // 7.) Now listen for a reply, write what we hear
          while (!Serial.available());
          while (Serial.available()){
          int numReceived = Serial.readBytesUntil(36, serialBuffer, 50);
          if (numReceived == 0){
            Serial.println("ERROR- NO INPUT TO WRITE WAS RECEIVED.");
          } else {
            Serial.print("Received # of Bytes: ");
            Serial.println(numReceived);
          }
          uint8_t ndefprefix = NDEF_URIPREFIX_URN_NFC;
          delay(10);
          Serial.print("wrote:");
          Serial.println(serialBuffer);
          success = nfc.ntag2xx_WriteNDEFURI(ndefprefix, serialBuffer, dataLength);
          if (success) 
          {
            Serial.println("Done writing.");
            Serial.println("nfc2py:1001:02");
            Serial.flush();
          }
          else 
          {
            Serial.println("ERROR! (URI length?)");
            Serial.flush();
          }
          }   
        } // CC contents NDEF record check
      } // CC container read check
    } // UUID length check
  } // Tag found
}



