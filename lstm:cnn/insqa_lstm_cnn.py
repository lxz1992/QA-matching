import datetime
import tensorflow as tf


##########################################################################
#  embedding_lookup + cnn + cosine margine ,  batch
##########################################################################
from tensorflow.contrib.rnn import BasicLSTMCell
from tensorflow.contrib.rnn import static_bidirectional_rnn


class InsQALSTMCNN(object):
    def __init__(
            self, sequence_length, batch_size,
            embeddings,embedding_size,
            filter_sizes, num_filters, l2_reg_lambda=0.0):
        # 用户问题,字向量使用embedding_lookup
        self.input_x_1 = tf.placeholder(tf.int32, shape=[None, sequence_length], name="input_x_1")
        # 待匹配正向问题
        self.input_x_2 = tf.placeholder(tf.int32, shape=[None, sequence_length], name="input_x_2")
        # 负向问题
        self.input_x_3 = tf.placeholder(tf.int32, shape=[None, sequence_length], name="input_x_3")
        # word2vec
        self.embeddings = embeddings

        self.dropout_keep_prob = 0.1 # tf.placeholder(tf.float32, name="dropout_keep_prob")
        l2_loss = tf.constant(0.0)
        print("input_x_1 ", self.input_x_1)

        # Embedding layer
        with tf.device('/cpu:0'), tf.name_scope("embedding"):
            # W = tf.Variable(
            #     tf.random_uniform([vocab_size, embedding_size], -1.0, 1.0),
            #     name="W")
            W = tf.Variable(tf.to_float(self.embeddings), trainable=True, name="W")
            questions = tf.nn.embedding_lookup(W, self.input_x_1)
            trueAnswers = tf.nn.embedding_lookup(W, self.input_x_2)
            falseAnswers = tf.nn.embedding_lookup(W, self.input_x_3)
            # self.embedded_chars_1 = tf.nn.dropout(chars_1, self.dropout_keep_prob)
            # self.embedded_chars_2 = tf.nn.dropout(chars_2, self.dropout_keep_prob)
            # self.embedded_chars_3 = tf.nn.dropout(chars_3, self.dropout_keep_prob)
            self.embedded_chars_1 = questions
            self.embedded_chars_2 = trueAnswers
            self.embedded_chars_3 = falseAnswers


        # def preprocess_BiRNN(x):
        #     x = tf.transpose(x, [1, 0, 2])
        #     # x = tf.reshape(x, [-1, embedding_size])
        #     # x = tf.split(x, sequence_length, 0)
        #     tf.unstack(x)
        #     return x
        #
        # preprocessed_1 = preprocess_BiRNN(self.embedded_chars_1)
        # preprocessed_2 = preprocess_BiRNN(self.embedded_chars_2)
        # preprocessed_3 = preprocess_BiRNN(self.embedded_chars_3)
        #
        #
        # def mybilstm(preprocessed_x):
        #     lstm_fw_cell = BasicLSTMCell(embedding_size // 2, forget_bias=1.0)
        #     lstm_bw_cell = BasicLSTMCell(embedding_size // 2, forget_bias=1.0)
        #     outputs, _, _ = static_bidirectional_rnn(lstm_fw_cell, lstm_bw_cell, preprocessed_x, dtype=tf.float32)
        #     return outputs
        #
        # with tf.variable_scope("my_bidirectional_lstm") as s:
        #     outputs_1 = mybilstm(preprocessed_1)
        #     s.reuse_variables()
        #     outputs_2 = mybilstm(preprocessed_2)
        #     outputs_3 = mybilstm(preprocessed_3)
        # outputs_1 = tf.stack(outputs_1)
        # outputs_1 = tf.transpose(outputs_1, [1, 0, 2])
        # outputs_2 = tf.stack(outputs_2)
        # outputs_2 = tf.transpose(outputs_2, [1, 0, 2])
        # outputs_3 = tf.stack(outputs_3)
        # outputs_3 = tf.transpose(outputs_3, [1, 0, 2])
        with tf.variable_scope("LSTM_scope", reuse=None):
            outputs_1 = self.biLSTMCell(questions, embedding_size // 2)
        print("h3")
        with tf.variable_scope("LSTM_scope", reuse=True):
            outputs_2 = self.biLSTMCell(trueAnswers, embedding_size // 2)
            outputs_3 = self.biLSTMCell(falseAnswers, embedding_size // 2)

        self.embedded_chars_expanded_1 = tf.expand_dims(outputs_1, -1)
        self.embedded_chars_expanded_2 = tf.expand_dims(outputs_2, -1)
        self.embedded_chars_expanded_3 = tf.expand_dims(outputs_3, -1)


        print("here")
        pooled_outputs_1 = []
        pooled_outputs_2 = []
        pooled_outputs_3 = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope("conv-maxpool-%s" % filter_size):
                filter_shape = [filter_size, embedding_size, 1, num_filters]
                W = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W")
                b = tf.Variable(tf.constant(0.1, shape=[num_filters]), name="b")
                conv = tf.nn.conv2d(
                    self.embedded_chars_expanded_1,
                    W,
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="conv-1"
                )
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu-1")
                pooled = tf.nn.max_pool(
                    h,
                    ksize=[1, sequence_length - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="poll-1"
                )
                pooled_outputs_1.append(pooled)

                conv = tf.nn.conv2d(
                    self.embedded_chars_expanded_2,
                    W,
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="conv-2"
                )
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu-2")
                pooled = tf.nn.max_pool(
                    h,
                    ksize=[1, sequence_length - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="poll-2"
                )
                pooled_outputs_2.append(pooled)

                conv = tf.nn.conv2d(
                    self.embedded_chars_expanded_3,
                    W,
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="conv-3"
                )
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu-3")
                pooled = tf.nn.max_pool(
                    h,
                    ksize=[1, sequence_length - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="poll-3"
                )
                pooled_outputs_3.append(pooled)
        num_filters_total = num_filters * len(filter_sizes)
        pooled_reshape_1 = tf.reshape(tf.concat(pooled_outputs_1, axis=3), [-1, num_filters_total])
        pooled_reshape_2 = tf.reshape(tf.concat(pooled_outputs_2, axis=3), [-1, num_filters_total])
        pooled_reshape_3 = tf.reshape(tf.concat(pooled_outputs_3, axis=3), [-1, num_filters_total])
        # dropout
        pooled_flat_1 = tf.nn.dropout(pooled_reshape_1, self.dropout_keep_prob)
        pooled_flat_2 = tf.nn.dropout(pooled_reshape_2, self.dropout_keep_prob)
        pooled_flat_3 = tf.nn.dropout(pooled_reshape_3, self.dropout_keep_prob)

        pooled_len_1 = tf.sqrt(tf.reduce_sum(tf.multiply(pooled_flat_1, pooled_flat_1), 1))  # 计算向量长度Batch模式
        pooled_len_2 = tf.sqrt(tf.reduce_sum(tf.multiply(pooled_flat_2, pooled_flat_2), 1))
        pooled_len_3 = tf.sqrt(tf.reduce_sum(tf.multiply(pooled_flat_3, pooled_flat_3), 1))
        pooled_mul_12 = tf.reduce_sum(tf.multiply(pooled_flat_1, pooled_flat_2), 1)  # 计算向量的点乘Batch模式
        pooled_mul_13 = tf.reduce_sum(tf.multiply(pooled_flat_1, pooled_flat_3), 1)

        with tf.name_scope("output"):
            self.cos_12 = tf.div(pooled_mul_12, tf.multiply(pooled_len_1, pooled_len_2), name="scores")  # 计算向量夹角Batch模式
            self.cos_13 = tf.div(pooled_mul_13, tf.multiply(pooled_len_1, pooled_len_3))

        zero = tf.constant(0, shape=[batch_size], dtype=tf.float32)
        margin = tf.constant(0.05, shape=[batch_size], dtype=tf.float32)
        with tf.name_scope("loss"):
            self.losses = tf.maximum(zero, tf.subtract(margin, tf.subtract(self.cos_12, self.cos_13)))
            self.loss = tf.reduce_sum(self.losses) + l2_reg_lambda * l2_loss
            print('loss ', self.loss)

        # Accuracy
        with tf.name_scope("accuracy"):
            self.correct = tf.equal(zero, self.losses)
            self.accuracy = tf.reduce_mean(tf.cast(self.correct, "float"), name="accuracy")

        # Define Training procedure
        self.optimizer = tf.train.AdamOptimizer(1e-1)
        self.train_op = self.optimizer.minimize(self.loss)

        # Summaries for loss and accuracy
        loss_summary = tf.summary.scalar("loss", self.loss)
        acc_summary = tf.summary.scalar("accuracy", self.accuracy)
        # Dev summaries
        self.dev_summary_op = tf.summary.merge([loss_summary, acc_summary])
        self.saver = tf.train.Saver(tf.global_variables())

    def train_step(self, x_batch_1, x_batch_2, x_batch_3, sess, step):
        """
        A single training step
        """
        feed_dict = {
            self.input_x_1: x_batch_1,
            self.input_x_2: x_batch_2,
            self.input_x_3: x_batch_3
        }
        summary_val, _, loss, accuracy = sess.run(
            [self.dev_summary_op,self.train_op, self.loss, self.accuracy],
            feed_dict)
        time_str = datetime.datetime.now().isoformat()
        if step % 120 == 119:
            train_writer = tf.summary.FileWriter('/Users/cjf/Downloads/log', sess.graph)
            train_writer.add_summary(summary_val,step)
            train_writer.close()
        print("{}: step {}, loss {:g}, acc {:g}".format(time_str, step, loss, accuracy))

    def dev_step(self, x_test_1, x_test_2, sess):
        feed_dict = {
            self.input_x_1: x_test_1,
            self.input_x_2: x_test_2,
            #self.input_x_3: x_test_3
        }
        batch_scores = sess.run([self.cos_12], feed_dict)
        return batch_scores

    @staticmethod
    def biLSTMCell(x, hiddenSize):
        input_x = tf.transpose(x, [1, 0, 2])
        input_x = tf.unstack(input_x)
        lstm_fw_cell = tf.contrib.rnn.BasicLSTMCell(hiddenSize, forget_bias=1.0, state_is_tuple=True)
        lstm_bw_cell = tf.contrib.rnn.BasicLSTMCell(hiddenSize, forget_bias=1.0, state_is_tuple=True)
        output, _, _ = tf.contrib.rnn.static_bidirectional_rnn(lstm_fw_cell, lstm_bw_cell, input_x,
                                                               dtype=tf.float32)
        output = tf.stack(output)
        output = tf.transpose(output, [1, 0, 2])
        return output