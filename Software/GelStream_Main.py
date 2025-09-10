from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QDialog, QScroller, QWidget,QMessageBox, QFileDialog, QScrollArea, QLabel, QSizePolicy, QMainWindow, QMenu, QAction, qApp
from PyQt5.QtGui import QImage, QPixmap, QPalette, QPainter, QColor
from PyQt5.QtCore import Qt,QSize, QTimer

import time
import numpy as np
from PIL import Image,ImageDraw,ImageFont, ImageChops

import cv2

import sys
import os
import RPi.GPIO as gp
import picamera2
from picamera2.previews.qt import QGlPicamera2
from picamera2 import Picamera2, Preview
from libcamera import Transform, controls
import configparser
from datetime import datetime as dt
import datetime
#import matplotlib.pyplot as plt

class Ui(QMainWindow):
    COUNT_ENABLE = False
    
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('GelStream_v8.ui', self)
        # self.setFixedSize(QSize(1024,600))
        # self.setWindowFlags( Qt.CustomizeWindowHint )
        # self.setWindowFlags( Qt.WindowMaximizeButtonHint) 
        self.preview = False
        self.previewW = 676
        self.previewH = 507
        self.sensorFH = 3040
        self.sensorFW = 4056
        self.exposureScaler = 1 #ms
        self.LightMode=["None",""]
        
        

        self.captureDialog = QMessageBox()
        self.captureDialog.setMinimumWidth(500)
        self.captureDialog.setText("Capturing...")
        self.captureDialog.setStandardButtons = QMessageBox.Cancel
        self.timerBackcount = QTimer()
        self.timerBackcount.timeout.connect(self.print_time_left)

        self.saveFolder = ""
        
        
        #tune = Picamera2.load_tuning_file("imx477_noir.json")
        #self.picam2 = Picamera2(tuning=tune)
        
        self.picam2 = Picamera2()

        #self.cfg_preview = self.picam2.create_preview_configuration(display="main",buffer_count = 2, main={'format': 'XBGR8888','size':(4056,3040)},controls={"AeEnable":False,"AwbEnable":True,"ColourGains":[1,1]})
        self.cfg_preview = self.picam2.create_preview_configuration(display="main",buffer_count = 2, main={'format': 'XBGR8888','size':(4056,3040)},controls={"AeEnable":False,"AwbEnable":True})
        #self.cfg_preview = self.picam2.create_preview_configuration(display="main",controls={"AeEnable":False,"AwbEnable":False,"ColourGains":[2,2]})
        self.cfg_capture = self.picam2.create_still_configuration(buffer_count = 1,raw={'format':'SRGGB12_CSI2P','size':(4056,3040)}) #controls={"AeEnable":False,"AwbEnable":False,"ColourGains":[2,2]})
        
        #self.cfg_capture = self.picam2.create_still_configuration(raw={'format': 'SBGGR12', 'size': (4056,3040)})
        #picam2.create_still_configuration(raw={'format': mode['unpacked']}, sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']})
        print(self.cfg_preview)
        print(self.cfg_capture)
        
        self.picam2.options["quality"] = 95
        self.picam2.options["compress_level"] = 0
        
        self.picam2.set_controls({"AeEnable":False,"AwbEnable":False,"ColourGains": [2,2]})
        self.picam2.set_controls({"NoiseReductionMode":controls.draft.NoiseReductionModeEnum.Off})
        self.picam2.configure(self.cfg_preview)
        
        self.qpicamera2 = QGlPicamera2(self.picam2, width=self.sensorFW, height=self.sensorFH, keep_ar=True)
        
        self.qpicamera2.done_signal.connect(self.capture_done)
        self.qpicamera2.setBackgroundRole(QPalette.Base)
        #self.qpicamera2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # self.qpicamera2.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        
        # overlay1 = 64.*np.ones((507, 700, 4))
        # overlayFile= cv2.imread("overlay.png")
        # overlay1[:,:,:3] = overlayFile

        # self.qpicamera2.set_overlay(overlay1.astype('uint8'))

        #self.scrollPreview.setBackgroundRole(QPalette.Dark)
        self.scrollPreview.setWidget(self.qpicamera2)
        self.scrollPreview.setVisible(False)
        self.scrollPreview.setWidgetResizable(False)
        
        
        
        self.imageLabel = QLabel()
        pix = QPixmap(4056,3040)
        pix.fill(QColor(255,255,0,255))
        self.imageLabel.setBackgroundRole(QPalette.Base)
        self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imageLabel.setPixmap(pix)
        self.imageLabel.setScaledContents(True)

        
        self.scrollCapture.setBackgroundRole(QPalette.Dark)
        self.scrollCapture.setWidget(self.imageLabel)
        self.scrollCapture.setVisible(False)
        
        self.checkBoxCaptureFit.stateChanged.connect(self.updateCaptureFit)
                    
        self.buttonPreview.clicked.connect(self.handlePreview)
        self.buttonOpenFile.clicked.connect(self.viewFile)
        self.buttonFocusBottom.clicked.connect(self.handleLensUp)
        self.buttonFocusTop.clicked.connect(self.handleLensDown)
        self.buttonFocusBottomFast.clicked.connect(self.handleLensUpFast)
        self.buttonFocusTopFast.clicked.connect(self.handleLensDownFast)
        self.buttonSnap.clicked.connect(self.handleSnapshot)
        self.buttonShutdown.clicked.connect(self.handleQuit)
        
        
        #self.sliderExpo.valueChanged.connect(self.paramExpo)
        self.sliderExpoTime.valueChanged.connect(self.paramExpoTime)
        self.sliderBrightness.valueChanged.connect(self.paramBright)
        self.sliderContrast.valueChanged.connect(self.paramContrast)
        self.sliderGain.valueChanged.connect(self.paramGain)
        self.sliderSatur.valueChanged.connect(self.paramSatur)
        
        #self.checkBoxLR.stateChanged.connect(self.paramLRUD)
        #self.checkBoxUD.stateChanged.connect(self.paramLRUD)
        #self.checkBoxAe.stateChanged.connect(self.paramAe)
        self.checkBoxZoom.stateChanged.connect(self.handleZoom)
        self.groupEpi.toggled.connect(self.handleEpi)
        self.groupTrans.toggled.connect(self.handleTrans)
        self.buttonsEpi.buttonToggled[QtWidgets.QAbstractButton,bool].connect(self.updateEpiLights)
        self.buttonsTrans.buttonToggled[QtWidgets.QAbstractButton,bool].connect(self.updateTransLights)
        
        self.exposureScaleSelect.activated[str].connect(self.updateExposureScale)
	
        gp.setmode(gp.BCM)
        self.pins74238 = ["","","",""] # A0, A1, A2, DATA (ON/OFF)
        # 74238 as 1-to-8 Demux with 3 pins address control, 1 pin data input
        self.pins74238[0] = 22 # pin 15 S0
        self.pins74238[1] = 27 # pin 13 S1
        self.pins74238[2] = 17 # pin 11 S2
        self.pins74238[3] = 4  # pin  7 DATA
        
        
        self.enableDEMUXpins()
        gp.output(self.pins74238[:],0)
        self.DEMUXADDRESS = 0
        self.motorStepPin = 6 #5
        self.motorDirPin = 26 #6
        self.motorEnablePin = 5 #26
        
        self.buzzerPin = 25
        
        gp.setup(self.motorStepPin,gp.OUT)
        gp.setup(self.motorDirPin,gp.OUT)
        gp.setup(self.motorEnablePin,gp.OUT)
        gp.setup(self.buzzerPin,gp.OUT)
        
        gp.output(self.motorEnablePin,1)
        
        #self.settings = configparser.ConfigParser()
        
        self.beep_long()

        QScroller.grabGesture(self.scrollPreview,QScroller.TouchGesture)
        QScroller.grabGesture(self.scrollCapture,QScroller.TouchGesture)
        self.show()
        
        
            
        
        for i in range(1,10):
            self.toolBox.setItemEnabled(i,False)
        

    def handlePreview(self):
        if self.preview:
            self.scrollPreview.setVisible(False)
            self.buttonOpenFile.setEnabled(True)
            self.picam2.stop()
            self.buttonPreview.setText("Start Camera")
            self.buttonShutdown.setEnabled(True)
            self.buttonFocusBottom.setEnabled(False)
            self.buttonFocusTop.setEnabled(False)
            self.buttonSnap.setEnabled(False)
            for i in range(1,10): #Disable pages except Preview and Turn-off
                self.toolBox.setItemEnabled(i,False)
            self.toolBox.setItemEnabled(self.toolBox.indexOf(self.pageTurnoff),True)
            gp.output(self.pins74238[:],0)
        else:
            #self.loadConfig()
            self.picam2.start()
            self.buttonPreview.setText("Stop Camera")
            self.buttonSnap.setEnabled(True)
            self.buttonOpenFile.setEnabled(False)
            self.checkBoxCaptureFit.setEnabled(False)
            self.buttonFocusBottom.setEnabled(True)
            self.buttonFocusTop.setEnabled(True)
            self.toolBox.setItemEnabled(self.toolBox.indexOf(self.pageTurnoff),False)
            self.scrollPreview.setVisible(True)
            self.scrollCapture.setVisible(False)

            for i in range(1,10): #Enable pages
                self.toolBox.setItemEnabled(i,True)
               

        self.preview = not self.preview
    
    
    def viewFile(self):
        options = QFileDialog.Options()
        # fileName = QFileDialog.getOpenFileName(self, "Open File", QDir.currentPath())
        fileName, _ = QFileDialog.getOpenFileName(self, 'QFileDialog.getOpenFileName()', '',
                                                  'Images (*.png *.jpeg *.jpg *.bmp *.gif)', options=options)
        if fileName:
            image = QImage(fileName)
            
            if image.isNull():
                QMessageBox.information(self, "Gel-Stream", "Cannot load %s." % fileName)
                return

            pix =QPixmap.fromImage(image)
            self.imageLabel.setPixmap(pix)
            self.scrollCapture.setVisible(True)
            self.checkBoxCaptureFit.setEnabled(True)
    


    def updateCaptureFit(self,flag):
        state = flag
        if state:
            self.imageLabel.resize(self.scrollCapture.width(),int(self.sensorFH*self.scrollCapture.width()/self.sensorFW))
        else:
            self.imageLabel.resize(self.sensorFW,self.sensorFH)
           
    
    def handleLensUp(self):
        gp.output(self.motorDirPin, 1)
        self.moveStepper(32)
        print("Lens Up")
        
    def handleLensUpFast(self):
        gp.output(self.motorDirPin, 1)
        self.moveStepper(320)
        print("Lens Up Fast")
        
        
    def handleLensDown(self):
        gp.output(self.motorDirPin, 0)
        self.moveStepper(32)   
        print("Lens Down")
        
    def handleLensDownFast(self):
        gp.output(self.motorDirPin, 0)
        self.moveStepper(320)   
        print("Lens Down Fast")
        
    # def paramLRUD(self):
        # if self.checkBoxLR.isChecked():
            # flagLR=1
        # else:
            # flagLR=0
                
        # if self.checkBoxUD.isChecked():
            # flagUD=1
        # else:
            # flagUD=0
        # if self.preview:
            # self.picam2.stop()
        # self.cfg_preview = self.picam2.create_preview_configuration(display="main",main={'format': 'XBGR8888','size':(4056,3040)},controls={"AeEnable":False,"AwbEnable":False,"ColourGains":[2,2]},transform=Transform(vflip=flagUD,hflip=flagLR))
        # self.cfg_capture = self.picam2.create_still_configuration(raw=self.picam2.sensor_modes[3],transform=Transform(vflip=flagUD,hflip=flagLR))
        # self.picam2.configure(self.cfg_preview)
        # #self.cfg_preview = self.picam2.create_preview_configuration(transform=Transform(vflip=flagUD,hflip=flagLR))
        # #self.cfg_capture = self.picam2.create_still_configuration(transform=Transform(vflip=flagUD,hflip=flagLR))
        # if self.preview:
            # self.picam2.start()
        
        
    def handleSnapshot(self):
        if self.preview:
            response = QFileDialog.getExistingDirectory(self,caption="Select Folder:")
            if response !="":
                self.saveFolder = response
                print(response)
                
                self.acqtime = time.localtime()
                
                #fname = 'GI_{}_{}_{}_{}_{}_{}'.format(tt[0],tt[1],tt[2],tt[3],tt[4],tt[5])
                for i in range(10): 
                    self.toolBox.setItemEnabled(i,False)
                self.buttonSnap.setEnabled(False)
                self.channelChoice.setEnabled(False)
                self.statusbar.showMessage("Saving Image File...")
                
                self.captureDialog.show()
                
                
                #self.picam2.switch_mode(self.cfg_capture)
                
                #job=self.picam2.capture_array(name="raw",signal_function = self.qpicamera2.signal_done)
                print("starting job")

                if self.COUNT_ENABLE:
                    self.timerBackcount.start(1000)
                
                
                job = self.picam2.switch_mode_and_capture_array( self.cfg_capture,signal_function = self.qpicamera2.signal_done)
                self.cycle_on = time.time()
                
                
                
                
            
    
    def capture_done(self,job):
        
        print("Inside capture_done()")
        self.statusbar.showMessage("Saving Image File...Done")
        data = self.picam2.wait(job)
        
        self.timerBackcount.stop()
        
        print(data.shape)
        tt = self.acqtime
        fname = 'GI_{}_{}_{}_{}_{}_{}_'.format(tt[0],tt[1],tt[2],tt[3],tt[4],tt[5])
        filter_option = self.channelChoice.currentText()
        print(filter_option)
        if (filter_option=="BLUE"):
            img = Image.fromarray(data[:,:,2],'P')
        elif (filter_option=="GREEN"):
            img = Image.fromarray(data[:,:,1],'P')
        elif (filter_option=="RED"):
            img = Image.fromarray(data[:,:,0],'P')
        inverted = False  
        if self.checkBoxInvertedSave.isChecked():
            img = ImageChops.invert(img)
            print("Donnnne")
            inverted = True
      
        #img=img.rotate(90,expand=True)    
        self.put_parameters(img,(65,65),50,inverted)
        img.save(self.saveFolder + "/" + fname+ str(filter_option) + ".png")
        
        
        for i in range(10):
            self.toolBox.setItemEnabled(i,True)
        self.buttonSnap.setEnabled(True)
        self.channelChoice.setEnabled(True)
        self.beep_long()
        self.captureDialog.close()
        
        QMessageBox.information(self,"GelStream","Capture Complete!")
        
        
    def put_parameters(self,img,position,font_size,inverted_flag):
        if inverted_flag:
            bwcolor=0
        else:
            bwcolor=255
                
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", font_size)
        exposure =  str(self.sliderExpoTime.value())
        exp_units =self.exposureScaleSelect.currentText()
        gain= str(self.sliderGain.value())
        brightness = str(self.sliderBrightness.value()/8.)
        contrast= str(self.sliderContrast.value())
        saturation= str(self.sliderSatur.value()/8.)
        I1 = ImageDraw.Draw(img)
        x0 = position[0]
        y0 = position[1]
        I1.text((x0,y0+0*font_size), "Gel-Stream v1.0",(bwcolor),font=font)
        I1.text((x0,y0+1*font_size), "Channel: " + self.channelChoice.currentText(),(bwcolor),font=font)
        I1.text((x0,y0+2*font_size ), "Exposure: " + exposure + " " + exp_units,(bwcolor),font=font)
        I1.text((x0,y0+3*font_size), "Gain: " + gain,(bwcolor),font=font)
        I1.text((x0,y0+4*font_size), "Brightness: " + brightness,(bwcolor),font=font)
        I1.text((x0,y0+5*font_size), "Contrast: " + contrast,(bwcolor),font=font)
        I1.text((x0,y0+6*font_size), "Saturation: " + saturation,(bwcolor),font=font)
        I1.text((x0,y0+7*font_size), "Illumination Mode: " + self.LightMode[0] + self.LightMode[1],(bwcolor),font=font)
        I1.text((x0,y0+8*font_size), "Emission Filter: " + self.emissionFilter.currentText(),(bwcolor),font=font)
        
        
    def moveStepper(self, steps):
        gp.output(self.motorEnablePin,0)
        self.beep_short()
        for i in range(steps):
            time.sleep(0.001)
            gp.output(self.motorStepPin,0)
            time.sleep(0.001)
            gp.output(self.motorStepPin,1)
        
           
        # send pulses to "motorStepPin" pin
        
        gp.output(self.motorEnablePin,1)
            
    
    """   
    def paramExpo(self,val):
        self.picam2.controls.ExposureValue=val
        self.valExpo.setText(str(val))
        self.statusbar.showMessage("Setting exposure to " + str(val))
    """    
    def paramExpoTime(self,val):
        self.picam2.controls.ExposureTime = int(val*self.exposureScaler)
        self.updateExposureScale(self.exposureScaleSelect.currentText())
        self.valExpoTime.setText(str(val) + " " + self.exposureScaleSelect.currentText())
        self.statusbar.showMessage("Setting exposure time to " + str(val) + " " + self.exposureScaleSelect.currentText())
    
    def updateExposureScale(self,text):
        if text =="minutes":
            self.exposureScaler = 1E06*60
            self.sliderExpoTime.setMaximum(10)
            self.COUNT_START = dt(1900,1,1,0,int(self.sliderExpoTime.value()),0)
            self.COUNT_ENABLE = True
        
        elif text =="seconds":
            self.exposureScaler = 1E06
            self.sliderExpoTime.setMaximum(59)
            if self.sliderExpoTime.value()<60:
                self.COUNT_START = dt(1900,1,1,0,0,int(self.sliderExpoTime.value()))
                self.COUNT_ENABLE = True
        
        elif text =="ms":
            self.exposureScaler = 1E03
            self.sliderExpoTime.setMaximum(1000)
            self.COUNT_ENABLE = False
        
        elif text=="microseconds":
            self.exposureScaler = 1
            self.sliderExpoTime.setMaximum(5000)
            self.COUNT_ENABLE = False
            
    def print_time_left(self):
        
        self.captureDialog.setText("Time left: " + str(dt.strftime( self.COUNT_START + datetime.timedelta(seconds = -round(time.time()-self.cycle_on)+1),"%M:%S")))
        self.captureDialog.repaint()
           
    def paramBright(self,val):
        self.picam2.controls.Brightness=val/8.
        self.valBright.setText(str(val/8.))
        self.statusbar.showMessage("Setting brightness to " + str(val/8.))
    
    def paramContrast(self,val):
        self.picam2.controls.Contrast=val
        self.valContrast.setText(str(val))
        self.statusbar.showMessage("Setting contrast to " + str(val))
    def paramGain(self,val):
        self.picam2.controls.AnalogueGain=val
        self.valGain.setText(str(val))
        self.statusbar.showMessage("Setting Gain to " + str(val))
    def paramSatur(self,val):
        self.picam2.controls.Saturation = val/8.
        self.valSatur.setText(str(val/8.))
        self.statusbar.showMessage("Setting Saturation to " + str(val/8.))
        
    def paramAe(self):
        flag = self.checkBoxAe.isChecked()
        self.picam2.controls.AeEnable = flag
        if flag:
            self.statusbar.showMessage("AutoExposure Enabled.")
        else:
            self.statusbar.showMessage("AutoExposure Disabled.")
        
        
            
    def handleZoom(self):
        flag = self.checkBoxZoom.isChecked()
        print(flag)
        if flag:
            self.qpicamera2.setFixedWidth(self.scrollPreview.width()-10)
            self.qpicamera2.setFixedHeight(self.scrollPreview.height()-10)
            print(self.scrollPreview.horizontalScrollBar().pageStep())
            
        else:
            
            self.qpicamera2.setFixedWidth(self.sensorFW)
            self.qpicamera2.setFixedHeight(self.sensorFH)
            
            self.scrollPreview.verticalScrollBar().setValue(3040/2)
            self.scrollPreview.horizontalScrollBar().setValue(2028-400)
            #print("VertScroll:",self.scrollPreview.verticalScrollBar().value())

    def handleEpi(self):
        if self.groupEpi.isChecked():
            self.LightMode=['Epi-',""]
            self.groupTrans.setChecked(False)
            self.updateDEMUXaddress(self.DEMUXADDRESS)
            self.enableDEMUXoutput(True)
            
        else:
            self.LightMode=['Trans-',""]
            self.enableDEMUXoutput(False)
            
    def handleTrans(self):
        if self.groupTrans.isChecked():
            self.LightMode=['Trans-',""] 
            self.groupEpi.setChecked(False)
            self.updateDEMUXaddress(self.DEMUXADDRESS)
            self.enableDEMUXoutput(True)

        else:
            self.LightMode=['Epi-',""]
            self.enableDEMUXoutput(False)
            
    def updateEpiLights(self,opt,checked):
        if not checked:
            return
        self.statusbar.showMessage("Epi Mode: "+ opt.text())
        self.LightMode[1]=opt.text()
        if opt.text()=="BLUE":
            self.DEMUXADDRESS = 0
            
        elif opt.text()=="RED":
            self.DEMUXADDRESS = 1  
        elif opt.text()=="GREEN":
            self.DEMUXADDRESS = 2            
              
        self.updateDEMUXaddress(self.DEMUXADDRESS)
        self.enableDEMUXoutput(True)
        
    def updateTransLights(self,opt,checked):
        if not checked:
            return
        self.statusbar.showMessage("Trans Mode: "+ opt.text())
        self.LightMode[1]=opt.text()
        if opt.text()=="BLUE":
            self.DEMUXADDRESS = 3
        elif opt.text()=="RED":
            self.DEMUXADDRESS = 4  
        elif opt.text()=="GREEN":
            self.DEMUXADDRESS = 5
        elif opt.text()=="WHITE":
            self.DEMUXADDRESS = 6
              
        self.updateDEMUXaddress(self.DEMUXADDRESS)
        self.enableDEMUXoutput(True)
        
    def enableDEMUXpins(self):
        
        print("Setting GPIOs as outputs: ")
        for pin in self.pins74238:
            gp.setup(pin,gp.OUT)
        
            
    def updateDEMUXaddress(self,addr):
        print("DEMUXaddress: "+ str(addr))
        # dec to binary conversion
        digit = -1;
        for pin in self.pins74238[:-1]:
            try:
                gp.output(pin,int(bin(addr)[digit]))
            except:
                gp.output(pin,0)
            digit -=1
        
        
    def enableDEMUXoutput(self, state):
        if state:
            gp.output(self.pins74238[3], 1)
            print("LIGHTS ON")
        else:
            gp.output(self.pins74238[3], 0)
            print("LIGHTS OFF")
            
    def beep_short(self):
        gp.output(self.buzzerPin,1)
        time.sleep(.05)
        gp.output(self.buzzerPin,0)
        
    def beep_long(self):
        gp.output(self.buzzerPin,1)
        time.sleep(.25)
        gp.output(self.buzzerPin,0)
        
    def updateDial(self,dial,str_value):
        dial.setValue(int(str_value))
        dial.sliderPosition(int(str_value))
        dial.update()
        dial.repaint()
        

                
    def handleQuit(self):
        self.enableDEMUXoutput(False)
        gp.output(self.motorEnablePin,1)
        self.picam2.stop()
        time.sleep(1)
        
        os.system("sudo shutdown -h now")

                
    # def loadConfig(self):
        # path = os.path.dirname(os.path.realpath(__file__))
        # fname = '/'.join([path, "GelImager.cfg"])
        # try:
            
            # with open(fname,'r') as configfile:
            
                # self.settings.read(configfile)
                
                # print(self.settings.sections())
                # print(self.settings['Camera Settings']['exposure'])
                
                # self.updateDial(self.sliderExpoTime, self.settings['Camera Settings']['exposure'])
                # print("Exposure Set...")
                # #self.exposureScaleSelect.currentText() = self.settings['Camera Settings']['ExposureUnits'] 
                # self.sliderGain.setValue(int(self.settings['Camera Settings']['gain']))
                # self.sliderBrightness.setValue(int(self.settings['Camera Settings']['brightness']))
                # self.sliderContrast.setValue(int(self.settings['Camera Settings']['contrast']))
                # self.sliderSatur.setValue(int(self.settings['Camera Settings']['saturation']))
                # print("Configuration Loaded...END")
                
                    
        # except:#very first run
            # print("Generating Config File...")
            # with open(fname,'w') as configfile:
                # self.settings["Camera Settings"]={}
                # self.settings["Camera Settings"]["exposure"]= "20" 
                # self.settings["Camera Settings"]["exposureUnits"]= "ms"
                # self.settings["Camera Settings"]["gain"]= "1" 
                # self.settings["Camera Settings"]["brightness"]= "0" 
                # self.settings["Camera Settings"]["contrast"]= "1" 
                # self.settings["Camera Settings"]["saturation"]= "1" 
                # self.settings.write(configfile)
        


