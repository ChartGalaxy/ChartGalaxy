import time
from utils.utils_chat import get_logger, ask_question_with_image, load_json, load_txt
from utils.utils_screenshot import get_driver, take_screenshot
from utils.utils_parse import parse_tree_from_html, convert_svg_to_html
from utils.utils_vis_bbox import vis_bboxes
from utils.utils_eval import compute_element_pairs, eval_scores, convert_tree_json
from utils.utils_judge import get_high_level_score
from pathlib import Path
import os

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from constants import *


def single_chat(logger, data_path, model_type, setting_name=None):
    if not setting_name:
        setting_name = model_type.split('/')[-1]
    model_dir = data_path / setting_name
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    if os.path.exists(model_dir / f'{setting_name}_raw.html') and \
        (html_len := len(load_txt(model_dir / f"{setting_name}_raw.html"))):
        logger.info(f'--------------------already have ({html_len}): {setting_name} {data_path.name}')
    else:
        save_path = model_dir / f'{setting_name}_raw.html'
        logger.info(f'--------------------start chat: {setting_name} {data_path.name}')
        result = ask_question_with_image(data_path / 'convert_chart.png', setting_name, model_type)
        if not result:
            logger.error(f'***** empty: {setting_name} {data_path.name}')
            return
        # write to html
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(result)
        if '```html' in result:
            pos = result.index('```html')
            while '```html' in result[pos+7:]:
                pos = result.index('```html', pos+7)
            if '\n```' not in result[pos+7:]:
                logger.error(f'***** not complete: {setting_name} {data_path.name}')
                return
            result = result[pos+7:result.index('\n```', pos+7)].strip()
        if '</html>' not in result:
            logger.error(f'***** </html> not found: {setting_name} {data_path.name}')
            return
        save_path = model_dir / f'{setting_name}.html'
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(result)
        logger.info(f'--------------------end chat({len(result)}): {setting_name} {data_path.name}')

def single_gt_convert(logger, data_path):
    logger.info(f'--------------------start gt visualize: {data_path.name}')
    driver = get_driver()
    # draw chart elements
    convert_svg_to_html(os.path.abspath(data_path / 'chart.svg'), data_path / 'convert_chart.html')
    take_screenshot(driver, os.path.abspath(data_path / 'convert_chart.html'))
    parse_tree_from_html(driver, os.path.abspath(data_path / 'convert_chart.html'))
    vis_bboxes(os.path.abspath(data_path / 'convert_chart.json'))
    convert_tree_json(logger, os.path.abspath(data_path / 'convert_chart.json'), 'gt')

def single_exp(logger, data_path, model_type, setting_name=None, eval_only=False, low_level=False, high_level=False, eval_model='gpt-4o-2024-11-20'):
    if not setting_name:
        setting_name = model_type.split('/')[-1]
    logger.info(f'****** start exp ******')
    logger.info(f'------ {setting_name} ------')
    logger.info(f'------ {data_path.name} ------')
    logger.info(f'------ eval_only: {eval_only} ------')
    logger.info(f'------ low_level: {low_level} ------')
    logger.info(f'------ high_level: {high_level} ------')
    if high_level:
        logger.info(f'------ eval_model: {eval_model} ------')
    driver = get_driver()

    # convert svg to html, png; parse tree and leafs
    if not os.path.exists(data_path / 'convert_chart_leafs.json'): 
        single_gt_convert(logger, data_path)

    model_dir = data_path / setting_name
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    # chat for code, 
    # output {setting_name}.html
    if not eval_only:
        try:
            single_chat(logger, data_path, model_type, setting_name)
        except Exception as e:
            logger.error(f'*** chat error: {setting_name} {data_path.name}')
            logger.error(str(e))
            return

    # parse tree from generated html code {setting_name}.html, 
    # output {setting_name}.json
    if (model_dir / f'{setting_name}.html').exists() and \
     len(load_txt(model_dir / f'{setting_name}.html')) > 0 and \
     not os.path.exists(model_dir / f'{setting_name}.json'):
        try:
            take_screenshot(driver, os.path.abspath(model_dir / f'{setting_name}.html'))
            logger.info(f'--------------------screenshot: {setting_name} {data_path.name}')
        except Exception as e:
            logger.error(f'*** screenshot error: {setting_name} {data_path.name}')
            logger.error(str(e))
            return
        try:
            parse_tree_from_html(driver, os.path.abspath(model_dir / f'{setting_name}.html'))
            logger.info(f'--------------------parse_tree_from_html: {setting_name} {data_path.name}')
            vis_bboxes(os.path.abspath(model_dir / f'{setting_name}.json'))
        except Exception as e:
            logger.error(f'*** parse tree error: {setting_name} {data_path.name}')
            logger.error(str(e))
            return

    # low level evaluation
    # use {setting_name}.json, 
    # output scores to {setting_name}_scores.json
    if low_level:
        if not (model_dir / f'{setting_name}.json').exists():
            logger.error(f'*** {setting_name} {data_path.name} json not exist')
            return
        if (model_dir / f'{setting_name}_scores.json').exists():
            logger.info(f'*** low level: {setting_name} {data_path.name} has done')
        else:
            try:
                convert_tree_json(logger, os.path.abspath(model_dir / f'{setting_name}.json'), 'pr')
                compute_element_pairs(logger, os.path.abspath(data_path / 'convert_chart.json'), os.path.abspath(model_dir / f'{setting_name}.json'))
                scores_dict = eval_scores(os.path.abspath(data_path / 'convert_chart.json'), os.path.abspath(model_dir / f'{setting_name}.json'))
                logger.info(f'*** {setting_name} {data_path.name} low level scores ***')
                for k, v in scores_dict.items():
                    if k == 'raw':
                        continue
                    logger.info(f'****** {k}: {v}')
            except Exception as e:
                logger.error(f'*** evaluate error: {setting_name} {data_path.name}')
                logger.error(str(e))

    # high level evaluation
    # use {setting_name}.png and convert_chart.png,
    # output scores to {setting_name}_model_scores.json
    if high_level and eval_model:
        if not (model_dir / f'{setting_name}.png').exists():
            logger.error(f'*** {setting_name} {data_path.name} png not exist')
            return
        if eval_model in load_json(model_dir / f'{setting_name}_model_scores.json'):
            logger.info(f'*** high level: {setting_name} {data_path.name} has done')
        else:
            try:
                ref_path = data_path / "convert_chart.png"
                gen_path = model_dir / f"{setting_name}.png"
                assert ref_path.exists() and gen_path.exists(), f"File not found: {ref_path} or {gen_path}"        
                scores = get_high_level_score(ref_path, gen_path, eval_model)
                logger.info(f'*** {setting_name} {data_path.name} high level scores by {eval_model} ***')
                for k, v in scores.items():
                    if isinstance(v, dict):
                        logger.info(f'**** {k}: {v["score"]}')
                    else:
                        logger.info(f'****** {k}: {v}')
            except Exception as e:
                logger.error(f'*** high level evaluate error: {setting_name} {data_path.name}')
                logger.error(str(e))

