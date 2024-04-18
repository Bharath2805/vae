# -*- coding: utf-8 -*-
"""VAE (3) (1).ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/15X50-JwL0whC9eWbX17VTvOodWDFgvLE
"""





from google.colab import drive
drive.mount('/content/drive')



import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, losses, optimizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Parameters
img_height = 128
img_width = 128
batch_size = 32
latent_dim = 50  # Dimensionality of the latent space
image_folder = '/content/sample_data/jpeg'  # Path to the folder containing images

# Data loading and preprocessing
datagen = ImageDataGenerator(rescale=1./255)
train_generator = datagen.flow_from_directory(
    image_folder,
    target_size=(img_height, img_width),
    batch_size=batch_size,
    class_mode=None,
    shuffle=True
)

# Define the encoder
encoder_inputs = layers.Input(shape=(img_height, img_width, 3))
x = layers.Conv2D(32, 3, activation="relu", strides=2, padding="same")(encoder_inputs)
x = layers.Conv2D(64, 3, activation="relu", strides=2, padding="same")(x)
x = layers.Flatten()(x)
x = layers.Dense(16, activation="relu")(x)
z_mean = layers.Dense(latent_dim, name="z_mean")(x)
z_log_var = layers.Dense(latent_dim, name="z_log_var")(x)

# Reparameterization trick to sample from the learned distribution
def sampling(args):
    z_mean, z_log_var = args
    batch = tf.shape(z_mean)[0]
    dim = tf.shape(z_mean)[1]
    epsilon = tf.keras.backend.random_normal(shape=(batch, dim))
    return z_mean + tf.exp(0.5 * z_log_var) * epsilon

z = layers.Lambda(sampling)([z_mean, z_log_var])

# Define the encoder model
encoder = models.Model(encoder_inputs, [z_mean, z_log_var, z], name="encoder")

# Define the decoder
latent_inputs = layers.Input(shape=(latent_dim,))
x = layers.Dense(8 * 8 * 64, activation="relu")(latent_inputs)
x = layers.Reshape((8, 8, 64))(x)
x = layers.Conv2DTranspose(64, 3, activation="relu", strides=2, padding="same")(x)
x = layers.Conv2DTranspose(32, 3, activation="relu", strides=2, padding="same")(x)
x = layers.Conv2DTranspose(32, 3, activation="relu", strides=2, padding="same")(x)
x = layers.Conv2DTranspose(32, 3, activation="relu", strides=2, padding="same")(x)  # Adjusted
decoder_outputs = layers.Conv2DTranspose(3, 3, activation="sigmoid", padding="same")(x)

# Define the decoder model
decoder = models.Model(latent_inputs, decoder_outputs, name="decoder")

# Define the VAE model
outputs = decoder(encoder(encoder_inputs)[2])
vae = models.Model(encoder_inputs, outputs, name="vae")

# VAE Loss
reconstruction_loss = losses.binary_crossentropy(encoder_inputs, outputs) * img_height * img_width
kl_loss = -0.5 * (1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var))
kl_loss = tf.reduce_mean(tf.reduce_sum(kl_loss, axis=1))
vae_loss = reconstruction_loss + kl_loss
vae.add_loss(vae_loss)

# Compile the VAE model
vae.compile(optimizer=optimizers.Adam())

# Train the VAE model
vae.fit(train_generator, epochs=10, steps_per_epoch=200)





!pip install torch torchvision

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.utils import save_image
import os

# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Hyper-parameters
batch_size = 32
latent_dim = 50
img_size = 128

# Create a directory to save generated images
sample_dir = 'samples'
if not os.path.exists(sample_dir):
    os.makedirs(sample_dir)

# Custom dataset class
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, root, transform=None):
        self.root = root
        self.transform = transform
        self.images = os.listdir(root)

    def __getitem__(self, index):
        img_path = os.path.join(self.root, self.images[index])
        image = Image.open(img_path).convert('RGB')

        if self.transform is not None:
            image = self.transform(image)

        return image

    def __len__(self):
        return len(self.images)

# Data transforms
transform = transforms.Compose([
    transforms.Resize((img_size, img_size)),
    transforms.ToTensor(),
])

# Load custom dataset
dataset = CustomDataset(root='/content/sample_data/jpeg', transform=transform)

# Create data loader
data_loader = DataLoader(dataset=dataset, batch_size=batch_size, shuffle=True)

# Define the VAE model
class VAE(nn.Module):
    def __init__(self):
        super(VAE, self).__init__()

        # Encoder
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(64*32*32, 256),
            nn.ReLU(),
            nn.Linear(256, latent_dim * 2)  # Two outputs for mean and log variance
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 64*32*32),
            nn.ReLU(),
            nn.Unflatten(1, (64, 32, 32)),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(32, 3, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid()  # Output range [0, 1]
        )

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        # Encode
        z_params = self.encoder(x)
        mu, logvar = torch.chunk(z_params, 2, dim=1)
        z = self.reparameterize(mu, logvar)

        # Decode
        reconstruction = self.decoder(z)
        return reconstruction, mu, logvar

