import socket
import struct
import math
from tkinter import Tk, Button, INSERT, END, Label, Text
from tkinter import scrolledtext


# ----  Global Variables ----
gWindow = Tk()
gTxtIP = Text(gWindow, height=1, width=40)
gTxtNewFreq = Text(gWindow, height=1, width=10)
gLblCurrFreq = Label(gWindow, height=1, width=10)
gTxtFeedback = scrolledtext.ScrolledText(gWindow)


def Get_Clicked():
    gTxtFeedback.delete('1.0',END)
    gTxtFeedback.insert(INSERT, 'Get Freq. button clicked\r\n')
    HOST = gTxtIP.get('1.0', END) #'192.168.1.27'    # The compressor's IP address
    HOST = HOST.strip()
    PORT = 502              # The port used by ModBus
    # Setup connection to get frequency
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(buildGetFreqQuery())
        data = s.recv(1024)
        breakdownReplyData(data)
        s.close()

def Set_Clicked():
    gTxtFeedback.delete('1.0',END)
    gTxtFeedback.insert(INSERT, 'Set Freq button clicked\r\n')
    HOST = gTxtIP.get('1.0', END) #'192.168.1.27'    # The compressor's IP address
    HOST = HOST.strip()
    PORT = 502              # The port used by ModBus
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(buildSetFreqCommand())
        data = s.recv(1024)
        s.close()

def buildSetFreqCommand():
    strNewFreq=gTxtNewFreq.get("1.0","end-1c")
    gTxtFeedback.insert(INSERT, '  New Freq Entered: ' + strNewFreq + '\r\n')
    fNewFreq = float(strNewFreq)
    fNewFreq = fNewFreq * 10.0
    fD, fI = math.modf(fNewFreq)
    iI = int(fI)
    gTxtFeedback.insert(INSERT, '  New Value: ' + str(iI) + '\r\n')
    bytes_val = iI.to_bytes(2, 'big')
    command = bytes([0x09, 0x99,  # Message ID
                     0x00, 0x00,  # Unused
                     0x00, 0x06,  # Message size in bytes
                     0x01,        # Slave Address
                     0x06,        # Function Code  6= Write a single Holding register
                     0x00,0x03,   # The register number
                     bytes_val[0],bytes_val[1]])  # The value
    
    gTxtFeedback.insert(INSERT, CommandByteArrayToReadableString(command))
    return command

def buildGetFreqQuery():
    query = bytes([0x09, 0x99,  # Message ID
                   0x00, 0x00,  # Unused
                   0x00, 0x06,  # Message size in bytes
                   0x01,        # Slave Address
                   0x04,        # Function Code  3= Read HOLDING registers, 4 read INPUT registers
                   0x00,0x24,   # The starting Register Number
                   0x00,0x01])  # How many to read
    gTxtFeedback.insert(INSERT, QueryByteArrayToReadableString(query))
    return query


def FloatToString(theNumber):
    fNumber = round(theNumber, 1)
    return str(fNumber)


def breakdownReplyData(rawData):
    gTxtFeedback.insert(INSERT, "Total Bytes Received: " + str(len(rawData)) + "\r\n")
    gTxtFeedback.insert(INSERT, "Bytes Received: \r\n")
    gTxtFeedback.insert(INSERT, ReplyByteArrayToReadableString(rawData) + "\r\n")


    wkrBytes = bytes([rawData[9], rawData[10]])
    iFreq = int.from_bytes(wkrBytes, byteorder='big')
    fFreq = float(iFreq) / 10.0
    gTxtFeedback.insert(INSERT, "Current Frequency: " + FloatToString(fFreq) + "\r\n")

def QueryByteArrayToReadableString(theArray):
    source = theArray.hex()
    sReturn = ''
    for x in range(0, len(source), 2):
        sReturn = sReturn + '0x' + source[x:x+2] + ' '
    sReturn = sReturn + '\r\n';
    sReturn = sReturn + '____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |    |    |    |____|__ How Many Registers\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |    |____|____________ Starting Register\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |______________________ Command number\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |___________________________ ID\r\n';
    sReturn = sReturn + '  |____|____|____|____|____|________________________________ Header\r\n';
    return sReturn


def ReplyByteArrayToReadableString(theArray):
    source = theArray.hex()
    sReturn = ''
    for x in range(0, len(source), 2):
        sReturn = sReturn + '0x' + source[x:x+2] + ' '
    sReturn = sReturn + '\r\n';
    sReturn = sReturn + '____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |    |    |____|__ Freq\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |    |____________ Length\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |_________________ Command number\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |______________________ ID\r\n';
    sReturn = sReturn + '  |____|____|____|____|____|___________________________ Header\r\n';
    return sReturn


def CommandByteArrayToReadableString(theArray):
    source = theArray.hex()
    sReturn = ''
    for x in range(0, len(source), 2):
        sReturn = sReturn + '0x' + source[x:x+2] + ' '
    sReturn = sReturn + '\r\n';
    sReturn = sReturn + '____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |    |    |    |____|__ Value to use\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |    |____|____________ Register to set\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |    |______________________ Command number\r\n';
    sReturn = sReturn + '  |    |    |    |    |    |    |___________________________ ID\r\n';
    sReturn = sReturn + '  |____|____|____|____|____|________________________________ Header\r\n';
    return sReturn


def main():
    gWindow.title("CPA3.0 Format ModbusTCP Inverter Frequency")
    gWindow.geometry('700x500')

    lblIP = Label(gWindow, text="IP Address:")
    lblIP.grid(column=0, row=0)

    gTxtIP.text = 'xxx.xxx.xxx.xxx'
    gTxtIP.grid(column=1, row=0)

    btnGet = Button(gWindow, text="Get Freq.", bg="LightBlue", command=Get_Clicked)
    btnGet.grid(column=0, row=1)
    gLblCurrFreq.grid(column=1, row=1)

    btnSet = Button(gWindow, text="Set Freq.", bg="LightBlue", command=Set_Clicked)
    btnSet.grid(column=0, row=2)
    gTxtNewFreq.grid(column=1, row=2)

    gTxtFeedback.grid(column=0, row=3, columnspan=3)

    gWindow.mainloop()


if __name__ == '__main__':
    main()
