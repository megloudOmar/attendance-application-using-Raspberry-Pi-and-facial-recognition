from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot, QTimer, QDate, Qt 
from PyQt5.QtWidgets import QDialog, QMessageBox, QApplication
from imutils.video import VideoStream
import imutils
import cv2
import face_recognition 
import numpy as np
import datetime
import csv
import argparse
import pickle
import sys
import time


ap = argparse.ArgumentParser()
ap.add_argument("-c", "--cascade", required=True, help = "path to where the face cascade resides")
ap.add_argument("-e", "--encodings", required=True, help="path to serialized db of facial encodings")
args = vars(ap.parse_args())



class MainWindow(QDialog):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("gui.ui", self)                                      
        self.image = None
        self.startVideo()
        title = "Time tracking application"
        self.setWindowTitle(title)
        # Update date and time
        now = QDate.currentDate()
        current_date = now.toString('dd.MM.yyyy')
        current_time = datetime.datetime.now().strftime('%H:%M:%S')
        
        self.dateLabel.setText(current_date)
        self.timeLabel.setText(current_time)
        

    @pyqtSlot()
    def startVideo(self):
        self.capture = VideoStream(usePiCamera=True).start()
        time.sleep(0.2)
        self.timer = QTimer(self)  # Create Timer
        self.timer.timeout.connect(self.update_frame)  # Connect timeout to the output function
        self.timer.start(10)  # emit the timeout() signal at x=10ms

    def face_rec(self, frame):
        data = pickle.loads(open(args["encodings"], "rb").read())                                       
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
        detector = cv2.CascadeClassifier(args["cascade"])
        rects = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]

        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []
        for encoding in encodings:
            matches = face_recognition.compare_faces(data["encodings"], encoding)
            name = "Unknown"
            if True in matches:
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}
                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1
                name = max(counts, key=counts.get)
            names.append(name)
        for ((top, right, bottom, left), name) in zip(boxes, names):

            cv2.rectangle(frame, (left, top), (right, bottom),(0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
            self.markAttendance(name)       
        return frame

    def markAttendance(self, name):
        if self.clockInButton.isChecked():
            self.clockInButton.setEnabled(False)
            with open('attendance.csv', 'a') as f:
                if (name != "Unknown"):
                    buttonReply = QMessageBox.question(self, "Welcome " + name, "Are you clocking in?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No )
                    if buttonReply == QMessageBox.Yes:
                        date_time_string = datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S")
                        f.writelines(f'\n{name},{date_time_string},Clock in')
                        self.clockInButton.setChecked(False)
                        self.nameLabel.setText(name)
                        self.statusLabel.setText("Clocked in")
                        self.hoursLabel.setText('Measuring')
                        self.minutesLabel.setText('')
                        self.Time1 = datetime.datetime.now()
                        self.clockInButton.setEnabled(True)
                    else:
                        print("not clicked")
                        self.clockInButton.setEnabled(True)
        elif self.clockOutButton.isChecked():
            self.clockOutButton.setEnabled(False)
            with open('attendance.csv', 'a') as f:
                if (name != "Unknown"):
                    buttonReply = QMessageBox.question(self, "Welcome " + name, "Are you clocking out?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No )
                    if buttonReply == QMessageBox.Yes:
                        date_time_string = datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S")
                        f.writelines(f'\n{name},{date_time_string},Clock out')
                        self.clockOutButton.setChecked(False)
                        self.nameLabel.setText(name)
                        self.statusLabel.setText("Clocked out")
                        h, m = self.Duration(name)
                        self.minutesLabel.setText(str(m)+"m")
                        self.hoursLabel.setText(str(h)+"h")
                        self.clockOutButton.setEnabled(True)
                        print(h)
                        print(m)
                    else:
                        print("not clicked")
                        self.clockOutButton.setEnabled(True)
    
    
    def Duration(self, name):
        file = open('attendance.csv')
        csvreader = csv.reader(file, delimiter=',')
        in_l = []
        out_l = []
        for row in csvreader:
            if row[0] == name and row[2] == 'Clock in':
                    in_l.append(row[1])
            if row[0] == name and row[2] == 'Clock out':
                    out_l.append(row[1])
        time_in = datetime.datetime.strptime(in_l[-1], '%y/%m/%d %H:%M:%S')
        time_out = datetime.datetime.strptime(out_l[-1], '%y/%m/%d %H:%M:%S')
        dt = time_out - time_in
        seconds = dt.total_seconds()
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return hours, minutes
    
    
    def update_frame(self):
        self.image = self.capture.read()
        self.displayImage(self.image, 1)


    def displayImage(self, image, window=1):
        image = cv2.resize(image, (420, 340))
        try:
            image = self.face_rec(image)
        except Exception as e:
            print(e)
        qformat = QImage.Format_Indexed8
        if len(image.shape) == 3:
            if image.shape[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888
        outImage = QImage(image, image.shape[1], image.shape[0], image.strides[0], qformat)
        outImage = outImage.rgbSwapped()

        if window == 1:
            self.imgLabel.setPixmap(QPixmap.fromImage(outImage))
            self.imgLabel.setScaledContents(True)
            
if __name__ == "__main__":
    App = QApplication(sys.argv)
    ui = MainWindow()
    ui.show()
    sys.exit(App.exec_())