app = QtWidgets.QApplication(sys.argv)
window = Ui()


sys.exit(app.exec_())
#window.picam2.stop()

"""
['Buffer', 'DrawChildren', 'DrawWindowBackground', 'IgnoreMask',
 'PaintDeviceMetric', 'PdmDepth', 'PdmDevicePixelRatio',
 'PdmDevicePixelRatioScaled', 'PdmDpiX', 'PdmDpiY', 'PdmHeight', 
 'PdmHeightMM', 'PdmNumColors', 'PdmPhysicalDpiX', 'PdmPhysicalDpiY', 
 'PdmWidth', 'PdmWidthMM', 'RenderFlag', 'RenderFlags', 
 '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__', 
 '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', 
 '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 
 'acceptDrops', 'accessibleDescription', 'accessibleName', 'actionEvent', 'actions', 'activateWindow', 
 'addAction', 'addActions', 'adjustSize', 'autoFillBackground', 'backgroundRole', 'baseSize', 'bg_colour',
 'blockSignals', 'buffers', 'camera_notifier', 'changeEvent', 'childAt', 'childEvent', 'children', 'childrenRect',
 'childrenRegion', 'cleanup', 'clearFocus', 'clearMask', 'close', 'closeEvent', 'colorCount', 'connectNotify',
 'contentsMargins', 'contentsRect', 'contextMenuEvent', 'contextMenuPolicy', 
 'count', 'create', 'createWindowContainer', 'create_surface', 'current_request', 'cursor',
 'customContextMenuRequested', 'customEvent', 'deleteLater', 'depth', 'destroy', 'destroyed', 
 'devType', 'devicePixelRatio', 'devicePixelRatioF', 'devicePixelRatioFScale', 'disconnect', 'disconnectNotify', 
 'done_signal', 'dragEnterEvent', 'dragLeaveEvent', 'dragMoveEvent', 'dropEvent',
 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'effectiveWinId', 'egl', 'ensurePolished',
 'enterEvent', 'event', 'eventFilter', 'find', 'findChild', 'findChildren', 'focusInEvent', 'focusNextChild', 
 'focusNextPrevChild', 'focusOutEvent', 'focusPolicy', 'focusPreviousChild', 'focusProxy', 'focusWidget', 'font',
 'fontInfo', 'fontMetrics', 'foregroundRole', 'frameGeometry', 'frameSize', 'geometry', 'getContentsMargins', 'grab',
 'grabGesture', 'grabKeyboard', 'grabMouse', 'grabShortcut', 'graphicsEffect', 'graphicsProxyWidget', 'handle_requests', 
 'hasFocus', 'hasHeightForWidth', 'hasMouseTracking', 'hasTabletTracking', 'height', 'heightForWidth', 'heightMM', 'hide',
 'hideEvent', 'inherits', 'initPainter', 'init_gl', 'inputMethodEvent', 'inputMethodHints', 'inputMethodQuery', 'insertAction', 
 'insertActions', 'installEventFilter', 'isActiveWindow', 'isAncestorOf', 'isEnabled', 'isEnabledTo', 'isFullScreen', 'isHidden', 
 'isLeftToRight', 'isMaximized', 'isMinimized', 'isModal', 'isRightToLeft', 'isSignalConnected', 'isVisible', 'isVisibleTo',
 'isWidgetType', 'isWindow', 'isWindowModified', 'isWindowType', 'keep_ar', 'keyPressEvent', 'keyReleaseEvent', 'keyboardGrabber', 
 'killTimer', 'layout', 'layoutDirection', 'leaveEvent', 'locale', 'lock', 'logicalDpiX', 'logicalDpiY', 'lower', 'mapFrom', 
 'mapFromGlobal', 'mapFromParent', 'mapTo', 'mapToGlobal', 'mapToParent', 'mask', 'maximumHeight', 'maximumSize', 'maximumWidth', 
 'metaObject', 'metric', 'minimumHeight', 'minimumSize', 'minimumSizeHint', 'minimumWidth', 'mouseDoubleClickEvent', 'mouseGrabber', 
 'mouseMoveEvent', 'mousePressEvent', 'mouseReleaseEvent', 'move', 'moveEvent', 'moveToThread', 'nativeEvent', 'nativeParentWidget',
 'nextInFocusChain', 'normalGeometry', 'objectName', 'objectNameChanged', 'overlay_present', 'overlay_texture', 'overrideWindowFlags', 
 'overrideWindowState', 'own_current', 'paintEngine', 'paintEvent', 'paintingActive', 'palette', 'parent', 'parentWidget', 'physicalDpiX',
 'physicalDpiY', 'picamera2', 'pos', 'preview_window', 'previousInFocusChain', 'program_image', 'program_overlay', 'property', 
 'pyqtConfigure', 'raise_', 'recalculate_viewport', 'receivers', 'rect', 'releaseKeyboard', 'releaseMouse', 'releaseShortcut',
 'removeAction', 'removeEventFilter', 'render', 'render_request', 'repaint', 'resize', 'resizeEvent', 'restoreGeometry',
 'running', 'saveGeometry', 'screen', 'scroll', 'sender', 'senderSignalIndex', 'setAcceptDrops', 'setAccessibleDescription', 
 'setAccessibleName', 'setAttribute', 'setAutoFillBackground', 'setBackgroundRole', 'setBaseSize', 'setContentsMargins',
 'setContextMenuPolicy', 'setCursor', 'setDisabled', 'setEnabled', 'setFixedHeight', 'setFixedSize', 'setFixedWidth',
 'setFocus', 'setFocusPolicy', 'setFocusProxy', 'setFont', 'setForegroundRole', 'setGeometry', 'setGraphicsEffect', 
 'setHidden', 'setInputMethodHints', 'setLayout', 'setLayoutDirection', 'setLocale', 'setMask', 'setMaximumHeight', 
 'setMaximumSize', 'setMaximumWidth', 'setMinimumHeight', 'setMinimumSize', 'setMinimumWidth', 'setMouseTracking', 
 'setObjectName', 'setPalette', 'setParent', 'setProperty', 'setShortcutAutoRepeat', 'setShortcutEnabled', 'setSizeIncrement', 
 'setSizePolicy', 'setStatusTip', 'setStyle', 'setStyleSheet', 'setTabOrder', 'setTabletTracking', 'setToolTip', 'setToolTipDuration', 
 'setUpdatesEnabled', 'setVisible', 'setWhatsThis', 'setWindowFilePath', 'setWindowFlag', 'setWindowFlags', 'setWindowIcon',
 'setWindowIconText', 'setWindowModality', 'setWindowModified', 'setWindowOpacity', 'setWindowRole', 'setWindowState', 'setWindowTitle',
 'set_overlay', 'sharedPainter', 'show', 'showEvent', 'showFullScreen', 'showMaximized', 'showMinimized', 'showNormal', 
 'signal_done', 'signalsBlocked', 'size', 'sizeHint', 'sizeIncrement', 'sizePolicy', 'stackUnder', 'startTimer', 'staticMetaObject',
 'statusTip', 'stop_count', 'style', 'styleSheet', 'surface', 'tabletEvent', 'testAttribute', 'thread', 'timerEvent',
 'title_function', 'toolTip', 'toolTipDuration', 'tr', 'transform', 'underMouse', 'ungrabGesture', 'unsetCursor',
 'unsetLayoutDirection', 'unsetLocale', 'update', 'updateGeometry', 'updateMicroFocus', 'updatesEnabled', 'visibleRegion',
 'whatsThis', 'wheelEvent', 'width', 'widthMM', 'winId', 'window', 'windowFilePath', 'windowFlags', 'windowHandle', 'windowIcon',
 'windowIconChanged', 'windowIconText', 'windowIconTextChanged', 'windowModality', 'windowOpacity', 'windowRole', 'windowState', 
 'windowTitle', 'windowTitleChanged', 'windowType', 'x', 'y']
"""