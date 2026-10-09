import sys
import numpy as np
from PIL import Image

# Create 4x4 grayscale noise texture for Mica-like effect
np.random.seed(42)
noise = np.random.randint(180, 230, (4, 4), dtype=np.uint8)

img = Image.fromarray(noise, mode='L')
out = sys.argv[1] if len(sys.argv) > 1 else 'D:/ASTRA/jarvis-ai-assistant/assets/textures/noise-4x4.png'
img.save(out)
print('Noise texture saved to:', out)