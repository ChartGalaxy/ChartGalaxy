from PIL import Image
import torch
import numpy as np
import open_clip

from constants import CLIP_CACHE_DIR

class ImageEncoders:
    def __init__(self):
        print("Loading image encoders...")
        self.device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms('ViT-L-14-336', pretrained='openai', cache_dir=CLIP_CACHE_DIR, device=self.device)
    
    def clip_feat(self, pil_img: Image.Image) -> np.ndarray:
        image = self.clip_preprocess(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad(), torch.cuda.amp.autocast():
            image_features = self.clip_model.encode_image(image)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        return image_features[0].cpu().numpy()

image_encoders = None

def extract_image_feature(pil_img: Image.Image, model_type='clip') -> np.ndarray:
    global image_encoders
    if not image_encoders:
        image_encoders = ImageEncoders()
    if model_type == 'clip':
        return image_encoders.clip_feat(pil_img)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

def cal_cosine_dist(vec1, vec2):
    return (1 - np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))) / 2
