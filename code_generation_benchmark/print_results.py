from collections import defaultdict, Counter
from pathlib import Path
import time
from utils.utils_chat import get_logger, load_json, safe_save_json
from constants import *

def print_table(logger, root_dir, model_types, save_path, eval_model='gpt-4.1-mini'):
    logger.info('*** print_table ***')
    logger.info(f'*** root_dir: {root_dir} ***')
    logger.info(f'*** eval_model: {eval_model} ***')
    data_cnt = 0
    res = {}
    summed_keys = ['area_matched','text','image','color','pos','size']
    for data_path in root_dir.iterdir():
        if not data_path.is_dir():
            continue
        data_cnt += 1
        res[data_path.name] = {}
        for mt in model_types:
            setting_name = mt.split('/')[-1]
            if not (data_path / setting_name / f'{setting_name}.html').exists():
                continue
            res[data_path.name][setting_name] = {}
            single_res = {
                'low': 0,
                'high': 0,
                'low_scores': {},
                'high_scores': {}
            }
            # execution fail
            if not (data_path / setting_name / f'{setting_name}.png').exists():
                continue
            if eval_model not in (high_level_results := load_json(data_path / setting_name / f'{setting_name}_model_scores.json')):
                logger.error(f'*** HIGH LEVEL EVAL({eval_model}) NOT FOUND: {setting_name} {data_path.name}')
            if not (data_path / setting_name / f'{setting_name}_scores.json').exists():
                logger.error(f'*** LOW LEVEL EVAL NOT FOUND: {setting_name} {data_path.name}')
            low_level_results = load_json(data_path / setting_name / f'{setting_name}_scores.json')
            if len(low_level_results):
                for k in summed_keys:
                    assert k in low_level_results, f'*** {k} not in {setting_name} {data_path.name} {low_level_results}'
                    single_res['low_scores'][k] = round(100 * low_level_results[k], 2)
                single_res['low'] = round(sum(single_res['low_scores'].values()) / len(summed_keys), 2)
            if eval_model in high_level_results:
                high_res = high_level_results[eval_model][-1]['score']
                single_res['high_scores'] = high_res
                single_res['high'] = high_res['total_score']
            res[data_path.name][setting_name] = single_res
    safe_save_json(res, save_path)
    logger.info(f'*** save to {save_path} ***')
    logger.info(f'*** data_cnt: {data_cnt} ***')

    output = {}
    comp_cnt = Counter()
    for mt in model_types:
        sname = mt.split('/')[-1]
        output[sname] = {}
        cc = defaultdict(list)
        for v in res.values():
            if sname not in v:
                continue
            comp_cnt[sname] += 1
            model_res = v[sname]
            if not len(model_res):
                continue
            for k, vv in model_res['low_scores'].items():
                cc[k].append(vv)
            cc['high_level'].append(model_res['high'])

        for k, v in cc.items():
            # If not finish, consider as a failure
            output[sname][k] = round(sum(v)/len(res), 2)
        if not comp_cnt[sname]:
            output.pop(sname)
            continue
        output[sname]['complete_rate'] = round(100 * comp_cnt[sname] / len(res), 2)
        # execution rate <= completion rate
        output[sname]['exec_rate'] = round(100 * len(cc['text']) / len(res), 2)
        output[sname]['low_level'] = round(sum([output[sname][k] if k in output[sname] else 0 for k in summed_keys]) / len(summed_keys), 2)
        output[sname]['overall'] = round((output[sname]['low_level'] + output[sname]['high_level']) / 2, 2)

    logger.info('*** all scores ***')
    all_keys = ['exec_rate'] + summed_keys + ['low_level', 'high_level', 'overall']
    model_types = [mt for mt in model_types if mt.split('/')[-1] in output]
    model_types = sorted(model_types, key=lambda x: output[x.split('/')[-1]]['overall'], reverse=True)
    for mt in model_types:
        sname = mt.split('/')[-1]
        logger.info(f'*** {sname} ***')
        for k in all_keys:
            if k in output[sname]:
                logger.info(f'--- {k}: {output[sname][k]:.2f}')
            else:
                logger.info(f'--- {k}: N/A')



if __name__ == '__main__':
    time_stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    logger = get_logger('main', LOG_DIR / f'eval_{time_stamp}.txt')
    save_path = Path(OUTPUT_DIR / f'results_{time_stamp}_table.json')
    save_path.parent.mkdir(parents=True, exist_ok=True)
    print_table(logger, ROOT_DIR, MODEL_TYPES, save_path, eval_model=EVAL_MODEL)
