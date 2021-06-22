import torch
import torch.nn as nn
import torch.nn.functional as F




class TransmissionTimePredictor(nn.Module):
    def __init__(self,outputnum=21):
        super(TransmissionTimePredictor,self).__init__()

        self.hidden_1 = nn.Linear(62,64,bias=True)
        self.bn1 = nn.BatchNorm1d(64)
        self.hidden_2 = nn.Linear(64,64,bias=True)
        self.bn2 = nn.BatchNorm1d(64)

        self.output = nn.Linear(64,outputnum)

    def forward(self,x):
        assert x.shape[1] == 62, "wrong shape of input"
        out = self.hidden_1(x)
        out = F.relu(self.bn1(out))
        out = self.hidden_2(out)
        out = F.relu(self.bn2(out))

        out = self.output(out)
        out = F.softmax(out,dim=1)
        return out





