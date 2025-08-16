import supervisor
import playi2s

# This will play all WAV files on the SD card (/sd/ directory).
#
playi2s.Playi2s("*.WAV")
supervisor.reload()
