

import torch
import torch.nn as nn
import torch.nn.functional as F
from pytorch_pretrained import BertModel, BertTokenizer

class Config(object):

    def __init__(self, dataset):
        # 模型名称
        self.model_name="CtxtBERTCNN"
        # 训练集
        self.train_path = dataset + '/data/train.txt'
        # 校验集
        self.dev_path = dataset + '/data/dev.txt'
        # 测试集
        self.test_path = dataset + '/data/test.txt'
        #dataset
        self.datasetpkl = dataset + '/data/dataset.pkl'
        # 类别名单
        self.class_list = [ x.strip() for x in open(dataset + '/data/class.txt').readlines()]

        #模型保存路径
        self.save_path = dataset + '/saved_dict/' + self.model_name + '.ckpt'
        # 运行设备
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # 若超过1000bacth效果还没有提升，提前结束训练
        self.require_improvement= 20
        # 类别数量
        self.num_classes = len(self.class_list)
        # epoch数
        self.num_epochs = 30
        # batch_size
        self.batch_size = 16
        # 序列长度
        self.pad_size = 16
        # 学习率
        self.learning_rate = 1e-5
        # 预训练位置
        self.bert_path = './bert_pretrain'
        # bert的 tokenizer
        self.tokenizer = BertTokenizer.from_pretrained((self.bert_path))
        # Bert的隐藏层数量
        self.hidden_size = 768
        # 卷积核尺寸
        self.filter_sizes = (2,3,4)
        # 卷积核数量
        self.num_filters = 256
        # droptout
        self.dropout = 0.5

class Model(nn.Module):
    def __init__(self, config):
        super(Model, self).__init__()
        self.bert = BertModel.from_pretrained(config.bert_path)
        for param in self.bert.parameters():
            param.requires_grad = True

        self.convs = nn.ModuleList(
             [nn.Conv2d(in_channels=1, out_channels=config.num_filters, kernel_size=(k, config.hidden_size)) for k in config.filter_sizes]
        )
        self.position_embedding = nn.Embedding(config.pad_size, config.hidden_size)
        self.droptout = nn.Dropout(config.dropout)

        self.fc = nn.Linear(config.num_filters * len(config.filter_sizes), config.num_classes)

    def conv_and_pool(self, x, conv):
        x = conv(x)
        x = x.squeeze(3)
        size = x.size(2)
        x = F.max_pool1d(x, size)
        x = x.squeeze(2)
        return x


    def forward(self, x):

        context = x[0]
        positions = torch.arange(context.size(1), dtype=torch.long, device=context.device)
        relative_positions = positions.unsqueeze(0).expand(context.size(0), -1)
        position_embeddings = self.position_embedding(relative_positions)
        mask = x[2]
        encoder_out, pooled = self.bert(context, attention_mask = mask, output_all_encoded_layers = False) #shape [128,768]
        position_embeddings = position_embeddings.tolist()
        out = encoder_out.unsqueeze(1)+position_embeddings
        out = torch.cat([self.conv_and_pool(out, conv)for conv in self.convs], 1)
        out = self.droptout(out)
        out = self.fc(out)
        return out

























