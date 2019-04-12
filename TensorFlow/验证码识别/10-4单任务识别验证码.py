# coding: UTF-8
import tensorflow as tf
from PIL import Image
from nets import nets_factory # 引入从github上tensorflow/models/tree/master/research/slim/net复制过来的并进行了稍许修改
import numpy as np

# 字符集
CHAR_SET = [str(i) for i in range(10)]
CHAR_SET_LEN = len(CHAR_SET)
# 训练集大小
TRAIN_NUM = 5800
# 批次大小
BATCH_SIZE = 128
# 迭代次数
EPOCHES = 30
# 循环次数
LOOP_TIMES = EPOCHES*TRAIN_NUM//BATCH_SIZE
# tf文件训练集
TFRECORD_FILE = 'captcha/train.tfrecord'

# 初始学习率
LEARNING_RATE = 0.001

# 构成读取数据的tf张量和操作节点  的函数
def read_and_decode(filename):
    tf_queue = tf.train.string_input_producer([filename])
    reader = tf.TFRecordReader()
    _, serialized_example = reader.read(tf_queue)
    features = tf.parse_single_example(serialized_example,
                                       features={
                                           'image':tf.FixedLenFeature([], tf.string),
                                            'label0': tf.FixedLenFeature([], tf.int64),
                                            'label1': tf.FixedLenFeature([], tf.int64),
                                            'label2': tf.FixedLenFeature([], tf.int64),
                                            'label3': tf.FixedLenFeature([], tf.int64),
                                       })
    image = tf.decode_raw(features['image'], tf.uint8)
    image = tf.reshape(image,[224,224])
    # 下边三行是进行特征缩放将0-255的值域缩放到-1到1之间
    image = tf.cast(image, tf.float32) / 255.0
    image = tf.subtract(image, 0.5)
    image = tf.multiply(image, 2.0)

    label0 = tf.cast(features['label0'], tf.int32)
    label1 = tf.cast(features['label1'], tf.int32)
    label2 = tf.cast(features['label2'], tf.int32)
    label3 = tf.cast(features['label3'], tf.int32)
    return image, label0, label1, label2, label3
# 执行生成构成读取数据的tf张量和操作节点（此时并没有真正的在读数据，知识构成了相关的tf结构）
image, label0, label1, label2, label3 = read_and_decode(TFRECORD_FILE)
# 洗牌，将tf_queue顺序打乱，并读取结构为 [image, label0, label1, label2, label3]长度为batch_size的List   的tf结构
image_batch, label0_batch, label1_batch, label2_batch, label3_batch = tf.train.shuffle_batch(
    [image, label0, label1, label2, label3],
    batch_size=BATCH_SIZE,
    capacity=10000,
    min_after_dequeue=2000,
    num_threads=1
)


# 定义网络结构 这里我们通过借鉴和修改alexNet网络，实现一个多任务网络结构的训练模型
# 即：alexnet_v2_captcha_multi这个方法是在原本的alexnet_v2进行扩增的方法
# nets_factory网络工厂中还提供了vgg，谷歌的inception，resnet等各种网络模型不过网络模型较深对数据量和硬件需求较高
train_network_fn = nets_factory.get_network_fn(
    'alexnet_v2_captcha_single',
    num_classes=CHAR_SET_LEN*4,#指定分类数量是40种,更确切的说是输出神经元数量为  BATCH_SIZE*40
    weight_decay=0.0005,
    is_training=True
)

# 网络
x = tf.placeholder(tf.float32,[None,224,224])
y0 = tf.placeholder(tf.float32,[None])
y1 = tf.placeholder(tf.float32,[None])
y2 = tf.placeholder(tf.float32,[None])
y3 = tf.placeholder(tf.float32,[None])
lr = tf.Variable(LEARNING_RATE, dtype=tf.float32)
# alexnet_v2模型要求数据必须是244*244
X = tf.reshape(x,[BATCH_SIZE,224,224,1])
logits_, end_points = train_network_fn(X)

