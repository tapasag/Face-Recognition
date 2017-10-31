#importing libraries

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from scipy import misc
import tensorflow as tf
import numpy as np
import sys
import time
import os
import cv2
import facenet
import align.detect_face

def main(sess, graph, target, class_names, labels, embeds):
    
	image_files=[target]
	image_size=160
    	image_margin=44
    
    	with graph.as_default():

        	with sess.as_default():
 			
			# Load and align images
            		st = time.time()
            		images = load_and_align_data(image_files, image_size, image_margin, 0.9)
            		print('Load and Align Images time = {}'.format(time.time() - st))
            		print(' ')
            
            		# Get input and output tensors
            		images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
            		embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
            		phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")

            		# Run forward pass to calculate embeddings
            		feed_dict = { images_placeholder: images, phase_train_placeholder:False }
            		st = time.time()
            		emb = sess.run(embeddings, feed_dict=feed_dict)
            		print('Feature Extraction time = {}'.format(time.time() - st))            
            		print(' ')
 
			# calculate distance between images	
			st = time.time() 
           		nrof_embeds = labels.size
            		nrof_images = len(image_files)
           		dist_array = np.zeros((nrof_embeds, nrof_images))
          
            		for i in range(nrof_embeds):
                		for j in range(nrof_images):
                			dist = np.sqrt(np.sum(np.square(np.subtract(embeds[i,:], emb[j,:]))))
                    			dist_array[i][j] = dist
            		print('Distance Calculation time = {}'.format(time.time() - st))
            		print(' ')

			# arranging distance in ascending order
            		pred_array = dist_array.argmin(0) 
         
			# threshold distance to 0.8
            		if dist_array[pred_array[0]][0] < 0.8 :
                		pred_label = labels[pred_array[0]]
                		pred_face = class_names[int(pred_label)]
                
            		else : 
                		pred_face = 'Unknown'
            
            		print('Face identified as:')
            		print(pred_face)
            		print(' ')
            		print('Face Distance:')
            		print(dist_array[pred_array[0]][0])            
            		print(' ')
            
	return pred_face
            
            
def load_and_align_data(image_paths, image_size, margin, gpu_memory_fraction):

    minsize = 20 # minimum size of face
    threshold = [ 0.6, 0.7, 0.7 ]  # three steps's threshold
    factor = 0.709 # scale factor
    tt = time.time()
    print('Creating networks and loading parameters')
    with tf.Graph().as_default():
        gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=gpu_memory_fraction)
        sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
        with sess.as_default():
            pnet, rnet, onet = align.detect_face.create_mtcnn(sess, None)
    print('Model align load time = {}'.format(time.time()-tt))
    print(' ')
            
    nrof_samples = len(image_paths)
    img_list = [None] * nrof_samples
    for i in range(nrof_samples):
        img = misc.imread(os.path.expanduser(image_paths[i]))
        img_size = np.asarray(img.shape)[0:2]
        tt = time.time()
        bounding_boxes, _ = align.detect_face.detect_face(img, minsize, pnet, rnet, onet, threshold, factor)
        print('Bounding boxes time = {}'.format(time.time()-tt))
        print(' ')
        det = np.squeeze(bounding_boxes[0,0:4])
        bb = np.zeros(4, dtype=np.int32)
        bb[0] = np.maximum(det[0]-margin/2, 0)
        bb[1] = np.maximum(det[1]-margin/2, 0)
        bb[2] = np.minimum(det[2]+margin/2, img_size[1])
        bb[3] = np.minimum(det[3]+margin/2, img_size[0])
        tt = time.time()
        cropped = img[bb[1]:bb[3],bb[0]:bb[2],:]
        aligned = misc.imresize(cropped, (image_size, image_size), interp='bilinear')
        prewhitened = facenet.prewhiten(aligned)
        print('Crop and align time = {}'.format(time.time()-tt))
        print(' ')
        img_list[i] = prewhitened
    images = np.stack(img_list)
    return images

if __name__ == '__main__':
    main(sess, graph, target, class_names, labels, embeds)
