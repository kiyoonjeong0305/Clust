import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time
import copy
import random
from torch.utils.data import DataLoader, TensorDataset

from Clust.clust.transformation.type.DFToNPArray import transDFtoNP
from Clust.clust.ML.common.train import Train
from Clust.clust.ML.regression.models.fc import FC
from Clust.clust.ML.regression.models.rnn import RNN_model
from Clust.clust.ML.regression.models.cnn_1d import CNN_1D
from Clust.clust.ML.regression.models.lstm_fcn import LSTM_FCNs

class RegressionTrain(Train):
    
    def __init__(self):
        """

        """

        # seed 고정
        random_seed = 42
        torch.manual_seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        np.random.seed(random_seed)
        random.seed(random_seed)
        super().__init__()


    def set_param(self, param):
        """
        Set Parameter for train

        Args:
        param(dict): parameter for train


        Example:

            >>> param = { 'num_layers': 2, 
            ...           hidden_size': 64, 
            ...            'dropout': 0.1,
            ...            'bidirectional': True,
            ...            "lr":0.0001,
            ...            "device":"cpu",
            ...            "batch_size":16,
            ...            "n_epochs":10    }
            

        """
        self.parameter = param
        self.n_epochs = param['n_epochs']
        self.device = param['device']
        self.batch_size = param['batch_size']


    def set_data(self, train_x, train_y, val_x, val_y, window_num=0):
        """
        set train, val data & transform data for training

        Args:
            train_x (dataframe): train X data
            train_y (dataframe): train y data
            val_x (dataframe): validation X data
            val_y (dataframe): validation y data
            window_num (integer) : window size
        """
        train_x, train_y = transDFtoNP(train_x, train_y, window_num)
        val_x, val_y = transDFtoNP(val_x, val_y, window_num)

        self.parameter['input_size'] = train_x.shape[1]
        self.parameter['seq_len']  = train_x.shape[2] # seq_length

        self._set_train_val(train_x, train_y, val_x, val_y)


    def set_model(self, model_method):
        """
        Build model and return initialized model for selected model_name

        Args:
            model_method (string): model method name  
        """
        # build initialized model
        if model_method == 'LSTM_rg':
            self.init_model = RNN_model(
                rnn_type='lstm',
                input_size=self.parameter['input_size'],
                hidden_size=self.parameter['hidden_size'],
                num_layers=self.parameter['num_layers'],
                bidirectional=self.parameter['bidirectional'],
                device=self.parameter['device']
            )
        elif model_method == 'GRU_rg':
            self.init_model = RNN_model(
                rnn_type='gru',
                input_size=self.parameter['input_size'],
                hidden_size=self.parameter['hidden_size'],
                num_layers=self.parameter['num_layers'],
                bidirectional=self.parameter['bidirectional'],
                device=self.parameter['device']
            )
        elif model_method == 'CNN_1D_rg':
            self.init_model = CNN_1D(
                input_channels=self.parameter['input_size'],
                input_seq=self.parameter['seq_len'],
                output_channels=self.parameter['output_channels'],
                kernel_size=self.parameter['kernel_size'],
                stride=self.parameter['stride'],
                padding=self.parameter['padding'],
                drop_out=self.parameter['drop_out']
            )
        elif model_method == 'LSTM_FCNs_rg':
            self.init_model = LSTM_FCNs(
                input_size=self.parameter['input_size'],
                num_layers=self.parameter['num_layers'],
                lstm_drop_p=self.parameter['lstm_drop_out'],
                fc_drop_p=self.parameter['fc_drop_out']
            )
        elif model_method == 'FC_rg':
            self.init_model = FC(
                representation_size=self.parameter['input_size'],
                drop_out=self.parameter['drop_out'],
                bias=self.parameter['bias']
            )
        else:
            print('Choose the model correctly')


    def train(self):
        """
        Train model and return model

        Returns:
            model: train model
        """

        # train/validation DataLoader 구축
        self.train_loader = DataLoader(self.train_set, batch_size=self.batch_size, shuffle=True)
        self.valid_loader = DataLoader(self.valid_set, batch_size=self.batch_size, shuffle=True)

        print("Start training model")

        # train model
        init_model = self.init_model.to(self.device)

        data_loaders_dict = {'train': self.train_loader, 'val': self.valid_loader}
        criterion = nn.MSELoss()
        optimizer = optim.Adam(init_model.parameters(), lr=self.parameter['lr'])
        
        model = self._train_model(init_model, data_loaders_dict, criterion, self.n_epochs, optimizer, self.device)

        return model





    def _set_train_val(self, train_x, train_y, val_x, val_y):
        """
        set train, validation data to torch

        Args:
            train_x (dataframe): train X data
            train_y (dataframe): train y data
            val_x (dataframe): validation X data
            val_y (dataframe): validation y data

        """
        datasets = []
        for dataset in [(train_x, train_y), (val_x, val_y)]:
            x_data = np.array(dataset[0])
            y_data = dataset[1]
            datasets.append(TensorDataset(torch.Tensor(x_data), torch.Tensor(y_data)))
        
        self.train_set, self.valid_set = datasets[0], datasets[1]
        

    def _train_model(self, model, data_loaders, criterion, num_epochs, optimizer, device):
        """
        Train the model

        Args:
            model (dataframe): initialized model
            data_loaders (dictionary): train & validation data loaders
            criterion (criterion): loss function for training
            num_epochs (integer): the number of train epochs
            optimizer (optimizer): optimizer used in training
            device (string): device

        Returns:
            model (model) : trained model

        """

        since = time.time()

        val_mse_history = []

        best_model_wts = copy.deepcopy(model.state_dict())
        best_mse = 10000000

        for epoch in range(num_epochs):
            if epoch == 0 or (epoch + 1) % 10 == 0:
                print()
                print('Epoch {}/{}'.format(epoch + 1, num_epochs))

            # 각 epoch마다 순서대로 training과 validation을 진행
            for phase in ['train', 'val']:
                if phase == 'train':
                    model.train()  # 모델을 training mode로 설정
                else:
                    model.eval()   # 모델을 validation mode로 설정

                running_loss = 0.0
                running_total = 0

                # training과 validation 단계에 맞는 dataloader에 대하여 학습/검증 진행
                for inputs, labels in data_loaders[phase]:
                    inputs = inputs.to(device)
                    labels = labels.to(device, dtype=torch.float)
                    
                    # parameter gradients를 0으로 설정
                    optimizer.zero_grad()

                    # forward
                    # training 단계에서만 gradient 업데이트 수행
                    with torch.set_grad_enabled(phase == 'train'):
                        # input을 model에 넣어 output을 도출한 후, loss를 계산함
                        outputs = model(inputs)
                        outputs = outputs.squeeze(1)
                        loss = criterion(outputs, labels)

                        # backward (optimize): training 단계에서만 수행
                        if phase == 'train':
                            loss.backward()
                            optimizer.step()

                    # batch별 loss를 축적함
                    running_loss += loss.item() * inputs.size(0)
                    running_total += labels.size(0)

                # epoch의 loss 및 accuracy 도출
                epoch_loss = running_loss / running_total

                if epoch == 0 or (epoch + 1) % 10 == 0:
                    print('{} Loss: {:.4f}'.format(phase, epoch_loss))

                # validation 단계에서 validation loss가 감소할 때마다 best model 가중치를 업데이트함
                if phase == 'val' and epoch_loss < best_mse:
                    best_mse = epoch_loss
                    best_model_wts = copy.deepcopy(model.state_dict())
                if phase == 'val':
                    val_mse_history.append(epoch_loss)

        # 전체 학습 시간 계산
        time_elapsed = time.time() - since
        print('\nTraining complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
        print('Best val MSE: {:4f}'.format(best_mse))

        # validation loss가 가장 낮았을 때의 best model 가중치를 불러와 best model을 구축함
        model.load_state_dict(best_model_wts)
        return model     