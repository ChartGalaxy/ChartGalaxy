import base64
import json
import os
import time
import numpy as np
from PIL import Image
from pathlib import Path
from scipy.optimize import linear_sum_assignment

from utils.utils_chat import safe_save_json, load_json
from utils.utils_screenshot import crop_icon
from utils.utils_image_encoder import extract_image_feature
from utils.utils_scores import *
from utils.utils_vis_bbox import vis_bboxes_with_indexes

import re

def is_zero(value):
    pattern = r"^([-+]?\d*\.?\d+)(px|em|rem|%|vh|vw|pt|cm|mm|in|ex|ch|pc)?$"

    match = re.match(pattern, value.strip().lower())
    if match:
        number = float(match.group(1))
        if number == 0:
            return True
    return False

def box_area(box):
    # box = xyxy(4,n)
    return (box[2] - box[0]) * (box[3] - box[1])

def is_visible_xyxy(bbox):
    # check if the bbox is visible inside [0,1]
    assert len(bbox) == 4, 'bbox should be [x1, y1, x2, y2]'
    assert bbox[0] <= bbox[2], 'x1 should be less than x2'
    assert bbox[1] <= bbox[3], 'y1 should be less than y2'
    assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= 1 and bbox[3] <= 1
    return (bbox[2] > bbox[0] or bbox[3] > bbox[1]) and \
        bbox[0] < 1 and bbox[1] < 1 and bbox[2] > 0 and bbox[3] > 0

def xywh2xyxy(x):
    # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
    y = np.copy(x)
    if len(x.shape)==1:
        y[0] = x[0] - x[2] / 2  # top left x
        y[1] = x[1] - x[3] / 2  # top left y
        y[2] = x[0] + x[2] / 2  # bottom right x
        y[3] = x[1] + x[3] / 2  # bottom right y
        return y
    else:
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
        return y

def normalize_bbox(bbox, ref):
    xx, yy, ww, hh = ref['x'], ref['y'], ref['width'], ref['height']
    if isinstance(bbox, dict):
        x_min, y_min, x_max, y_max = bbox['x'], bbox['y'], bbox['x'] + bbox['width'], bbox['y'] + bbox['height']
    else:
        # assert False, 'Do not support this bbox format'
        x_min, y_min, x_max, y_max = bbox
    x_min = (x_min - xx) / ww
    y_min = (y_min - yy) / hh
    x_max = (x_max - xx) / ww
    y_max = (y_max - yy) / hh

    x_min = min(1, max(0, x_min))
    y_min = min(1, max(0, y_min))
    x_max = min(1, max(x_min, x_max))
    y_max = min(1, max(y_min, y_max))

    return [x_min, y_min, x_max, y_max]

def find_ele_in_tree(tree, ele_list, find_all=False, tag_name=None, class_name=None, id_name=None):
    if not find_all and ele_list:
        return ele_list
    flag = True
    if tag_name and tag_name != tree['tag']:
        flag = False
    if class_name and class_name not in tree['attributes'].get('class', []):
        flag = False
    if id_name and id_name != tree['attributes'].get('id', ''):
        flag = False
    if flag:
        ele_list.append(tree)
    for child in tree['children']:
        find_ele_in_tree(child, ele_list, find_all, tag_name, class_name, id_name)
    return ele_list

def parse_all_text_leafs(tree, ele_list):
    if not tree['children']:
        if 'text' in tree or tree['tag'] == 'text':
            ele_list.append(tree)
    for child in tree['children']:
        parse_all_text_leafs(child, ele_list)
    return ele_list

def get_tree_height(tree):
    if not tree['children']:
        return 1
    max_height = 0
    for child in tree['children']:
        max_height = max(max_height, get_tree_height(child))
    return max_height + 1

