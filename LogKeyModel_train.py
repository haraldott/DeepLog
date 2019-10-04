import torch
import torch.nn as nn
import torch.optim as optim
from tensorboardX import SummaryWriter
from torch.utils.data import TensorDataset, DataLoader
import argparse
import os
import pandas as pd

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# Hyperparameters
window_size = 10
input_size = 1
hidden_size = 64
num_layers = 2
num_classes = 43
num_epochs = 300
batch_size = 2048
model_dir = 'model'
log = 'Adam_batch_size=' + str(batch_size) + ';epoch=' + str(num_epochs)

# def generate(name):
#     num_sessions = 0
#     inputs = []
#     outputs = []
#     with open('data/' + name, 'r') as f:
#         for line in f.readlines():
#             if num_sessions < 10:
#                 print(line)
#             num_sessions += 1
#             line = tuple(map(lambda n: n - 1, map(int, line.strip().split())))
#             for i in range(len(line) - window_size):
#                 if num_sessions < 10:
#                     print(line[i:i + window_size])
#                 inputs.append(line[i:i + window_size])
#                 outputs.append(line[i + window_size])
#     print('Number of sessions({}): {}'.format(name, num_sessions))
#     print('Number of seqs({}): {}'.format(name, len(inputs)))
#     print('Output {}, Input {}'.format(len(outputs), len(inputs)))
#     print(inputs)
#     dataset = TensorDataset(torch.tensor(inputs, dtype=torch.float), torch.tensor(outputs))
#     return dataset


def generate(name):
    inputs = []
    outputs = []
    structured = pd.read_csv(
        'openstack_val_normal_n2_structured.csv')

    for i in range(len(structured["EventId"].values) - window_size):
        inputs.append(structured["EventId"].values[i:i + window_size])
        outputs.append(structured["EventId"].values[i + window_size])
    print('Number of seqs({}): {}'.format(name, len(inputs)))
    print('Output {}, Input {}'.format(len(outputs), len(inputs)))
    print()
    dataset = TensorDataset(torch.tensor(inputs, dtype=torch.float), torch.tensor(outputs))
    return dataset

class Model(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, num_keys):
        super(Model, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_keys)

    def forward(self, input):
        h0 = torch.zeros(self.num_layers, input.size(0), self.hidden_size).to(device)
        c0 = torch.zeros(self.num_layers, input.size(0), self.hidden_size).to(device)
        out, _ = self.lstm(input, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-num_layers', default=2, type=int)
    parser.add_argument('-hidden_size', default=64, type=int)
    parser.add_argument('-window_size', default=10, type=int)
    args = parser.parse_args()
    num_layers = args.num_layers
    hidden_size = args.hidden_size
    window_size = args.window_size

    model = Model(input_size, hidden_size, num_layers, num_classes).to(device)
    seq_dataset = generate('hdfs_train')
    dataloader = DataLoader(seq_dataset, batch_size=batch_size, shuffle=True, pin_memory=True)
    writer = SummaryWriter(logdir='log/' + log)

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters())

    # Train the model
    total_step = len(dataloader)
    for epoch in range(num_epochs):  # Loop over the dataset multiple times
        train_loss = 0
        for step, (seq, label) in enumerate(dataloader):
            # Forward pass
            seq = seq.clone().detach().view(-1, window_size, input_size).to(device)
            output = model(seq)
            loss = criterion(output, label.to(device))

            # Backward and optimize
            optimizer.zero_grad()
            loss.backward()
            train_loss += loss.item()
            optimizer.step()
        print('Epoch [{}/{}], Train_loss: {:.4f}'.format(epoch + 1, num_epochs, train_loss / len(dataloader.dataset)))
        writer.add_scalar('train_loss', train_loss / len(dataloader.dataset), epoch + 1)
    if not os.path.isdir(model_dir):
        os.makedirs(model_dir)
    torch.save(model.state_dict(), model_dir + '/' + log + 'part2.pt')
    writer.close()
    print('Finished Training')
