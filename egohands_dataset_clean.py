import scipy.io as sio
import numpy as np
import os
import gc
import six.moves.urllib as urllib
import cv2
import time
import xml.etree.cElementTree as ET
import random
import shutil as sh
from shutil import copyfile
import zipfile

import csv


def save_csv(csv_path, csv_content):
    with open(csv_path, 'w') as csvfile:
        wr = csv.writer(csvfile)
        for i in range(len(csv_content)):
            wr.writerow(csv_content[i])

def save_txt(txt_path, cls, x_c, y_c, w, h):
    with open(txt_path, 'w') as txtfile:
        outtxt = cls, x_c, y_c, w, h
        txtfile.write(str(outtxt) + '\n')

def get_bbox_visualize(base_path, dir):
    image_path_array = []
    for root, dirs, filenames in os.walk(base_path + dir):
        for f in filenames:
            if(f.split(".")[1] == "jpg"):
                img_path = base_path + dir + "/" + f
                image_path_array.append(img_path)

    #sort image_path_array to ensure its in the low to high order expected in polygon.mat
    image_path_array.sort()
    boxes = sio.loadmat(
        base_path + dir + "/polygons.mat")
    # there are 100 of these per folder in the egohands dataset
    polygons = boxes["polygons"][0]
    # first = polygons[0]
    # print(len(first))
    pointindex = 0

    for first in polygons:
        index = 0

        font = cv2.FONT_HERSHEY_SIMPLEX

        img_id = image_path_array[pointindex]
        img = cv2.imread(img_id)

        img_params = {}
        img_params["width"] = np.size(img, 1)
        img_params["height"] = np.size(img, 0)
        head, tail = os.path.split(img_id)
        img_params["filename"] = tail
        img_params["path"] = os.path.abspath(img_id)
        img_params["type"] = "train"
        pointindex += 1

        boxarray = []
        csvholder = []
        for pointlist in first:
            pst = np.empty((0, 2), int)
            max_x = max_y = min_x = min_y = height = width = 0

            findex = 0
            for point in pointlist:
                if(len(point) == 2):
                    x = int(point[0])
                    y = int(point[1])

                    if(findex == 0):
                        min_x = x
                        min_y = y
                    findex += 1
                    max_x = x if (x > max_x) else max_x
                    min_x = x if (x < min_x) else min_x
                    max_y = y if (y > max_y) else max_y
                    min_y = y if (y < min_y) else min_y
                    # print(index, "====", len(point))
                    appeno = np.array([[x, y]])
                    pst = np.append(pst, appeno, axis=0)
                    cv2.putText(img, ".", (x, y), font, 0.7,
                                (255, 255, 255), 2, cv2.LINE_AA)

            hold = {}
            hold['minx'] = min_x
            hold['miny'] = min_y
            hold['maxx'] = max_x
            hold['maxy'] = max_y
            if (min_x > 0 and min_y > 0 and max_x > 0 and max_y > 0):
                boxarray.append(hold)
                labelrow = [tail,
                            np.size(img, 1), np.size(img, 0), "hand", min_x, min_y, max_x, max_y]
                csvholder.append(labelrow)

            cv2.polylines(img, [pst], True, (0, 255, 255), 1)
            cv2.rectangle(img, (min_x, max_y),
                          (max_x, min_y), (0, 255, 0), 1)

        csv_path = img_id.split(".")[0]
        if not os.path.exists(csv_path + ".csv"):
            cv2.putText(img, "DIR : " + dir + " - " + tail, (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (77, 255, 9), 2)
            cv2.imshow('Verifying annotation ', img)
            save_csv(csv_path + ".csv", csvholder)
            print("===== saving csv file for ", tail)
        cv2.waitKey(2)  # close window when a key press is detected

# Create text files in normalized yolo format rather than csv file
# <x> <y> <width> <height> - float values relative to width and height of image, it can be equal from 0.0 to 1.0
# <x> = <absolute_x> / <image_width> or <height> = <absolute_height> / <image_height>
# images are 1280 x 720
# x, y are center coords of rectangle
def format_txt_bb(base_path, out_path):
    for file in os.listdir(base_path):
        with open(base_path + file, "r") as filestream:
            print("Opening file: " + base_path + file)

            out_file = open(out_path + file, "w")

            for line in filestream:
                currentline = line.split(",")

                if (currentline[0] != '\n'):
                    # filename, img_x, img_y, img_class, x1, y1, x2, y2
                    # CARDS_COURTYARD_B_T_frame_0176.jpg, 1280, 720, hand, 610, 432, 783, 541
                    img_x = float(currentline[1])
                    img_y = float(currentline[2])
                    
                    # Hand class 
                    img_class = 0
                    if (currentline[3] == 'hand'):
                        img_class = 0

                    x1 = float(currentline[4])
                    y1 = float(currentline[5])
                    x2 = float(currentline[6])
                    y2 = float(currentline[7])
                    
                    # Compute scaled x_c, y_c, w, h settings
                    x_c = ((x1 + x2) / 2.0) / img_x
                    y_c = ((y1 + y2) / 2.0) / img_y
                    w = (x2 - x1) / img_x
                    h = (y2 - y1) / img_y

                    # Check for nan values
                    import math
                    if (math.isnan(x_c)):
                        x_c = 0
                        print('Found NAN value')
                    if (math.isnan(y_c)):
                        y_c = 0
                        print('Found NAN value')
                    if (math.isnan(w)):
                        w = 0
                        print('Found NAN value')
                    if (math.isnan(h)):
                        h = 0
                        print('Found NAN value')

                    out_file.write(
                        str(img_class) + " " + 
                        str(x_c) + " " + 
                        str(y_c) + " " + 
                        str(w) + " " + 
                        str(h) + 
                        "\n")

            out_file.close
                

def create_directory(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# combine all individual csv files for each image into a single csv file per folder.


# def generate_label_files(image_dir):
#     header = ['filename', 'width', 'height',
#               'class', 'xmin', 'ymin', 'xmax', 'ymax']
#     for root, dirs, filenames in os.walk(image_dir):
#         for dir in dirs:
#             csvholder = []
#             csvholder.append(header)
#             loop_index = 0
#             for f in os.listdir(image_dir + dir):
#                 if(f.split(".")[1] == "csv"):
#                     loop_index += 1
#                     #print(loop_index, f)
#                     csv_file = open(image_dir + dir + "/" + f, 'r')
#                     reader = csv.reader(csv_file)
#                     for row in reader:
#                         csvholder.append(row)
#                     csv_file.close()
#                     os.remove(image_dir + dir + "/" + f)
#             save_csv(image_dir + dir + "/" + dir + "_labels.csv", csvholder)
#             print("Saved label csv for ", dir, image_dir +
#                   dir + "/" + dir + "_labels.csv")


# Split data, copy to train/test folders
def split_data_test_eval_train(image_dir):
    create_directory("images")
    create_directory("images/train")
    create_directory("images/test")

    create_directory("labels")
    create_directory("labels/train")
    create_directory("labels/test")

    data_size = 4000
    loop_index = 0
    data_sampsize = int(0.1 * data_size)
    test_samp_array = random.sample(range(data_size), k=data_sampsize)

    for root, dirs, filenames in os.walk(image_dir):
        for dir in dirs:
            for f in os.listdir(image_dir + dir):
                if(f.split(".")[1] == "jpg"):
                    loop_index += 1
                    print(loop_index, f)

                    if loop_index in test_samp_array:
                        os.rename(image_dir + dir +
                                  "/" + f, "images/test/" + f)
                        os.rename(image_dir + dir +
                                  "/" + f.split(".")[0] + ".csv", "labels/test/" + f.split(".")[0] + ".txt")
                    else:
                        os.rename(image_dir + dir +
                                  "/" + f, "images/train/" + f)
                        os.rename(image_dir + dir +
                                  "/" + f.split(".")[0] + ".csv", "labels/train/" + f.split(".")[0] + ".txt")
                    print(loop_index, image_dir + f)
            print(">   done scanning director ", dir)
            os.remove(image_dir + dir + "/polygons.mat")
            os.rmdir(image_dir + dir)

        print("Train/test content generation complete!")
        # generate_label_files("images/")


def generate_csv_files(image_dir):
    for root, dirs, filenames in os.walk(image_dir):
        for dir in dirs:
            get_bbox_visualize(image_dir, dir)

    print("CSV generation complete!\nGenerating train/test/eval folders")
    split_data_test_eval_train("egohands/_LABELLED_SAMPLES/")          

# rename image files so we can have them all in a train/test/eval folder.
def rename_files(image_dir):
    print("Renaming files")
    loop_index = 0
    for root, dirs, filenames in os.walk(image_dir):
        for dir in dirs:
            for f in os.listdir(image_dir + dir):
                if (dir not in f):
                    if(f.split(".")[1] == "jpg"):
                        loop_index += 1
                        os.rename(image_dir + dir +
                                  "/" + f, image_dir + dir +
                                  "/" + dir + "_" + f)
                else:
                    break

    generate_csv_files("egohands/_LABELLED_SAMPLES/")

def extract_folder(dataset_path):
    print("Egohands dataset already downloaded.\nGenerating CSV files")
    if not os.path.exists("egohands"):
        zip_ref = zipfile.ZipFile(dataset_path, 'r')
        print("> Extracting Dataset files")
        zip_ref.extractall("egohands")
        print("> Extraction complete")
        zip_ref.close()
        rename_files("egohands/_LABELLED_SAMPLES/")

def download_egohands_dataset(dataset_url, dataset_path):
    is_downloaded = os.path.exists(dataset_path)
    if not is_downloaded:
        print(
            "> downloading egohands dataset. This may take a while (1.3GB, say 3-5mins). Coffee break?")
        opener = urllib.request.URLopener()
        opener.retrieve(dataset_url, dataset_path)
        print("> download complete")
        extract_folder(dataset_path)

    else:
        extract_folder(dataset_path)


EGOHANDS_DATASET_URL = "http://vision.soic.indiana.edu/egohands_files/egohands_data.zip"
EGO_HANDS_FILE = "egohands_data.zip"


# download_egohands_dataset(EGOHANDS_DATASET_URL, EGO_HANDS_FILE)

format_txt_bb('F:\\Data\\handtracking\\labels\\test\\', 'F:\\Data\\handtracking\\labels_format\\test\\')
format_txt_bb('F:\\Data\\handtracking\\labels\\train\\', 'F:\\Data\\handtracking\\labels_format\\train\\')
