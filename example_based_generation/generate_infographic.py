import os
import pandas as pd
import openai
import requests
from pathlib import Path
import time
import json
from typing import List, Dict, Optional
from PIL import Image
import base64
import numpy as np
import cv2
from io import BytesIO

API_KEY = "YOUR_API_KEY"
BASE_URL = "YOUR_OPENAI_SERVER_URL"

class InfographicImageGenerator:
    def __init__(self):
        """
        Initialize image generator
        
        Args:
            api_key: OpenAI API key
            base_url: Optional API base URL for custom endpoint
        """
        self.client = openai.OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        self.processed_data_dir = "processed_data"
        self.output_dir = "generated_images"
        self.prompts_dir = "."
        
        # Create output directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/titles", exist_ok=True)
        os.makedirs(f"{self.output_dir}/pictograms", exist_ok=True)
        # Coming Soon directories
        os.makedirs(f"{self.output_dir}/chart_variations", exist_ok=True)
        os.makedirs(f"{self.output_dir}/final_infographics", exist_ok=True)
        
    def load_prompt_file(self, filename: str) -> str:
        """Load prompt file content"""
        prompt_path = os.path.join(self.prompts_dir, filename)
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Cannot find prompt file {filename}")
            return ""
    
    def read_csv_data(self, csv_path: str) -> str:
        """Read CSV file and convert to string format"""
        try:
            df = pd.read_csv(csv_path)
            # Convert CSV data to string format, including column names and first few rows of data
            csv_content = f"Columns: {', '.join(df.columns.tolist())}\n"
            csv_content += f"Data shape: {df.shape[0]} rows, {df.shape[1]} columns\n"
            csv_content += "Sample data:\n"
            csv_content += df.head(10).to_string(index=False)
            return csv_content
        except Exception as e:
            print(f"Failed to read CSV file {csv_path}: {e}")
            return ""
    
    def generate_title_text(self, csv_data: str) -> str:
        """Generate title text using GPT-4"""
        try:
            # Load title recommendation prompt
            title_prompt_template = self.load_prompt_file("generate_title_recommendation_prompt.md")
            if not title_prompt_template:
                return "Data Analysis Report"
            
            # Replace CSV data placeholder
            prompt = title_prompt_template.replace("{csv_data}", csv_data)
            
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            title = response.choices[0].message.content.strip()
            print(f"Generated title: {title}")
            return title
            
        except Exception as e:
            print(f"Failed to generate title text: {e}")
            return "Data Insights"
    
    def generate_image_prompt(self, title: str, prompt_type: str) -> str:
        """Generate image generation prompt"""
        try:
            if prompt_type == "title":
                # Read title prompt file and use GPT-4.1 to generate professional image prompt
                title_prompt_template = self.load_prompt_file("generate_title_image_prompt.md")
                title_prompt = title_prompt_template.replace("{title}", title)
                response = self.client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "user", "content": title_prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                
                prompt = response.choices[0].message.content.strip()
                print(f"Generated title image prompt: {prompt}...")
                
            elif prompt_type == "pictogram":
                # Read pictogram prompt file and use GPT-4.1 to generate professional image prompt
                pictogram_prompt_template = self.load_prompt_file("generate_pictogram_prompt.md")
                pictogram_prompt = pictogram_prompt_template.replace("{title}", title)
                response = self.client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "user", "content": pictogram_prompt}
                    ],
                )
                prompt = response.choices[0].message.content.strip()
                print(f"Generated pictogram image prompt: {prompt}...")
            
            return prompt
            
        except Exception as e:
            print(f"Failed to generate image prompt: {e}")
            return f"Create a simple {prompt_type} image about {title}"
    
    def generate_image(self, prompt: str, image_type: str, filename: str) -> bool:
        """Generate image using GPT-Image-1"""
        try:
            print(f"Generating {image_type} image: {filename}")
            
            response = self.client.images.generate(
                model="gpt-image-1", 
                prompt=prompt,
                n=1,
                size="1024x1024",
                quality="high",
            )
            
            if response and response.data:
                image_base64 = response.data[0].b64_json
                image_data = base64.b64decode(image_base64)
                image= Image.open(BytesIO(image_data))
                # Convert to RGBA mode
                image = image.convert('RGBA')
                data = image.getdata()
                
                # Convert white (tolerance 20) to transparent
                new_data = []
                for item in data:
                    # Check if RGB value is close to white (tolerance 20)
                    if item[0] > 235 and item[1] > 235 and item[2] > 235:
                        new_data.append((255, 255, 255, 0))
                    else:
                        new_data.append(item)
                        
                image.putdata(new_data)

                # Convert image to numpy array
                img_array = np.array(image)
                
                # Create binary mask, non-transparent pixels are 1, transparent pixels are 0
                mask = (img_array[:,:,3] > 0).astype(np.uint8)
                
                # Mark connected regions
                num_labels, labels = cv2.connectedComponents(mask)
                
                # Calculate number of pixels in each connected region
                for label in range(1, num_labels):
                    area = np.sum(labels == label)
                    # If region pixel count is less than 20, set it to transparent
                    if area < 20:
                        img_array[labels == label] = [255, 255, 255, 0]
                        
                # Convert back to PIL image
                image = Image.fromarray(img_array)

                image.save(filename)
                print(f"Image saved: {filename}")
                return True

            else:
                print(f"Failed to generate image: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Failed to generate image: {e}")
            return False
    
    def process_csv_file(self, csv_file: str):
        """Process a single CSV file"""
        print(f"\nProcessing CSV file: {csv_file}")
        
        # Read CSV data
        csv_path = os.path.join(self.processed_data_dir, csv_file)
        csv_data = self.read_csv_data(csv_path)
        
        if not csv_data:
            print(f"Skipping file {csv_file} - read failed")
            return
        
        base_filename = os.path.splitext(csv_file)[0]
        
        # Generate 4 images
        for i in range(4):
            print(f"\nGenerating {i+1} set of images...")

            # Generate title text
            title_text = self.generate_title_text(csv_data)
        
            # Generate title image
            title_prompt = self.generate_image_prompt(title_text, "title")
            title_filename = f"{self.output_dir}/titles/{base_filename}_title_{i+1}.png"
            
            success = self.generate_image(title_prompt, "title", title_filename)
            if success:
                # Add delay to avoid API limits
                time.sleep(2)
            
            # Generate pictogram image
            pictogram_prompt = self.generate_image_prompt(title_text, "pictogram")
            pictogram_filename = f"{self.output_dir}/pictograms/{base_filename}_pictogram_{i+1}.png"
            
            success = self.generate_image(pictogram_prompt, "pictogram", pictogram_filename)
            if success:
                # Add delay to avoid API limits
                time.sleep(2)
            
            # Coming Soon: generate chart variations and use layout template
    
    def process_all_csv_files(self):
        """Process all CSV files"""
        if not os.path.exists(self.processed_data_dir):
            print(f"Error: Cannot find directory {self.processed_data_dir}")
            return
        
        csv_files = [f for f in os.listdir(self.processed_data_dir) if f.endswith('.csv')]
        
        if not csv_files:
            print(f"No CSV files found in {self.processed_data_dir}")
            return
        
        print(f"Found {len(csv_files)} CSV files")
        
        for csv_file in csv_files:
            try:
                self.process_csv_file(csv_file)
            except Exception as e:
                print(f"Error processing file {csv_file}: {e}")
                continue

def main():
    """Main function"""
    print("=== Infographic Generator ===")
    
    # Create generator and start processing
    generator = InfographicImageGenerator()
    generator.process_all_csv_files()
    
    print("\n=== Processing completed ===")
    print(f"Generated images saved in: {generator.output_dir}")

if __name__ == "__main__":
    main() 