def judge_invalid_elements(ele):
    ref_group_name = ele['ref_group_name']
    tree = ele['node']
    # remove invisible elements
    if not is_visible_xyxy(tree['norm_bbox']):
        return False
    # remove opacity=0 elements
    if tree['computed_style']['opacity'] == "0":
        return False
    if not tree['children']:
        # remove rect with gradient fill
        if tree['computed_style']['fill'].startswith('url'):
            return False
        # hard code to remove the large background rect
        if tree['tag'] == 'rect' and \
            tree['norm_bbox'][2] - tree['norm_bbox'][0] > 0.8 and \
            tree['norm_bbox'][3] - tree['norm_bbox'][1] > 0.8:
            return False
        # remove invisible elements
        if tree['tag'] != 'image' and \
            (tree['computed_style']['fill'] == 'none' or tree['computed_style']['fill-opacity'] == "0") and \
            (tree['computed_style']['stroke'] == 'none' or tree['computed_style']['stroke-opacity'] == "0" or is_zero(tree['computed_style']['stroke-width'])):
            return False
        # remove <text> elements without text
        if tree['tag'] == 'text' and 'text' not in tree:
            return False
    if ref_group_name in ['image', 'icon-item']:
        if not (tree['norm_bbox'][2] > tree['norm_bbox'][0] and tree['norm_bbox'][3] > tree['norm_bbox'][1]):
            return False
    if tree['tag'] == 'image':
        for key in ['xlink:href', 'href']:
            if key in tree['attributes'] and tree['attributes'][key].startswith('https'):
                # remove the image with https
                return False
    return True

def parse_all_leafs(tree, ele_list, ref_group_name=""):
    # do not parse defs and stop elements
    if tree['tag'] in ['stop', 'defs']:
        return ele_list
    if not tree['children']:
        ele_list.append({
            'id': len(ele_list),
            'ref_group_name': ref_group_name,
            'node': tree
        })
        return ele_list

    ref_group_names = ['title', 'image', 'chart', 'legend', 'horizontal-axis', 'vertical-axis', 'axis-item', 'icon-item', 'legend-item', 'axis']
    # 'data-item', 'data-items', 
    if tree['tag'] == 'g' and tree['attributes'].get('class', '') in ref_group_names:
        ref_group_name = tree['attributes'].get('class', '')

    # for icon-item and image, do not get all children, they act as standalone images
    if tree['tag'] == 'g' and \
        'chart' not in tree['attributes'].get('class', '') and \
        (tree['attributes'].get('class', '') in ['icon-item', 'image']):
        ele_list.append({
            'id': len(ele_list),
            'ref_group_name': 'image',
            'node': tree
        })
        return ele_list

    for child in tree['children']:
        parse_all_leafs(child, ele_list, ref_group_name)
    return ele_list

def normalize_tree_leafs(tree, ref):
    tree['norm_bbox'] = normalize_bbox(tree['bounding_box'], ref)
    for child in tree['children']:
        normalize_tree_leafs(child, ref)

def normalize_leafs(leafs, ref):
    for leaf in leafs:
        leaf['node']['norm_bbox'] = normalize_bbox(leaf['node']['bounding_box'], ref)

def leaf_cost(gleaf, pleaf):
    is_both_image = (gleaf['node']['tag'] == 'image' and pleaf['node']['tag'] == 'g' and pleaf['ref_group_name'] in ['icon-item', 'image'])
    if gleaf['node']['tag'] != pleaf['node']['tag'] and not is_both_image and \
        not (gleaf['node']['tag'] == 'path' and pleaf['node']['tag'] in ['rect', 'circle', 'ellipse', 'polygon']) and \
        not (pleaf['node']['tag'] == 'path' and gleaf['node']['tag'] in ['rect', 'circle', 'ellipse', 'polygon']) and \
        not ('text' in gleaf['node'] and 'text' in pleaf['node']):
        return 1e9, []

    sims = []

    # deal with images
    if is_both_image:
        img_sim = image_similarity(gleaf, pleaf)
        sims.append(float(img_sim))
    elif gleaf['node']['tag'] == 'text' and 'text' in gleaf['node'] and 'text' in pleaf['node']:
        text_sim = text_similarity(gleaf, pleaf)
        sims.append(float(text_sim))
    else:
        color_sim = color_similarity(gleaf, pleaf)
        sims.append(float(color_sim))

    pos_sim = pos_similarity(gleaf, pleaf)
    sims.append(float(pos_sim))

    return 1 - (sum(sims) / len(sims)), sims


def pair_leafs(gt_leafs, pr_leafs, gt_matched_prs, pr_matched_gts, gt_match_costs, gt_match_sims):
    m = len(gt_leafs)
    n = len(pr_leafs)
    cost_matrix = np.zeros((m, n))
    sims_record = [[[] for _ in range(n)] for _ in range(m)]
    for i, gleaf in enumerate(gt_leafs):
        for j, pleaf in enumerate(pr_leafs):
            cost_matrix[i, j], sims_record[i][j] = leaf_cost(gleaf, pleaf)

    # hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    for i, j in zip(row_ind, col_ind):
        if cost_matrix[i, j] > 1:
            continue
        if gt_matched_prs[i] != -1 or pr_matched_gts[j] != -1:
            continue
        gt_matched_prs[i] = int(j)
        pr_matched_gts[j] = int(i)
        gt_match_costs[i] = cost_matrix[i, j]
        gt_match_sims[i] = sims_record[i][j]

