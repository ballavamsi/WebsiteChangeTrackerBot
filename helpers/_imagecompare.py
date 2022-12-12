import cv2
import imutils
import os
import numpy as np


class ImageComparer:
    def __init__(self, track_id, image1, image2):
        self.track_id = track_id
        self.image1 = image1
        self.image2 = image2

    def mse(self, img1, img2):
        h, w = img1.shape
        diff = cv2.subtract(img1, img2)
        err = np.sum(diff**2)
        mse = err/(float(h*w))
        return mse, diff

    def compare(self):
        image1 = cv2.imread(self.image1)
        image2 = cv2.imread(self.image2)
        # convert the images to grayscale
        grayA = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        grayB = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        # compute the Structural Similarity Index (SSIM) between the two
        # images, ensuring that the difference image is returned
        error, diff = self.mse(grayA, grayB)
        return error

    def compare_and_highlight(self):
        original = cv2.imread(self.image1)
        new = cv2.imread(self.image2)
        # resize the images to make them small in size. A bigger
        # size image may take a significant time
        # more computing power and time
        original = imutils.resize(original, height=600)
        new = imutils.resize(new, height=600)
        # create a copy of original image so that we can store the
        # difference of 2 images in the same on
        diff = original.copy()
        cv2.absdiff(original, new, diff)
        # converting the difference into grayscale images
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # increasing the size of differences after that we can capture them all
        for i in range(0, 3):
            dilated = cv2.dilate(gray.copy(), None, iterations=i+1)

        # threshold the gray image to binary it. Anything pixel that has
        # value higher than 3 we are converting to white
        # (remember 0 is black and 255 is exact white)
        # the image is called binarised as any value lower than 3 will be 0 and
        # all of the values equal to and higher than 3 will be 255
        (T, thresh) = cv2.threshold(dilated, 3, 255, cv2.THRESH_BINARY)

        # now we have to find contours in the binarized image
        cnts = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        for c in cnts:
            # nicely fiting a bounding box to the contour
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(new, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # get file name and path of image2
        path = os.path.dirname(self.image2)
        filename = os.path.basename(self.image2)

        output_file_name = f"data/screenshot_{self.track_id}_diff.png"
        cv2.imwrite(output_file_name, new)
        return output_file_name
