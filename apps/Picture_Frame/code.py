import supervisor
import playimage

# This will play all images (BMP, JPG, PNG, RLE, GIF) in the current directory
# or in the /sd/ directory if no images are found in the current directory.
# It will display each image for 20 seconds.
#
# Note that GIF animations must have a width < = 320.

playimage.playimage("*.*,20")
supervisor.reload()
