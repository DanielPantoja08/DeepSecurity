from core.classifiers import *
import cv2
import numpy as np
import tensorflow as tf

class Classifier:
    def __init__(self):
        self.model = MesoInception4()
        self.model.load("models/weights/MesoInception_DF.h5")
    
    def predict(self, x):
        x = cv2.resize(x,(256,256))
        x = x.astype('float')/255.0
        x = tf.keras.preprocessing.image.img_to_array(x)
        x = np.expand_dims(x,axis = 0)
        prediction = self.model.predict(x)
        return prediction[0][0]