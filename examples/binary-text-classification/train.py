import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import re
import os
from collections import Counter

DATA_DIR = "./dataset"
OUTPUT_PATH = "/output/model.pth"

# ------------------------------
# Dataset
# ------------------------------
class TextDataset(Dataset):
    def __init__(self, csv_path, vocab=None):
        self.data = pd.read_csv(csv_path)
        self.texts = self.data['text'].astype(str).tolist()
        self.labels = self.data['label'].astype(int).tolist()
        
        # Build vocab if not provided
        if vocab is None:
            self.vocab = self.build_vocab(self.texts)
        else:
            self.vocab = vocab

    def build_vocab(self, texts, min_freq=1):
        counter = Counter()
        for t in texts:
            tokens = self.tokenize(t)
            counter.update(tokens)
        vocab = {"<PAD>": 0, "<UNK>": 1}
        for word, freq in counter.items():
            if freq >= min_freq:
                vocab[word] = len(vocab)
        return vocab

    def tokenize(self, text):
        return re.findall(r"\b\w+\b", text.lower())

    def vectorize(self, text):
        tokens = self.tokenize(text)
        vec = torch.zeros(len(self.vocab))
        for tok in tokens:
            idx = self.vocab.get(tok, self.vocab["<UNK>"])
            vec[idx] += 1
        return vec

    def __getitem__(self, idx):
        text_vec = self.vectorize(self.texts[idx])
        label = torch.tensor(self.labels[idx], dtype=torch.long)
        return text_vec, label

    def __len__(self):
        return len(self.texts)


# ------------------------------
# Load Data
# ------------------------------
train_dataset = TextDataset(os.path.join(DATA_DIR, "train.csv"))
valid_dataset = TextDataset(os.path.join(DATA_DIR, "valid.csv"), vocab=train_dataset.vocab)
test_dataset = TextDataset(os.path.join(DATA_DIR, "test.csv"), vocab=train_dataset.vocab)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
valid_loader = DataLoader(valid_dataset, batch_size=16)
test_loader = DataLoader(test_dataset, batch_size=16)

num_classes = len(set(train_dataset.labels))
vocab_size = len(train_dataset.vocab)
print(f"Vocab size: {vocab_size}, Classes: {num_classes}")


# ------------------------------
# Model
# ------------------------------
class SimpleTextClassifier(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(SimpleTextClassifier, self).__init__()
        self.fc = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        return self.fc(x)


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = SimpleTextClassifier(vocab_size, num_classes).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)


# ------------------------------
# Training
# ------------------------------
num_epochs = 5
for epoch in range(num_epochs):
    model.train()
    total_loss = 0
    for x, y in train_loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        outputs = model(x)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * y.size(0)

    train_loss = total_loss / len(train_dataset)

    # Validation
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for x, y in valid_loader:
            x, y = x.to(device), y.to(device)
            outputs = model(x)
            loss = criterion(outputs, y)
            val_loss += loss.item() * y.size(0)
    val_loss /= len(valid_dataset)

    print(f"Epoch [{epoch+1}/{num_epochs}] Train Loss: {train_loss:.4f}  Val Loss: {val_loss:.4f}")


# ------------------------------
# Test Accuracy
# ------------------------------
model.eval()
correct = 0
total = 0
with torch.no_grad():
    for x, y in test_loader:
        x, y = x.to(device), y.to(device)
        outputs = model(x)
        _, predicted = torch.max(outputs, 1)
        total += y.size(0)
        correct += (predicted == y).sum().item()

acc = 100 * correct / total if total > 0 else 0
print(f"Test Accuracy: {acc:.2f}%")


# ------------------------------
# Save model
# ------------------------------
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
torch.save({
    'model_state_dict': model.state_dict(),
    'vocab': train_dataset.vocab,
    'num_classes': num_classes
}, OUTPUT_PATH)
print(f"Model saved to {OUTPUT_PATH}")
