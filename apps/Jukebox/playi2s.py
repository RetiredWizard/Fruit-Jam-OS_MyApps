# 
# Files that have been converted as follows have been tested
# Other formats may work.....
#

"""Audio Format                          : PCM
Format settings                          : Little / Signed
Codec ID                                 : 1
Duration                                 : 4 min 5 s
Bit rate mode                            : Constant
Bit rate                                 : 128 kb/s
Channel(s)                               : 1 channel
Sampling rate                            : 8 000 Hz
Bit depth                                : 16 bits
Stream size                              : 3.75 MiB (100%)
"""


import board
import time
from supervisor import runtime
try:
    import bitbangio
except:
    import busio as bitbangio
try:
    import adafruit_sdcard
except:
    try:
        import sdcardio as adafruit_sdcard
    except:
        pass

try:
    from pydos_ui import Pydos_ui
    try:
        from pydos_ui import input
    except:
        pass
    readkbd = Pydos_ui.read_keyboard
    sba = Pydos_ui.serial_bytes_available
except:
    try:
        from tdeck_repl import Pydos_ui
        from tdeck_repl import input
    except:
        from sys import stdin as Pydos_ui
        readkbd = Pydos_ui.read
        sba = lambda : runtime.serial_bytes_available

import digitalio
import storage
import audiocore
import audiobusio
import adafruit_tlv320
import adafruit_ticks
import os
import json
import adafruit_pathlib as pathlib

def Playi2s(passedIn=""):
    # optional configuration file for speaker/headphone setting
    launcher_config = {}
    if pathlib.Path("/launcher.conf.json").exists():
        with open("/launcher.conf.json", "r") as f:
            launcher_config = json.load(f)
    launcher_config = launcher_config.get("jukebox",{})

    # Check if TLV320 DAC is connected
    if "I2C" in dir(board):  
        i2c = board.I2C()
        for i in range(500): # try for 5 seconds
            if i2c.try_lock():
                break
            time.sleep(0.01)
        if 0x18 in i2c.scan():
            ltv320_present = True
        else:
            ltv320_present = False
        i2c.unlock()
    else:
        ltv320_present = False

    if ltv320_present:
        dac = adafruit_tlv320.TLV320DAC3100(i2c)
        dac.reset()

        # set sample rate & bit depth
        dac.configure_clocks(sample_rate=44100, bit_depth=16)

        if "ltv320" in launcher_config:
            if launcher_config["ltv320"].get("output") == "speaker":
                # use speaker
                dac.speaker_output = True
                dac.dac_volume = launcher_config["ltv320"].get("volume",5)  # dB
            else:
                # use headphones
                dac.headphone_output = True
                dac.dac_volume = launcher_config["ltv320"].get("volume",0)  # dB
        else:
            # default to headphones
            dac.headphone_output = True
            dac.dac_volume = 0  # dB

    audio_bus = None
    if 'I2S_BIT_CLOCK' in dir(board):
        audio_bus = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
    if 'I2S_BCLK' in dir(board):
        audio_bus = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)
    elif 'SPEAKER_SCK' in dir(board):
        audio_bus = audiobusio.I2SOut(board.SPEAKER_SCK, board.SPEAKER_WS, board.SPEAKER_DOUT)
    else:
        print('No I2S pins defined on the board')
        input("Press 'Enter' to close.\n\n")
        return

    # Check if the SD card is already mounted
    try:
        storage.getmount("/sd")
    except OSError:
        try:
            if "SD_SPI" in dir(board):
                spi = board.SD_SPI()
            elif "SD_SCK" in dir(board):
                spi = bitbangio.SPI(board.SD_SCK,board.SD_MOSI,board.SD_MISO)
            elif "SPI" in dir(board):
                spi = board.SPI()
            else:
                spi = bitbangio.SPI(board.SCK,board.MOSI,board.MISO)

            if "SD_CS" in dir(board):
                cs = digitalio.DigitalInOut(board.SD_CS)
            elif "SDCARD_CS" in dir(board):
                cs = digitalio.DigitalInOut(board.SDCARD_CS)
            else:
                cs = digitalio.DigitalInOut(board.CS)

            try:
                sd = adafruit_sdcard.SDCard(spi,cs)
            except:
                cs.deinit()
                if "SD_CS" in dir(board):
                    sd = adafruit_sdcard.SDCard(spi,board.SD_CS)
                elif "SDCARD_CS" in dir(board):
                    sd = adafruit_sdcard.SDCard(spi,board.SDCARD_CS)
                else:
                    sd = adafruit_sdcard.SDCard(spi,board.CS)

            vfs = storage.VfsFat(sd)
            storage.mount(vfs,'/sd')
            print('SD card mounted on /sd')
        except:
            try:
                cs.deinit()
            except:
                pass
            try:
                spi.deinit()
            except:
                pass

    if passedIn != "":
        flist = passedIn
    else:
        flist = ""
        
    while flist == "":
        flist = input("Enter filename: ")

    try:
        while Pydos_ui.virt_touched():
            pass
    except:
        pass

    print('Press "s" to skip, "q" to quit')
    if flist != passedIn:
        input('Press "Enter" to continue')

    files = flist.split(',')
    print(f"Files to play: {files}")

    singlewav = False
    if len(files) == 1:
        singlewav = True

    fileindx = 0
    wildindx = 0
    while True:
        fname = files[fileindx]
        print(f"Playing: {fname}")

        if fname[0] == '*':
            wildlist = [f for f in os.listdir('/sd') if f[-4:].upper() == ".WAV"]
            print(f"Found {wildlist} on the SD card.")
            if len(wildlist) == 0:
                if singlewav:
                    input(f"\n\n\nWAV files not found on the SD card (/sd).\n\nPress 'Enter' to close.\n\n")
                    audio_bus.deinit()
                    return

                fname = ""
                fileindx = (fileindx + 1) % len(files)
            else:
                fname = wildlist[wildindx]
                wildindx = (wildindx +1) % len(wildlist)
                if wildindx == 0:
                    fileindx = (fileindx + 1) % len(files)
        else:
            fileindx = (fileindx + 1) % len(files)

        print(f"Really Playing: {fname}")
        if fname[-4:].upper() == ".WAV":
            f = open('/sd/'+fname, "rb")
            wav = audiocore.WaveFile(f)

            if audio_bus is not None:
                print("Press S to skip, Q to quit")
                try:
                    audio_bus.play(wav)
                    while audio_bus.playing:
                        if sba():
                            cmnd = readkbd(1)
                            print(cmnd, end="", sep="")
                            if cmnd in "sS":
                                audio_bus.stop()
                                break
                            elif cmnd in "qQ":
                                audio_bus.stop()
                                audio_bus.deinit()
                                f.close()
                                return

                except:
                    pass
                    
            f.close()

        elif fname != "":
            print('Unknown filetype')

    audio_bus.deinit()
    return

if __name__ == "PyDOS":
    Playi2s(passedIn)
else:
    print("Enter 'playi2s.Playi2s('file1, file2, ...')' in the REPL or PEXEC command to run.")
