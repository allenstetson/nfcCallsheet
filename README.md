# nfcCallsheet

This is a piece of code written to prove a technology solution at a former employer.  That employer used a digital "callsheet" for motion capture. That callsheet defined the expected markers, joints, and geometry for various elements that could be markered and captured on the mocap stage.  For each shoot, potentially dozens of times in a day, the callsheet would need to be cleared and set up for that particular shoot. This involved adding props to the callsheet by manually entering the serial number found on a sticker for each prop. Once entered, the callsheet software would pull the definition matching that serial number from a database and add it to the digital callsheet.

To save on time and reduce error, the idea came up that NFC stickers could be used. Once affixed to a prop, the NFC tag could be programmed with a unique ID.  Since the memory on an NFC tag is at a premium, any descriptive information about that prop could be stored in a separate database and retrieved once the NFC tag was scanned. The relevant data could be sent to the digital callsheet with a RabbitMQ message that the software would intercept, and would add the prop to the callsheet as a result.

The end result would be a nearly-instantaneous and error free addition of a prop to the callsheet.

Having had pretty extensive experience with Arduino in the past, I volunteered to prototype the technology, and wrote this code on an airplane while flying out to a mocap stage. I actually brought the Arduino with me on the airplane (I wonder if I could even get away with that nowadays?).  While this prototype does not issue RabbitMQ messages, the concept is pretty sound, and extending it to send a message would be trivial.  The prototype is written as a shell script with commandline arguments for different actions that the user might want (ie. programming an NFC tag, reading an NFC tag, updating an existing record, or assigning an existing record to a new NFC tag).  The real implementation would be written with GUI components and would be able to execute these tasks via buttons. Additionally, the discovery of the proper COM port would be coded into the production software, instead of relying on a hard-coded COM port of 2, as this prototype does.

## The Code
The code in this package is one of three things:
1. python code, custom
  * This makes up a majority of the softare in this package and contains the logic for the callsheet prototype.
2. arduino code, custom
  * While only one file, this does the heavy lifting of reading NFC tags, writing NFC tags, and interfacing with the python software over the serial COM port.
3. 3rd party software
  * Much of the complicated logic of determining species of scanned NFC tags, and programming the NFC reader is provided to the public by Adafruit with a BSD license, essentially freeware with no restrictions on usage. Why reinvent the wheel? I just included that in the package.

Let's break down the custom code.

### shellscript_base.py
Listed first because it doesn't _really_ belong to nfcCallsheet specifically. Much of the work that we did on the mocap stage was writing very quick shell scripts that did specific things. We often wrote these under extreme pressure in minutes or seconds as needed so as not to hold up the talent on stage. Having a framework, even simple, helped us to smash out scripts faster than otherwise. `shellscript_base.py` provided a very simple framework for us to use in order to supply commandline arguments to our script and to have a `run()` command that we could implement and have our tool just work. This is based on `argparse` and really doesn't do anything fancy other than provide some verbose printing logic, and debug levels (using an arbitrary integer defining what level to print; level 2 would print anything at 1 and 2, whereas level 6 would print anything from 1-6).

### database.py
A simple database implementation. Because this is a prototype, sqlite was used for the database. In production, this would be replaced by an actual relational database being hosted on the network.  This database utilizes a dictFactory so that queries are returned as dictionaries for ease of use.

### main.py
The entry point for this software, this leverages shellscript_base to create a commandline application presenting the user with a variety of flags that define actions that the software can perform.  When creating a record, the user is asked for entry on the commandline of information. In this implementation, the user is required to enter information in colon-separated key value pairs, with multiple pairs separated by commas. This is a pretty ugly burden for the user, but in the production implementation, a GUI would be provided for defining the data that gets stored ina record, associated with a prop.

### records.py
This houses the record object that gets stored in a database or on an NFC tag, and associated with a prop.  (generally, only the uuid of the record is stored on the tag, but there isn't a ton of information for these props, and it's probably possible to store the whole record on one; nonetheless, we leverage the database to store the record). Records can populate themselves based on incoming kwargs, on the contents of a scanned NFC tag, or from the database, and they can write themselves to an NFC tag or to the database.

### serial_connection.py
This module contains the handler that communicates over a serial COM port to an attached Arduino. The serial connection is a singleton which is important since COM ports can be fragile and easily overwhelmed. The singleton just ensures that, once established, the connection is utilized one request at a time, and not destroyed until the software exits.  A serial shorthand was invented to allow the Python object and the Arduino to communicate. Signals have certain prefixes that let each other know that we're talking to them, followed by a device ID, and then a command type (such as write or read), followed by the payload.  At times, this module's handler will wait for a signal indicating that a tag was scanned before it continues operating.

### nfcPyInterface/nfcPyInterface.ino
This Arduino code contains all of the logic to be uploaded to the Arduinon in order for it to work with the NFC reader/writer and to effectively communicate with the python app. It leverages the serial shorthand defined above.

## To Do
Were this to be a production script, a GUI would need to be written, RabbitMQ messages would need to be generated, and a proper database would need to be stood up and leveraged to make this stable enough for use. Generally, just a few days of work could make this a production reality.
