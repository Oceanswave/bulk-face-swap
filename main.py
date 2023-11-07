import os
import re
import base64
import json
import random
import requests
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image

# Load environment variables
load_dotenv()

def get_random_subfolder(directory):
    subfolders = [f.path for f in os.scandir(directory) if f.is_dir()]
    return random.choice(subfolders) if subfolders else None

# Function to keep searching for random subfolders until an output folder does not exist.
def find_unique_subfolder(input_folder, output_folder):
    while True:
        random_input_subfolder = get_random_subfolder(input_folder)
        if random_input_subfolder:
            path_parts = os.path.normpath(random_input_subfolder).split(os.sep)[-2:]
            modified_output_folder = os.path.join(output_folder, *path_parts)
            
            if not os.path.exists(modified_output_folder):
                os.makedirs(modified_output_folder)
                return random_input_subfolder, modified_output_folder
        else:
            # No subfolders exist in the input folder
            return None, None

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def decode_image_from_base64(base64_string, output_path):
    image_data = base64.b64decode(base64_string)
    image = Image.open(BytesIO(image_data))
    image.save(output_path)

def numerical_sort_key(file_name):
    """ Extracts numbers from the filename and returns it to be used as a sorting key. """
    numbers = re.findall(r'\d+', file_name)
    return int(numbers[-1]) if numbers else 0

def resize_image_longest_edge_to_base64(input_path, size):
    with Image.open(input_path) as image:
        original_size = max(image.size)
        scale = size / float(original_size)
        new_size = tuple([int(x*scale) for x in image.size])
        # Resize the image
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Save the resized image to a bytes buffer
        buffer = BytesIO()
        resized_image.save(buffer, format=image.format)
        buffer.seek(0)

        # Encode the image to base64
        base64_string = base64.b64encode(buffer.read()).decode('utf-8')
    
    # Return a list that contains the base64 string
    return base64_string

def post_image(encoded_image, url, save_path, encoded_reference_image = None):
    headers = {'Content-Type': 'application/json'}
    data = {
        "image": encoded_image,
        "units": [
            {
                "source_img": encoded_reference_image,
                "blend_faces": False,
                "same_gender": True,
                "sort_by_size": True,
                "check_similarity": False,
                "compute_similarity": False,
                "min_sim": 0,
                "min_ref_sim": 0,
                "faces_index": [0],
                "reference_face_index": 0,
                "swapping_options": {
                #     "face_restorer_name": "codeformer",
                #     "restorer_visibility": 1,
                #     "codeformer_weight": 1,
                    "upscaler_name": "R-ESRGAN 4x+",
                #     "improved_mask": False,
                    "color_corrections": True,
                    "sharpen": True,
                #     "erosion_factor": 1
                },
                # "post_inpainting": {
                #     "inpainting_denoising_strengh": 0,
                #     "inpainting_prompt": "Portrait of a [gender]",
                #     "inpainting_negative_prompt": "",
                #     "inpainting_steps": 20,
                #     "inpainting_sampler": "Euler",
                #     "inpainting_model": "Current",
                #     "inpainting_seed": -1
                # }
            }
        ],
        "postprocessing": {
            "face_restorer_name": "codeformer",
            "restorer_visibility": 1,
            "codeformer_weight": 1,
            "upscaler_name": "R-ESRGAN 4x",
            "scale": 2,
            "upscaler_visibility": 1,
            "inpainting_when": "Never",
            # "inpainting_options": {
            #     "inpainting_denoising_strengh": 0,
            #     "inpainting_prompt": "Portrait of a [gender]",
            #     "inpainting_negative_prompt": "",
            #     "inpainting_steps": 20,
            #     "inpainting_sampler": "Euler a",
            #     "inpainting_when": "Never",
            #     "inpainting_model": "Current",
            #     "inpainting_seed": -1
            # }
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        response_json = json.loads(response.content)
        # Get the image data from the JSON
        image_data = response_json['images'][0]
        # Decode the image data
        decode_image_from_base64(image_data, save_path)
    else:
        print(f"Failed to post image: {response.status_code}")
        # Print the response content
        print(response.content)

def process_images(input_folder, output_folder, endpoint_url, encoded_reference_image = None):

    # List the image files
    image_names = os.listdir(input_folder)
    
    # Sort the list of image names based on the numerical value in the filename
    image_names.sort(key=numerical_sort_key)
    
    for image_name in image_names:
        if image_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"Processing image: {image_name}")
            image_path = os.path.join(input_folder, image_name)
            #encoded_image = encode_image_to_base64(image_path)
            encoded_image = resize_image_longest_edge_to_base64(image_path, 1024)
            save_path = os.path.join(output_folder, f"processed_{image_name}")
            post_image(encoded_image, endpoint_url, save_path, encoded_reference_image)

if __name__ == "__main__":
    input_folder = os.getenv('INPUT_FOLDER')
    output_folder = os.getenv('OUTPUT_FOLDER')
    reference_image_path = os.getenv('REFERENCE_IMAGE_PATH')
    endpoint_url = os.getenv('ENDPOINT_URL')

    # We need to ensure this directory exists before we proceed, as the execution environment is ephemeral.
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Pick a random subfolder from the input folder
    random_input_subfolder, modified_output_folder = find_unique_subfolder(input_folder, output_folder)

    print(f"Random input subfolder: {random_input_subfolder}")
    print(f"Modified output folder: {modified_output_folder}")

    if (reference_image_path is None or reference_image_path == "" or not os.path.exists(reference_image_path)):
        encoded_reference_image = None
    else :
        encoded_reference_image = encode_image_to_base64(reference_image_path)
    
    process_images(random_input_subfolder, modified_output_folder, endpoint_url, encoded_reference_image)