def convert_tree_json(logger, tree_file, file_type):
    assert file_type in ['gt', 'pr'], 'file_type should be gt or pr'
    logger.info(f'converting {tree_file} to leafs')
    tree_json = load_json(tree_file)
    ref_bbox = tree_json['bounding_box']
    normalize_tree_leafs(tree_json, ref_bbox)
    leafs = parse_all_leafs(tree_json, [])
    logger.info(f'*** {file_type}    all: {len(leafs)}')

    for leaf in leafs:
        leaf['valid'] = judge_invalid_elements(leaf)
        if file_type == 'pr' and leaf['node']['tag'] == 'image':
            leaf['valid'] = False
    safe_save_json(leafs, tree_file.replace('.json', '_ori_leafs.json'))

    leafs = [leaf for leaf in leafs if leaf['valid']]
    logger.info(f'*** {file_type} filter: {len(leafs)}')
    # reorder leafs by x and y and update ids
    leafs = sorted(leafs, key=lambda x: x['node']['norm_bbox'][0])
    leafs = sorted(leafs, key=lambda x: x['node']['norm_bbox'][1])
    for i, leaf in enumerate(leafs):
        leaf['id'] = i
    safe_save_json(leafs, tree_file.replace('.json', '_leafs.json'))
    leaf_bboxes = [leaf['node']['norm_bbox'] for leaf in leafs]
    vis_bboxes_with_indexes(leaf_bboxes, tree_file.replace('.json', '.png'), tree_file.replace('.json', '_leafs.png'))

def compute_element_pairs(logger, gt_file, pr_file):
    gt_leafs_file = gt_file.replace('.json', '_leafs.json')
    pr_leafs_file = pr_file.replace('.json', '_leafs.json')
    assert os.path.exists(gt_leafs_file), f'gt leafs file {gt_leafs_file} not exist'
    assert os.path.exists(pr_leafs_file), f'pr leafs file {pr_leafs_file} not exist'

    gt_leafs = load_json(gt_leafs_file, output=False)
    pr_leafs = load_json(pr_leafs_file, output=False)

    print('Extracting image features...')
    for leaf in gt_leafs:
        if leaf['node']['tag'] == 'image':
            img = crop_icon(gt_file.replace('.json', '.png'), leaf['node']['norm_bbox'])
            feat = extract_image_feature(img)
            leaf['image_feature'] = feat
    for leaf in pr_leafs:
        if leaf['node']['tag'] == 'g' and leaf['ref_group_name'] in ['icon-item', 'image']:
            img = crop_icon(pr_file.replace('.json', '.png'), leaf['node']['norm_bbox'])
            feat = extract_image_feature(img)
            leaf['image_feature'] = feat

    gt_matched_prs = [-1] * len(gt_leafs)
    pr_matched_gts = [-1] * len(pr_leafs)
    gt_match_costs = [-1] * len(gt_leafs)
    gt_match_sims = [[]] * len(gt_leafs)

    pair_leafs(gt_leafs, pr_leafs, gt_matched_prs, pr_matched_gts, gt_match_costs, gt_match_sims)
    matched_costs = [x for x in gt_match_costs if x > -1]
    logger.info(f'*** matched cnt and cost: {len(matched_costs)}, {np.mean(matched_costs)}')

    safe_save_json({
        'gt_matched_prs': gt_matched_prs,
        'pr_matched_gts': pr_matched_gts,
        'gt_match_costs': gt_match_costs,
        'gt_match_sims': gt_match_sims
    }, pr_file.replace('.json', '_matched.json'))
    
    result_path = Path(pr_file).parent / 'result.txt'
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f'gt: {len(gt_leafs)}\n')
        f.write(f'pr: {len(pr_leafs)}\n')
        f.write(f'matched cnt and cost: {len(matched_costs)} {np.mean(matched_costs)}\n')
        for i, leaf in enumerate(gt_leafs):
            if gt_matched_prs[i] != -1:
                f.write(f'gt{i} {leaf["node"]["tag"]} {gt_matched_prs[i]} {pr_leafs[gt_matched_prs[i]]["node"]["tag"]} {gt_match_costs[i]} {gt_match_sims[i]}\n')
            else:
                f.write(f'gt{i} {leaf["node"]["tag"]} -1 -1 -1 []\n')
        for i, leaf in enumerate(pr_leafs):
            if pr_matched_gts[i] != -1:
                f.write(f'pr{i} {leaf["node"]["tag"]} {pr_matched_gts[i]} {gt_leafs[pr_matched_gts[i]]["node"]["tag"]} {gt_match_costs[pr_matched_gts[i]]} {gt_match_sims[pr_matched_gts[i]]}\n')
            else:
                f.write(f'pr{i} {leaf["node"]["tag"]} -1 -1 -1 []\n')
    
    return gt_matched_prs, pr_matched_gts

