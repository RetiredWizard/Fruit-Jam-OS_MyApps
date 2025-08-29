import supervisor
import playi2s

# This will play all WAV and MP3 files on the SD card (/sd/ directory).
#
playi2s.Playi2s("*.WAV")
supervisor.reload()