# Create the VAE model
model = VAE().to(device)

# Loss function
def loss_function(reconstruction, target, mu, logvar):
    BCE = nn.functional.binary_cross_entropy(reconstruction, target, reduction='sum')
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return BCE + KLD

# Optimizer
optimizer = optim.Adam(model.parameters(), lr=1e-3)

# Training
num_epochs = 1000
for epoch in range(num_epochs):
    for batch_idx, data in enumerate(data_loader):
        img = data.to(device)

        # Forward pass
        reconstruction, mu, logvar = model(img)

        # Compute loss
        loss = loss_function(reconstruction, img, mu, logvar)

        # Backward pass and optimization
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch_idx % 100 == 0:
            print('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}'
                  .format(epoch+1, num_epochs, batch_idx+1, len(data_loader), loss.item()))

    # Save generated images
    with torch.no_grad():
        z = torch.randn(batch_size, latent_dim).to(device)
        generated_images = model.decoder(z).cpu()
        save_image(generated_images, os.path.join(sample_dir, 'generated_images-{}.png'.format(epoch+1)))

# Save the trained model
torch.save(model.state_dict(), 'vae_model.pth')



"""**working code**

"""

!pip install Pillow

from PIL import Image

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.utils import save_image
import os

# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Hyper-parameters
batch_size = 64
latent_dim = 100
img_size = 64
learning_rate = 1e-4
num_epochs = 2000

# Create a directory to save generated images
sample_dir = 'samples'
if not os.path.exists(sample_dir):
    os.makedirs(sample_dir)

# Custom dataset class
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, root, transform=None):
        self.root = root
        self.transform = transform
        self.images = os.listdir(root)

    def __getitem__(self, index):
        img_path = os.path.join(self.root, self.images[index])
        image = Image.open(img_path).convert('RGB')

        if self.transform is not None:
            image = self.transform(image)

        return image

    def __len__(self):
        return len(self.images)

# Data transforms
transform = transforms.Compose([
    transforms.Resize((img_size, img_size)),
    transforms.ToTensor(),
])

# Load custom dataset
dataset = CustomDataset(root='/content/sample_data/dataset', transform=transform)

# Create data loader
data_loader = DataLoader(dataset=dataset, batch_size=batch_size, shuffle=True)

# Define the VAE model
class VAE(nn.Module):
    def __init__(self):
        super(VAE, self).__init__()

        # Encoder
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(128*8*8, 1024),
            nn.ReLU(),
            nn.Linear(1024, latent_dim * 2)  # Two outputs for mean and log variance
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 1024),
            nn.ReLU(),
            nn.Linear(1024, 128*8*8),
            nn.ReLU(),
            nn.Unflatten(1, (128, 8, 8)),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(32, 3, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid()  # Output range [0, 1]
        )

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        # Encode
        z_params = self.encoder(x)
        mu, logvar = torch.chunk(z_params, 2, dim=1)
        z = self.reparameterize(mu, logvar)

        # Decode
        reconstruction = self.decoder(z)
        return reconstruction, mu, logvar

# Create the VAE model
model = VAE().to(device)

# Loss function
def loss_function(reconstruction, target, mu, logvar):
    BCE = nn.functional.binary_cross_entropy(reconstruction, target, reduction='sum')
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return BCE + KLD

# Optimizer
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

# Training
for epoch in range(num_epochs):
    for batch_idx, data in enumerate(data_loader):
        img = data.to(device)

        # Forward pass
        reconstruction, mu, logvar = model(img)

        # Compute loss
        loss = loss_function(reconstruction, img, mu, logvar)

        # Backward pass and optimization
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch_idx % 100 == 0:
            print('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}'
                  .format(epoch+1, num_epochs, batch_idx+1, len(data_loader), loss.item()))

    # Save generated images
    with torch.no_grad():
        z = torch.randn(batch_size, latent_dim).to(device)
        generated_images = model.decoder(z).cpu()
        save_image(generated_images, os.path.join(sample_dir, 'generated_images-{}.png'.format(epoch+1)))

# Save the trained model
torch.save(model.state_dict(), 'vae_model.pth')





# Save generated images
    with torch.no_grad():
        z = torch.randn(batch_size, latent_dim).to(device)
        generated_images = model.decoder(z).cpu()
        save_image(generated_images, os.path.join(sample_dir, 'generated_images-{}.png'.format(epoch+1)))

# Save the trained model
torch.save(model.state_dict(), '/content/sample_data/vae_model1.pth')







"""Model -3"""









for filename in train_generator.filenames:
    print(filename)









