import supervisor
import playimage
import adafruit_fruitjam.peripherals

# This will play all images (BMP, JPG, PNG, RLE, GIF) in the current directory
# or in the /sd/ directory if no images are found in the current directory.
#
# Note that GIF animations must have a width < = 320.

# The 20 at the end of the file list is the number of seconds to display each
# image. To change the display time, change the number after the comma.
adafruit_fruitjam.peripherals.request_display_config(320, 240)
playimage.playimage("*.*,20")
supervisor.reload()