file_lock = threading.Lock()

def process_chat_task(logger, task):
    data_path = Path(task['data_path'])
    model_type = task['model_type']
    setting_name = task['setting_name']
    try:
        single_chat(logger, data_path, model_type, setting_name)
    except Exception as e:
        logger.error(f'*** chat error: {setting_name} {data_path.name}')
        logger.error(str(e))

def do_eval(logger, task):
    data_path = Path(task['data_path'])
    model_type = task['model_type']
    setting_name = task['setting_name']
    with file_lock:
        single_exp(logger, data_path, model_type, setting_name=setting_name, eval_only=True, low_level=True, high_level=True, eval_model=EVAL_MODEL)

def judge_need_to_chat(model_dir: Path):
    sname = model_dir.name
    return not model_dir.exists() or \
        not (model_dir / f'{sname}_raw.html').exists()

def main_chat_multiprocess(logger, root_dir):
    model_types = MODEL_TYPES

    tasks = []
    for data_path in root_dir.iterdir():
        for mt in model_types:
            setting_name = mt.split('/')[-1]
            if not judge_need_to_chat(data_path / setting_name):
                continue
            tasks.append({
                'id': len(tasks),
                'data_path': data_path,
                'model_type': mt,
                'setting_name': setting_name
            })
    logger.info(f'*** TOTAL {len(tasks)} tasks to do ***')
    time.sleep(15)

    # parse gt charts 
    for data_path in root_dir.iterdir():
        if not os.path.exists(data_path / 'convert_chart_leafs.json'): 
            single_gt_convert(logger, data_path)

    with ThreadPoolExecutor(max_workers=N_WORKERS) as executor:
        future_to_item = {executor.submit(process_chat_task, logger, task): task for task in tasks}

        for future in as_completed(future_to_item):
            task = future_to_item[future]
            try:
                do_eval(logger, task)
                logger.info(f'*** task {task["id"]} done ***')
            except Exception as exc:
                logger.error(f'{task["setting_name"]} {task["data_path"]} generated an exception: {exc}')

def main(logger, root_dir):
    main_chat_multiprocess(logger, root_dir)


if __name__ == '__main__':
    logger = get_logger('main', LOG_DIR / f'log_{time.strftime("%Y%m%d_%H%M%S", time.localtime())}.txt')
    logger.info('*** Experiment settings ***')
    logger.info(f'*** root_dir: {ROOT_DIR} ***')
    logger.info(f'*** log_dir: {LOG_DIR} ***')
    logger.info(f'*** eval_model: {EVAL_MODEL} ***')
    logger.info(f'*** n_workers: {N_WORKERS} ***')
    logger.info(f'*** VLM_PARAMS: ***')
    for k, v in VLM_PARAMS.items():
        logger.info(f'--- {k}: {v}')
    logger.info(f'*** MODELS: ***')
    for v in MODEL_TYPES:
        logger.info(f'--- {v}')
    logger.info(f'*** HIGH_LEVEL_EVAL: {HIGH_LEVEL_EVAL_PROMPT_FILE} ***')
    logger.info(f'*** CHAT_PROMPT_FILE: {CHAT_PROMPT_FILE} ***')

    main(logger, ROOT_DIR)