def eval_scores(gt_file, pr_file):
    gt_leafs = load_json(gt_file.replace('.json', '_leafs.json'), output=False)
    pr_leafs = load_json(pr_file.replace('.json', '_leafs.json'), output=False)
    match_results = load_json(pr_file.replace('.json', '_matched.json'), output=False)
    gt_matched_prs = match_results['gt_matched_prs']

    tp_cnt = len([x for x in gt_matched_prs if x != -1])
    prec = tp_cnt / len(pr_leafs) if len(pr_leafs) > 0 else 0
    rec = tp_cnt / len(gt_leafs) if len(gt_leafs) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    
    color_sims = []
    text_sims = []
    pos_sims = []
    image_sims = []
    size_sims = []

    matched_areas = []
    all_areas = []

    print('Extracting image features...')
    for leaf in gt_leafs:
        if leaf['node']['tag'] == 'image':
            img = crop_icon(gt_file.replace('.json', '.png'), leaf['node']['norm_bbox'])
            feat = extract_image_feature(img)
            leaf['image_feature'] = feat
        all_areas.append(box_area(leaf['node']['norm_bbox']))
    for leaf in pr_leafs:
        if leaf['node']['tag'] == 'g' and leaf['ref_group_name'] in ['icon-item', 'image']:
            img = crop_icon(pr_file.replace('.json', '.png'), leaf['node']['norm_bbox'])
            feat = extract_image_feature(img)
            leaf['image_feature'] = feat
        all_areas.append(box_area(leaf['node']['norm_bbox']))
    
    for gt, pr in enumerate(gt_matched_prs):
        gleaf = gt_leafs[gt]
        if pr == -1:
            if gleaf['node']['tag'] == 'text':
                text_sims.append(0)
            elif gleaf['node']['tag'] == 'image':
                image_sims.append(0)
            continue
        pleaf = pr_leafs[pr]

        matched_areas.append(box_area(gleaf['node']['norm_bbox']))
        matched_areas.append(box_area(pleaf['node']['norm_bbox']))
        color_sims.append(float(color_similarity(gleaf, pleaf)))
        pos_sims.append(pos_similarity_1d(gleaf, pleaf))
        size_sims.append(size_similarity(gleaf, pleaf))
        if gleaf['node']['tag'] == 'text':
            text_sims.append(text_similarity(gleaf, pleaf))
        elif gleaf['node']['tag'] == 'image':
            image_sims.append(float(image_similarity(gleaf, pleaf)))
    
    scores_dict = {
        'f1_score': f1,
        'precision': prec,
        'recall': rec,
        'area_matched': sum(matched_areas) / sum(all_areas),
        'text_recall': len([gt for gt, pr in enumerate(gt_matched_prs) if pr != -1 and gt_leafs[gt]['node']['tag'] == 'text']) / len(text_sims) if len(text_sims) > 0 else 0,
        'text': sum(text_sims) / len(text_sims) if text_sims else 0,
        'image_recall': len([gt for gt, pr in enumerate(gt_matched_prs) if pr != -1 and gt_leafs[gt]['node']['tag'] == 'image']) / len(image_sims) if len(image_sims) > 0 else 0,
        'image': sum(image_sims) / len(image_sims) if image_sims else 0,
        'color': sum(color_sims) / len(color_sims) if color_sims else 0,
        'size': sum(size_sims) / len(size_sims) if size_sims else 0,
        'pos': sum(pos_sims) / len(pos_sims) if pos_sims else 0,
        'raw': {
            'text': text_sims,
            'image': image_sims,
            'color': color_sims,
            'size': size_sims,
            'pos': pos_sims
        }
    }
    safe_save_json(scores_dict, pr_file.replace('.json', '_scores.json'))
    
    return scores_dict

