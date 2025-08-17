# Internet Weather Clock

The files in this folder will add the Internet Clock app to the Fruit Jam OS application list, however the *clock.py* program (along with the *pydos* **lib** files and the **fonts** folder) will run on many CircuitPython boards. I have run it on display boards varying from the [LILYGO T-Watch-2020](https://lilygo.cc/products/t-watch-2020-v3?srsl), an ESP32 [Cheap Yellow Display](https://github.com/witnessmenow/ESP32-Cheap-Yellow-Display), Dot Clock displays like the [7" MaTouch Parallel TFT](https://www.makerfabs.com/esp32-s3-parallel-tft-with-touch-7-inch.html), [Adafruit TFT FeatherWings](https://www.adafruit.com/product/3651) and [S3 RGB Matrix Portal displays](https://www.adafruit.com/product/5778). To run on devices other than the Fruit Jam, you may need to add additional adafruit libraries and/or support files from [PyDOS](https://github.com/RetiredWizard/PyDOS).  

The clock is a digital clock displaying the day of the week, time, current temperature and weather forecast from weather.gov and weatherunderground.com.

By default the time and weather is provided for the Boston, MA area however the time zone and weather station locations can be customized using a launcher.conf.json file. The application will search the root folder for the launcher.conf.json file.

## Optional Parameters
  
**tz_offset** - Your local timezone offset.  
  
**brightness** - A brightness adjustment. A value greater than zero adjusts the brightness. The appropriate brightness for a particular screen may take some experimentation. If a keyboard is connected to the Fruit Jam the screen brightness can be adjusted using the +/- keys.  
  
-------------------------------------------  
**weatherunderground:stationID** - This is the station id of one [Weather Underground station](https://www.wunderground.com) which the program will attempt to retrieve the current temperature and feel's like temperature from. If the program can't retrieve a temperature from this source it will fall back to the weather.gov stations. You can use the [Wundermap](https://www.wunderground.com/wundermap) from the web site to find a station near you and by clicking on a station icon the Station ID will be displayed.  
  
**Important** *clock.py* does not use an official Weather Underground API to retrieve this data. The program use a hacky web scrape which is very likely to break and stop working at some point when Weather Underground updates their website. When this has happened in the past minor tweaks could be made to get things working again but it's possible this data may not be easily retrieved in the future, *clock.py* will fall back to using weather.gov stations in that case.  
  
**weatherunderground:stationLbl** - This is the label that will identify the location the Weather Underground temperatures was recorded from. The label should be limited to about 7 characters.  
    
-------------------------------------------  
**weathergov:lat**   
**weathergov:long** - The latitude and longitude of the location you want the clock to display a forcast for.  
  
**weathergov:stationID1** - This is the station ID of a [weather.gov](https://www.weather.gov) METAR observation station, If this station is reachable, the temperature from this location will be displayed. If this station is unreachable, the program will attempt to reach station #2 and then station #3.  
  
By using the mini map on the [weather.gov](https://www.weather.gov) site and clicking on and around your location you can identify nearby station IDs. There may be other options as well but the National Weather Service web sites are not the easiest to operate. I did locate a [web site](https://www.cnrfc.noaa.gov/metar.php) with a national listing of observation stations that you can use to identify the station IDs near you. In case that web site disappears, I've also included the [table](<https://github.com/RetiredWizard/Fruit-Jam-OS_MyApps/blob/main/Observation Station Identifiers.pdf>) in this repository.  
  
**weathergov:stationLbl1** -  This is the label associated with the first *weather.gov* observation station. This label should be limited to about 12 characters.    
  
**weathergov:stationID2** -  If station 1 is not reachable, this station will be used.  
**weathergov:stationLbl2**  
  
**weathergov:stationID3** - If station 1 and 2 are not reachable, this station wil be used.  
**weathergov:stationLbl3**  
  
------------------------------
## Example launcher.conf.json file  

```json
{
    "inetclock": {

        "tz_offset": -4,
        "brightness": 0,

        "weatherunderground": {
            "stationID": "KMABOSTO365",
            "stationLbl": "Boston"
        },

        "weathergov": {
            "lat": 42.3555,
            "long": -71.0565,
            "stationID1": "KBOS",
            "stationLbl1": "Logan",
            "stationID2": "KORH",
            "stationLbl2": "Worcester",
            "stationID3": "KOWD",
            "stationLbl3": "Norwood"
        }
    }
}
```
