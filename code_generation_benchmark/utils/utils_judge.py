import json
from utils.utils_chat import get_client, load_json, safe_save_json, get_logger, load_txt
import base64
from pathlib import Path
import os

from constants import *

def get_high_level_score(ref_path: Path, gen_path: Path, eval_model):
    logger = get_logger()
    question = load_txt(HIGH_LEVEL_EVAL_PROMPT_FILE)    
    if not os.path.exists(ref_path) or not os.path.exists(gen_path):
        logger.error(f"File not found: {ref_path} or {gen_path}")
        return
    client = get_client(eval_model)
    with open(ref_path, "rb") as image_file:
        ref_image = base64.b64encode(image_file.read()).decode('utf-8')
    with open(gen_path, "rb") as image_file:
        gen_image = base64.b64encode(image_file.read()).decode('utf-8')

    chat_completion = client.chat.completions.create(
        model=eval_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ref_image}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{gen_image}"}},
                ],
            }
        ],
        max_tokens=4096,
        temperature=0.0,
        top_p=1.0,
    )
    model_usage = chat_completion.usage
    try:
        res = chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in get_high_level_score: {e}")
        return
    try:
        if '```json' in res:
            pos = res.index('```json')
            res = res[pos + 7:res.index('```', pos + 7)].strip()
        res_dict = json.loads(res)
    except Exception as e:
        logger.error(str(e))
        logger.error(f"Error in parsing JSON response: {res}")
        return
    if 'total_score' not in res_dict:
        logger.error(f"Error in response with no total_score: {res}")
        return
    save_path = gen_path.parent / gen_path.name.replace('.png', '_model_scores.json')
    results = load_json(save_path)
    results[eval_model] = results.get(eval_model, [])
    results[eval_model].append({
        'usage': model_usage.model_dump(),
        'score': res_dict,
    })
    safe_save_json(results, save_path, output=False)
    return res_dict
