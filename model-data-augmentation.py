
# For running inference on the TF-Hub module
import tensorflow as tf
from tensorflow.keras import datasets, layers, models
from sklearn.model_selection import train_test_split
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras import layers, optimizers

# For downloading the image.
import matplotlib.pyplot as plt
import tempfile
from six.moves.urllib.request import urlopen
from six import BytesIO
from zipfile import ZipFile
import pandas as pd

# For image manipulation.
import numpy as np
from skimage import data
from skimage.color import rgb2gray
from skimage import transform

# For measuring the inference time.
import time

# Print Tensorflow version
print(tf.__version__)

# Check available GPU devices.
print("The following GPU devices are available: %s" % tf.test.gpu_device_name())


"""Load in df of images (3 traches) created by download_data.py"""

df = pd.read_csv('tranch_master.csv')
df = df.dropna(subset=['primary_posture'])
df = df.reset_index(drop=True)
df = df[df['primary_posture'] != 'Unknown']

# numerical mappings for labels
categories = {'Sitting': 0, 'Standing': 1, 'Lying': 2}
df['primary_posture_n'] = df['primary_posture'].map(categories)


"""Model"""


all_ims = []
all_labels = []

print('\nloading images')

# data augmentation start
sitCount = 0
lyingCount = 0
standCount = 0
import cv2
# Reading images from DataFrame and duplicating each lying image with a random augmentation
for i in range(len(df)):
    im = cv2.imread(df.iloc[i].file_path)
    im = cv2.resize(im, (224, 224))
    label = df.iloc[i].primary_posture_n
    if label == 0:
        if sitCount <= len(df)//4:
            for i in range(0, 2):
                all_ims.append(im)
                all_labels.append(0)
            sitCount += 2
        else:
            all_ims.append(im)
            all_labels.append(0)
            sitCount += 1
    elif label == 2:
        if lyingCount <= len(df)//6:
            for i in range(0, 2):
                all_ims.append(im)
                all_labels.append(2)
            lyingCount += 2
        else:
            all_ims.append(im)
            all_labels.append(2)
            lyingCount += 1
    elif label == 1 and standCount < 20000:
        all_ims.append(im)
        all_labels.append(df.iloc[i].primary_posture_n)
        standCount += 1


# data augmentation end


print('\nsplitting images')
# Split images and labels into train and test sets
train_ims, test_ims, train_labels, test_labels = train_test_split(all_ims, all_labels, test_size=.20)

print('\nfinishing loading images')
print('len of train images:', len(train_ims))
print('len of test images:', len(test_ims))

# create train and test matrixes
train_ims = np.array( train_ims ) / 255
train_labels = np.array( train_labels )
print('train matrix created')
test_ims = np.array( test_ims ) / 255
test_labels = np.array( test_labels )
print('test matrix created')

# Convert the labels to categorical variables
train_labels = tf.keras.utils.to_categorical( train_labels , num_classes=3 )
test_labels = tf.keras.utils.to_categorical( test_labels , num_classes=3 )


# Create model instance and add layers
print('\loading model')
base_model = MobileNetV2(weights='imagenet',include_top=False, input_shape=(224, 224, 3)) # 224, 224
x = base_model.output
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dense(1024,activation='relu')(x)
x = layers.Dense(1024,activation='relu')(x)
x = layers.Dense(512,activation='relu')(x)
preds = layers.Dense(3, activation='softmax')(x)
model = models.Model(inputs=base_model.input,outputs=preds)


# fine tuning on top of base MobileNet model
fine_tune_at = 100
for layer in model.layers[:fine_tune_at]:
    layer.trainable=False
for layer in model.layers[fine_tune_at:]:
    layer.trainable=True

# Compile the model
model.compile(optimizer='Adam',loss='categorical_crossentropy',metrics=["accuracy"])

print('\ntraining')
print()

# Fit model to train data
history = model.fit(
    train_ims, train_labels,
    epochs=80,
    batch_size=18,
    callbacks=None,
    validation_split=0.3
)

# Evaluate the model on test images
print('\ntesting')
results = model.evaluate(test_ims, test_labels)

print("test loss, test acc:", results)
print()


# confusion matrix
predictions = model.predict(test_ims)
pl = [np.argmax(x) for x in predictions]
tl = [np.argmax(x) for x in test_labels]

print('prediction shape', pl)
print('test labels', tl)
print(tf.math.confusion_matrix(tl, pl))


# accuray graph
plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.savefig('Accuracy2.pdf')

plt.close()

# loss graph
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.savefig('Loss2.pdf')