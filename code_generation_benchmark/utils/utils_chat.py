import base64
from datetime import datetime
import json
from openai import OpenAI
from google import genai
from google.genai import types
import anthropic
import os
import time
import logging
from pathlib import Path
from PIL import Image

from constants import *

my_logger = None

def get_logger(name=None, log_path=None):
    global my_logger
    if my_logger is not None:
        return my_logger
    assert name is not None, 'name should not be None'
    assert log_path is not None, 'log_path should not be None'
    my_logger = logging.getLogger(name)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', \
        handlers=[logging.FileHandler(filename=log_path, encoding='utf-8', mode='a+'), logging.StreamHandler()])
    return my_logger

def load_json(save_path, output=False):
    info_dict = {}
    if os.path.exists(save_path):
        with open(save_path, "r", encoding='utf-8') as f:
            info_dict = json.load(f)
    if output:
        print('already have', len(info_dict))
    return info_dict


def load_txt(save_path):
    assert os.path.exists(save_path), f'{save_path} not exist'
    info = ''
    if os.path.exists(save_path):
        with open(save_path, "r", encoding='utf-8') as f:
            info = f.read()
    return info


def safe_save_json(info_dict, save_path, output=False):
    while True:
        try:
            with open(save_path, "w", encoding='utf-8') as f:
                json.dump(info_dict, f, indent=2, ensure_ascii=False)
            break
        except Exception as e:
            time.sleep(1)
            print('----------save error:', str(e))
            print('----------do not interrupt saving, retrying...')
    if output:
        print(f'--------------------save success,', len(info_dict), 'saved')

def get_client(name=None):
    if 'claude' in name:
        return get_client_claude()
    if 'gemini' in name:
        return get_client_gemini()
    if 'intern' in name:
        return get_client_internvl()
    return get_client_openai()

def get_client_openai():
    client = OpenAI(
        api_key=APIS['openai']['API_KEY'],
        base_url=APIS['openai']['BASE_URL'],
    )
    return client

def get_client_gemini():
    client = genai.Client(
        api_key=APIS['gemini']['API_KEY'],
        http_options={"base_url": APIS['gemini']['BASE_URL']},
    )
    return client

def get_client_claude():
    client = anthropic.Anthropic(
        api_key=APIS['claude']['API_KEY'],
        base_url=APIS['claude']['BASE_URL'],
    )
    return client

def get_client_internvl():
    client = OpenAI(
        api_key=APIS['intern']['API_KEY'],
        base_url=APIS['intern']['BASE_URL'],
    )
    return client


def ask_question_with_image(image_path: Path, setting_name, model_type):
    max_tokens = VLM_PARAMS['max_tokens']
    thinking_budget = VLM_PARAMS['thinking_budget']
    temperature = VLM_PARAMS['temperature']
    top_p = VLM_PARAMS['top_p']
    prompt_template = CHAT_PROMPT_FILE

    my_logger.info(f'*** max_tokens: {max_tokens}')
    my_logger.info(f'*** thinking budget: {thinking_budget}')
    my_logger.info(f'*** prompt_template: {prompt_template}')
    if not max_tokens:
        my_logger.info('!!! param max_tokens unset')
    question = load_txt(prompt_template)

    if '{{TABLE}}' in question:
        my_logger.info(f'### Adding table ###')
        question = question.replace('{{TABLE}}', \
            json.dumps(load_json(image_path.parent / 'data.json')["data"], indent=2, ensure_ascii=False))
    if max_tokens:
        question = question.replace('## Constraints:', f'## Constraints:\n- Output Limit: Your output must be concise, self-contained, and strictly limited to {max_tokens} tokens.')
    if thinking_budget > 0:
        thinking_prompt = question.replace('## Constraints:', f'## Constraints:\n- Thinking Budget: You must use no more than {thinking_budget} tokens in internal reasoning before producing the output.')
    else:
        thinking_prompt = question.replace('## Constraints:', f'## Constraints:\n- Thinking Budget: You should not conduct internal reasoning. Please produce the output directly.')
    cost_save_path = image_path.parent / setting_name / f'{setting_name}_cost.json'

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    image_pil = Image.open(image_path)

    # client = get_client(model_type)
    
    if 'gemini-2.5-flash' in model_type:
        client = get_client_gemini()
        if not max_tokens:
            max_tokens = 16384
        response = client.models.generate_content(
            model=model_type,
            contents=[
                thinking_prompt,
                image_pil,
            ],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
                temperature=temperature,
                max_output_tokens=max_tokens+thinking_budget,
                top_p=top_p,
            ),
        )
        safe_save_json(response.usage_metadata.model_dump(), cost_save_path)
        my_logger.info(f'{setting_name} {image_path.parent.name} {response.usage_metadata.model_dump()}')
        return response.text
    elif 'claude-3-7-sonnet' in model_type:
        client = get_client_claude()
        if not max_tokens:
            max_tokens = 16384
        response = client.messages.create(
            model=model_type,
            max_tokens=max_tokens+thinking_budget,
            temperature=1.0,  # may only be set to 1 when thinking is enabled
            thinking={
                "type": "enabled",
                "budget_tokens": thinking_budget
            },
            messages=[{
                "role": "user", "content": 
                [{"type": "text", "text": thinking_prompt},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": f"{base64_image}"}}],
            }],
        )
        safe_save_json(response.usage.model_dump(), cost_save_path)
        my_logger.info(f'{setting_name} {image_path.parent.name} {response.usage.model_dump()}')
        reply_text = "".join(block.text for block in response.content if block.type == "text")
        return reply_text
    else:
        if 'internvl' in model_type:
            client = get_client_internvl()
        else:
            client = get_client_openai()
        args = {
            "model": model_type,
            "temperature": temperature,
            "top_p": top_p,
            "messages": [{
                "role": "user", "content": 
                [{"type": "text", "text": question},
                 {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}],
            }],
        }
        if model_type in ['o4-mini', 'o3', 'o1']:
            if max_tokens:
                args['max_completion_tokens'] = max_tokens+thinking_budget
            else:
                args['max_completion_tokens'] = 16384+thinking_budget
            args['messages'][0]['content'][0]['text'] = thinking_prompt
        elif 'gemini-2.5-pro' in model_type:
            if max_tokens:
                args['max_tokens'] = max_tokens+thinking_budget
            args['messages'][0]['content'][0]['text'] = thinking_prompt
        else:
            if max_tokens:
                args['max_tokens'] = max_tokens
            else:
                if model_type == 'moonshot-v1-32k-vision-preview':
                    args['max_tokens'] = 16384

        chat_completion = client.chat.completions.create(**args)
        if chat_completion.choices is None:
            return None
        if chat_completion.usage is not None:
            safe_save_json(chat_completion.usage.model_dump(), cost_save_path)
            my_logger.info(f'{setting_name} {image_path.parent.name} {chat_completion.usage.model_dump()}')
        return chat_completion.choices[0].message.content
