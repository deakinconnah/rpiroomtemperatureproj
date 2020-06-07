from flask import Flask, render_template, Response
import datetime
import Adafruit_DHT
import time
import RPi.GPIO as GPIO
import threading
from csv import writer, reader
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from os import path

#initalises temp/hum pin and sensor type
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4

#sets variables for GPIO LED pins
GPIO21 = 21
GPIO20 = 20
GPIO16 = 16

#setup for GPIO pins for LED interface
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO21, GPIO.OUT)
GPIO.setup(GPIO20, GPIO.OUT)
GPIO.setup(GPIO16, GPIO.OUT)

#sets which LEDs are to be lit
def GPIO21select():
    GPIO.output(GPIO21, True)
    GPIO.output(GPIO20, False)
    GPIO.output(GPIO16, False)
    
def GPIO20select():
    GPIO.output(GPIO21, False)
    GPIO.output(GPIO20, True)
    GPIO.output(GPIO16, False)

def GPIO16select():
    GPIO.output(GPIO21, False)
    GPIO.output(GPIO20, False)
    GPIO.output(GPIO16, True)
    
def GPIOOff():
    GPIO.output(GPIO21, False)
    GPIO.output(GPIO20, False)
    GPIO.output(GPIO16, False)

GPIOOff()    
#checks if siteData file exists and if not then create the files and add the headings to the data file
if not path.exists("siteData.csv"):
    with open("siteData.csv", 'wb') as csvfile:
        filewriter = writer(csvfile, delimiter=',', quotechar='|')
        filewriter.writerow(['Date', 'Temperature', 'Humidity'])
    
#initalises the global variables for the most up to date error free reading from the temp/hum sensor
latestHum, latestTemp = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)

#initalises the imgname as an empty variable to store the name of the graph to be displayed in the website
imgname = None

#checks if the value from sensor is valid
if latestHum is None or latestTemp is None:
    headers = ['Date', 'Temperature', 'Humidity']
    df = pd.read_csv('siteData.csv', names = headers)
    
    #if the value is not valid then the size of the length of the CSV is checked to make sure that there is enough data to read a successful previous value
    dflength = sum(1 for row in df['Date'])
    #if there is not enough data in the CSV then default values are assigned for temp and hum based off of average room temperatures and humidities
    if dflength < 2:
        latestHum = 50
        latestTemp = 20
    else:
        #if there is enough data than the last value of the CSV file is used as the new current temperature
        latestTemp = float(df['Temperature'][-1:])
        latestHum = float(df['Humidity'][-1:])

#getData function to fetch, verify and return the current humidity and temperature    
def getData():
    #attempts to read the data from the sensor
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    #loads the previous successful values as a global variable
    global latestTemp
    global latestHum
    #checks if current values are not None or 0
    if humidity is not None and temperature is not None and humidity is not 0.0 and temperature is not 0.0:
        #checks the current value against the previous value to ensure that the data is not too far out of range of the previous value
        if temperature < int(latestTemp * 1.25) and temperature > int(latestTemp * 0.75):
            #once checks are validated, the values can be updated as the latest successful values
            latestTemp = temperature
            latestHum = humidity
            return latestTemp, latestHum
        else:
            #if values are out of range, return previous successful values
            return latestTemp, latestHum
    else:
        #if values are None or 0, return previous successful values
        return latestTemp, latestHum

#function to change the LED colours when specific threshholds of temperature are met
def LEDWarning():
    temp, hum = getData()
    #checks temperature values and if they are between a certain value, then an specified LED will light up
    if temp > 28 or temp < 16:
        GPIO21select()
    elif temp > 25 or temp < 19:
        GPIO20select()
    else:
        GPIO16select()
    threading.Timer(300.0,functionControl).start()
    
#Function to add row to CSV file
def csvAdd():
    #opens siteData.csv
    with open("siteData.csv", "a+", newline ='') as write_obj:
        csv_writer = writer(write_obj)
        #retrieves data from getData function
        temp, hum = getData()
        #sets now to current time in datetime format
        now = datetime.datetime.now()
        #checks if now is not None and then adds values to CSV file
        if now is not None:
            timeString = now.strftime("%Y-%m-%d %H:%M:%S")
            itemToAdd = [timeString, temp, hum]
            csv_writer.writerow(itemToAdd)
        write_obj.close()
        threading.Timer(300.0,csvAdd).start()
    

def functionControl():
    LEDWarning()
    csvAdd()
    
functionControl()

    
#function to take values from csv file and create a new graph to be displayed on website
def createGraph():
    #reads data and adds them into a variable for later use
    headers = ['Date', 'Temperature', 'Humidity']
    df = pd.read_csv('siteData.csv', names = headers)
    
    #checks length of csv file so that approprate length graphs can be made, not taking data from months ago
    dflength = sum(1 for row in df['Date'])
    if dflength < 500:
        df = df[-(int(dflength/2)):]
    else:
        df = df[-250:]
        
    #graph is only created if there are more than 10 values
    if dflength > 10:
        #reorders the data so that a correct line graph can be create
        df['Date'] = df['Date'].map(lambda x: datetime.datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S"))
        #turns the temperature string values into a list of float values to be graphed
        lst = [float(i) for i in df['Temperature']]
        
        #creates graph
        x = df['Date']
        y = lst
        x, y = zip(*sorted(zip(*(x, y))))
        fig = plt.figure()
        plt.plot(x,y)
        fig.suptitle('Temperature over Time Graph')
        plt.xlabel('Date')
        plt.ylabel('Temperature')
    
        plt.gcf().autofmt_xdate()
        
    #creates file name as the date and time, then saves the image if the graph and removes the previous image
    global imgname
    if imgname is not None:
        if path.exists(imgname):
            os.remove(imgname)
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d %H:%M:%S")
    imgname = 'static/{0}.png'.format(date)
    plt.savefig(imgname)
    
#initalises webserver
app = Flask(__name__)
#function to be run whenever the homepage is accessed
@app.route('/')

def webserver():
    #collects data to be inserted into HTML file
    now = datetime.datetime.now()
    timeString = now.strftime("%Y-%m-%d %H:%M")
    global imgname
    temp, hum = getData()
    createGraph()
    templateData = {
        'title': 'Room Temperature and Humidity Monitor',
        'time': timeString,
        'temperature': temp,
        'humidity': hum,
        'imgname': imgname
        }
    #renders the index.html file with the collected data
    return render_template('index.html', **templateData)

#function that is run whenever the /dataset page is accessed
@app.route('/dataset')
def dataset():
    #turns the csv file into a table that can be interpereted by a web browser
    table = pd.read_csv("siteData.csv", header = 0)
    table = table.iloc[::-1]
    templateData = {
        'title': 'Data History',
        'data': table.to_html()
        }
    return render_template("dataset.html", **templateData)


if __name__ == '__main__':
    app.run(debug=True, port=80, host='0.0.0.0')