one_hot_label0 = tf.one_hot(indices=tf.cast(y0,tf.int32), depth=CHAR_SET_LEN)#indices中的每个数字都拉伸成用长度为depth的n个0和一个1的形式表示
one_hot_label1 = tf.one_hot(indices=tf.cast(y1,tf.int32), depth=CHAR_SET_LEN)
one_hot_label2 = tf.one_hot(indices=tf.cast(y2,tf.int32), depth=CHAR_SET_LEN)
one_hot_label3 = tf.one_hot(indices=tf.cast(y3,tf.int32), depth=CHAR_SET_LEN)
one_hot_label = tf.concat(values=[one_hot_label0, one_hot_label1, one_hot_label2, one_hot_label3],axis=1)
total_loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels=one_hot_label,logits=logits_))
optimizer = tf.train.AdamOptimizer(learning_rate=lr).minimize(total_loss)

# 计算准确率
logits0 = tf.cast(tf.slice(logits_, begin=[0,0], size=[-1,10]),tf.int32)
logits1 = tf.cast(tf.slice(logits_, begin=[0,10], size=[-1,10]),tf.int32)#从第0行的第10列开始切，-1代表所有的行都要，10代表往后切10列
logits2 = tf.cast(tf.slice(logits_, begin=[0,20], size=[-1,10]),tf.int32)
logits3 = tf.cast(tf.slice(logits_, begin=[0,30], size=[-1,10]),tf.int32)

correct_pre0 = tf.equal(tf.argmax(one_hot_label0, 1), tf.argmax(logits0, 1))
accuracy0 = tf.reduce_mean(tf.cast(correct_pre0, tf.float32))

correct_pre1 = tf.equal(tf.argmax(one_hot_label1, 1), tf.argmax(logits1, 1))
accuracy1 = tf.reduce_mean(tf.cast(correct_pre1, tf.float32))

correct_pre2 = tf.equal(tf.argmax(one_hot_label2, 1), tf.argmax(logits2, 1))
accuracy2 = tf.reduce_mean(tf.cast(correct_pre2, tf.float32))

correct_pre3 = tf.equal(tf.argmax(one_hot_label3, 1), tf.argmax(logits3, 1))
accuracy3 = tf.reduce_mean(tf.cast(correct_pre3, tf.float32))

saver = tf.train.Saver()


with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess,coord=coord)

    i_epoch = 0

    for i in range(LOOP_TIMES):
        b_image, b_label0, b_label1, b_label2, b_label3 = sess.run(
            [image_batch, label0_batch, label1_batch, label2_batch, label3_batch])

        logits0_, logits1_, logits2_, logits3_ = sess.run([logits0, logits1, logits2, logits3], feed_dict={x:b_image})

        sess.run(optimizer, feed_dict={x:b_image,
                                       y0:b_label0,
                                       y1:b_label1,
                                       y2:b_label2,
                                       y3:b_label3})
        i_epoch_new = i//(5800/BATCH_SIZE) + 1
        if i_epoch != i_epoch_new:
            i_epoch = i_epoch_new
            if i_epoch%8 == 0:
                sess.run(tf.assign(lr,lr*0.5))

        if i%20 == 0:
            acc0, acc1, acc2, acc3, loss_ = sess.run([accuracy0, accuracy1,accuracy2, accuracy3,total_loss],
                                                     feed_dict={x:b_image,
                                                               y0:b_label0,
                                                               y1:b_label1,
                                                               y2:b_label2,
                                                               y3:b_label3})
            learning_rate = sess.run(lr)
            print("Iter:%d/%d epoch:%d,  Loss:%.3f  Accuracy:%.2f,%.2f,%.2f,%.2f  Learning_rate:%.5f" % (
                i, LOOP_TIMES, i_epoch, loss_, acc0, acc1, acc2, acc3, learning_rate))
        if acc0>0.9 and acc1>0.9 and acc2>0.9 and acc3>0.9 and i==LOOP_TIMES-1:
            saver.save(sess,'captcha/model/crack_captcha.model',global_step=i)

    coord.request_stop()
    coord.join(threads)