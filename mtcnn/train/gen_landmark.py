import os
import random

import cv2
import progressbar
import numpy as np
import numpy.random as npr

from mtcnn.utils.functional import IoU


def get_landmark_data(output_folder, suffix='landmarks'):
    
    output_folder = os.path.join(output_folder, suffix)

    images = np.load(os.path.join(output_folder, 'image_matrix.npy'))
    landmarks = np.load(os.path.join(output_folder, 'landmarks.npy'))

    return images, landmarks



def gen_landmark_data(meta, size, output_folder, argument=False, suffix='landmarks'):
    """For training MTCNN, generate data for facial landmark localization task. 
    The Generated file will be saved in "output_folder"

    Args:
        meta (list): Each item contains a dict with file_name, num_bb (Number of bounding box), meta_data (x1, y1, w, h), landmarks (lefteye_x lefteye_y righteye_x righteye_y nose_x nose_y leftmouth_x leftmouth_y rightmouth_x rightmouth_y).
        size (int): The size of the saved image.
        output_folder (str): Directory to save the result.
        argument (bool, optional): Defaults to False. Apply augmentation or not.
    """
    final_images = []
    final_landmarks = []

    bar = progressbar.ProgressBar(max_value=len(meta) - 1)

    for index, item in enumerate(meta):
        bar.update(index)
        image_path = item['file_name']
        boxes = item['meta_data']
        landmarks = item['landmarks']

        img = cv2.imread(image_path)
        img_w = img.shape[0]
        img_h = img.shape[1]

        for bbox, landmark in zip(boxes, landmarks):
            left = bbox[0]
            top = bbox[1]
            w = bbox[2]
            h = bbox[3]
            right = bbox[0]+w+1
            bottom = bbox[1]+h+1

            # Crop the face image.
            face_img = img[top: bottom, left: right]

            # Resize the image
            face_img = cv2.resize(face_img, (size, size))

            # Resize landmark as (5, 2)
            landmark = np.array(landmark)
            landmark.resize(5, 2)

            # (( x - bbox.left)/ width of bounding box, (y - bbox.top)/ height of bounding box
            landmark_gtx = (landmark[:, 0] - left) / w
            landmark_gty = (landmark[:, 1] - top) / h
            landmark_gt = np.stack([landmark_gtx, landmark_gty], 1)

            final_images.append(face_img)
            final_landmarks.append(landmark_gt)

            if not argument:
                continue

            if max(w, h) < 40 or left < 0 or right < 0 or min(w, h) < 0:
                continue

            # random shift
            for i in range(10):
                bbox_size = npr.randint(
                    int(min(w, h) * 0.8), np.ceil(1.25 * max(w, h)))
                delta_x = npr.randint(-w * 0.2, w * 0.2)
                delta_y = npr.randint(-h * 0.2, h * 0.2)
                nx1 = int(max(left+w/2-bbox_size/2+delta_x, 0))
                ny1 = int(max(top+h/2-bbox_size/2+delta_y, 0))

                nx2 = nx1 + bbox_size
                ny2 = ny1 + bbox_size
                if nx2 > img_w or ny2 > img_h:
                    continue

                crop_box = np.array([nx1, ny1, nx2, ny2])
                gt_box = np.array([left, top, right, bottom])

                iou = IoU(crop_box, np.expand_dims(gt_box, 0))

                if iou > 0.65:
                    landmark_croppedx = (landmark[:, 0] - nx1) / bbox_size
                    landmark_croppedy = (landmark[:, 1] - ny1) / bbox_size
                    landmark_gt = np.stack(
                        [landmark_croppedx, landmark_croppedy], 1)

                    cropped_img = img[ny1: ny2, nx1: nx2]
                    cropped_img = cv2.resize(cropped_img, (size, size))

                    final_images.append(cropped_img)
                    final_landmarks.append(landmark_gt)

    # Joint all face images and landmarks together
    final_images = np.stack(final_images)
    final_landmarks = np.stack(final_landmarks)

    output_folder = os.path.join(output_folder, suffix)
    # Save the result
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    np.save(os.path.join(output_folder, 'image_matrix.npy'), final_images)
    np.save(os.path.join(output_folder, 'landmarks.npy'), final_landmarks)
