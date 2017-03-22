#coding:utf-8
import os,sys,csv
import numpy
import numpy as np
import multiprocessing

from generator import HawkesGenerator
from discriminator import CNNDiscriminator

cpu = multiprocessing.cpu_count()

class HawkesGAN(object):
	def __init__(self):
		self.gen = HawkesGenerator()
		self.dis = CNNDiscriminator()

	def full_train(self,full_sequences,train_sequences,features,publish_years,pids,superparams):
		from keras.layers import Input, Dense, Flatten, Convolution2D, Activation, Dropout, merge
		from keras.models import Model
		from keras.regularizers import l1,l2

		nb_sequence = len(full_sequences)
		nb_event = len(train_sequences[0])
		pred_length = len(full_sequences[0]) - nb_event
		nb_type = len(full_sequences[0][0])
		nb_feature = len(full_sequences[0][0][0])

		# pretrain generator
		if self.gen.params is None:
			raise Exception('generator not pretrained')

		# compile keras models
		self.gen.create_trainable_model(train_sequences,pred_length)
		self.dis.create_trainable_model(nb_event + pred_length,nb_type,nb_feature)
		self.dis.model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['categorical_accuracy'])

		self.dis.model.trainable = False
		for l in self.dis.model.layers: l.trainable = False
		x = Input(shape=(1,), dtype='int32')
		y = self.gen.model(x)
		z = self.dis.model(y)
		gan_model = Model(input=[x], output=[z])
		gan_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['categorical_accuracy'])

		# pretrain discrimnator
		X = np.arange(nb_sequence)
		Y = self.gen.model.predict(X,batch_size=1)
		print {
			'np.mean(Y[:,15:])':np.mean(Y[:,15:]),
			'np.mean(Y[:,0:15])':np.mean(Y[:,0:15]),
			'np.mean(np.array(full_sequences)[:,15:])':np.mean(np.array(full_sequences)[:,15:]),
			'np.mean(np.array(full_sequences)[:,0:15])':np.mean(np.array(full_sequences)[:,0:15]),
			'np.mean(np.array(train_sequences)[:,0:15])':np.mean(np.array(train_sequences)[:,0:15]),
		}
		Y = np.array([Y[i/2] if i % 2 == 0 else full_sequences[i/2] for i in range(2 * nb_sequence)])
		Z = np.array([[0.,1.] if i % 2 == 0 else [1.,0.] for i in range(2 * nb_sequence)])
		self.dis.model.fit(Y,Z,batch_size=1,epochs=1,verbose=1,validation_split=0.2)

		self.gen.model.summary()
		self.dis.model.summary()
		gan_model.summary()


		# full train gan model

		# self.dis.model.fit(
		# 	[np.array(full_sequences)],[np.array([[0.,1.] for i in xrange(nb_sequence)])],
		# 	nb_epoch=500, batch_size=1,
		# 	verbose=1,validation_split=0.2)

		# gan_model.fit(
		# 	[np.arange(nb_sequence)],[np.array([[0.,1.] for i in xrange(nb_sequence)])],
		# 	nb_epoch=500, batch_size=1,
		# 	verbose=1,validation_split=0.2)


	# def pre_train_hawkes(self,paper_data='../data/paper3.txt'):

	# def pre_train_cnn(self,paper_data='../data/paper3.txt'):
	# 	sequences,labels,features,publish_years,pids,superparams = self.dis.load(paper_data)
	# 	self.dis.model.fit(
	# 		[numpy.array(sequences)], [numpy.array(labels)],
	# 		nb_epoch=500, batch_size=1,
	# 		verbose=1,validation_split=0.2)

	def load(self,f,pred_length=10,train_length=15):
		# features[paper][feature], sequences[paper][day][feature]
		data = []
		pids = []
		for i,row in enumerate(csv.reader(file(f,'r'))):
			if i % 4 == 2:
				pids.append(str(row[0]))
				row = [float(row[1])]
			elif i % 4 == 0 or i % 4 == 1:
				row = [float(x) for x in row[1:]]
			elif i % 4 == 3:
				_row = [float(x) for x in row[1:]]
				_max = max(_row)
				_min = min(_row)
				row = [(x - _min)/float(_max - _min) for x in _row]
			data.append(row)
		
		I = int(len(data)/4)
		#train_seq = []
		# test_seq = []
		full_sequences = []
		train_sequences = []
		features = []
		publish_years = []
		for i in range(I):
			publish_year = data[i * 4 + 2][0]
			self_seq = data[i * 4]
			nonself_seq = data[i * 4 + 1]
			feature = data[i * 4 + 3]
			#time_seq = self_seq + nonself_seq
			#time_seq.sort()

			sequence = []
			for year in range(int(pred_length + train_length)) :
				self_count = len([x for x in self_seq if year <= x and x < year + 1])
				nonself_count = len([x for x in nonself_seq if year <= x and x < year + 1])
				sequence.append([[self_count],[nonself_count]])
			full_sequences.append(sequence)

			features.append(feature)
			publish_years.append(publish_year)

			sequence = []
			for year in range(train_length) :
				self_count = len([x for x in self_seq if year <= x and x < year + 1])
				nonself_count = len([x for x in nonself_seq if year <= x and x < year + 1])
				sequence.append([[self_count],[nonself_count]])
			# for year in range(train_length,int(pred_length + train_length)) :
			# 	self_count = len([x for x in self_seq if year <= x and x < year + 1]) * 1.5
			# 	nonself_count = len([x for x in nonself_seq if year <= x and x < year + 1]) * 1.5
				# sequence.append([[self_count],[nonself_count]])
			train_sequences.append(sequence)

		superparams = {}
		# print {
		# 	# 'np.mean(np.array(full_sequences)[:,15:])':np.mean(np.array(full_sequences)[:,15:]),
		# 	'np.mean(np.array(full_sequences)[:,0:15])':np.mean(np.array(full_sequences)[:,0:15]),
		# 	'np.mean(np.array(train_sequences)[:,0:15])':np.mean(np.array(train_sequences)[:,0:15]),
		# }
		# exit()
		return full_sequences,train_sequences,features,publish_years,pids,superparams


# yield
if __name__ == '__main__':
	with open('../log/train_gan.log','w') as f:
		old_stdout = sys.stdout
		sys.stdout = f
		gan = HawkesGAN()
		try:
			gan.gen.params = json.load(open('../data/paper.pretrain.params.json'))
		except:
			loaded = gan.gen.load('../data/paper3.txt')
			gan.gen.pre_train(*loaded,max_outer_iter=1)
			with open('../data/paper.pretrain.params.json','w') as fw:
				json.dump(gan.gen.params,fw)
		loaded = gan.load('../data/paper3.txt')
		gan.full_train(*loaded)
		sys.stdout = old_stdout