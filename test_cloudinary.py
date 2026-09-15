import cloudinary
import cloudinary.uploader
import os

cloudinary.config(cloud_name='dpe4f3bmh', api_key='164485736311586', api_secret='P-tZOOXXGCiVYZi1M__QHjGM74Q')

with open('test.txt', 'w') as f:
    f.write('hello')

try:
    print(cloudinary.uploader.upload('test.txt', resource_type='raw'))
except Exception as e:
    print(f"Error: {e}")
