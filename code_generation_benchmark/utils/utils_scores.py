from utils.utils_color import color_similarity_ciede2000
from difflib import SequenceMatcher
from utils.utils_image_encoder import cal_cosine_dist

def color_similarity(gleaf, pleaf):
    gs = gleaf['node']['computed_style']
    ps = pleaf['node']['computed_style']
    
    # get color similarity
    gfill = gs.get('fill', 'none')
    gopacity = float(gs.get('opacity', '1')) * float(gs.get('fill-opacity', '1'))
    pfill = ps.get('fill', 'none')
    popacity = float(ps.get('opacity', '1')) * float(ps.get('fill-opacity', '1'))
    if gfill != 'none' and pfill != 'none':
        color_sim = color_similarity_ciede2000(gfill, pfill, gopacity, popacity)
    else:
        color_sim = 0
    return color_sim

def text_similarity(gleaf, pleaf):
    # text similarity
    text_sim = SequenceMatcher(None, gleaf['node']['text'], pleaf['node']['text']).ratio()
    return text_sim

def image_similarity(gleaf, pleaf):
    if 'image_feature' not in gleaf:
        assert False, f'image_feature not in gleaf {gleaf["id"]}'
    else:
        feat1 = gleaf['image_feature']
    if 'image_feature' not in pleaf:
        assert False, f'image_feature not in pleaf {pleaf["id"]}'
    else:
        feat2 = pleaf['image_feature']
    # get image similarity
    img_sim = 1 - cal_cosine_dist(feat1, feat2)
    return img_sim

def pos_similarity(gleaf, pleaf):
    gpos = (gleaf['node']['norm_bbox'][0] + gleaf['node']['norm_bbox'][2]) / 2, \
            (gleaf['node']['norm_bbox'][1] + gleaf['node']['norm_bbox'][3]) / 2
    ppos = (pleaf['node']['norm_bbox'][0] + pleaf['node']['norm_bbox'][2]) / 2, \
            (pleaf['node']['norm_bbox'][1] + pleaf['node']['norm_bbox'][3]) / 2
    pos_sim = 1 - ((gpos[0] - ppos[0]) * (gpos[0] - ppos[0]) + (gpos[1] - ppos[1]) * (gpos[1] - ppos[1])) / 2
    return pos_sim

def pos_similarity_1d(gleaf, pleaf):
    gpos = (gleaf['node']['norm_bbox'][0] + gleaf['node']['norm_bbox'][2]) / 2, \
            (gleaf['node']['norm_bbox'][1] + gleaf['node']['norm_bbox'][3]) / 2
    ppos = (pleaf['node']['norm_bbox'][0] + pleaf['node']['norm_bbox'][2]) / 2, \
            (pleaf['node']['norm_bbox'][1] + pleaf['node']['norm_bbox'][3]) / 2
    pos_sim = 1 - max(abs(gpos[0] - ppos[0]), abs(gpos[1] - ppos[1]))
    return pos_sim

def size_similarity(gleaf, pleaf):
    gsize = (gleaf['node']['norm_bbox'][2] - gleaf['node']['norm_bbox'][0]) * \
            (gleaf['node']['norm_bbox'][3] - gleaf['node']['norm_bbox'][1])
    psize = (pleaf['node']['norm_bbox'][2] - pleaf['node']['norm_bbox'][0]) * \
            (pleaf['node']['norm_bbox'][3] - pleaf['node']['norm_bbox'][1])
    if max(gsize, psize) == 0:
        gsize = max((gleaf['node']['norm_bbox'][2] - gleaf['node']['norm_bbox'][0]), \
            (gleaf['node']['norm_bbox'][3] - gleaf['node']['norm_bbox'][1]))
        psize = max((pleaf['node']['norm_bbox'][2] - pleaf['node']['norm_bbox'][0]), \
            (pleaf['node']['norm_bbox'][3] - pleaf['node']['norm_bbox'][1]))
    size_sim = 1 - abs(gsize - psize) / max(gsize, psize)
    return size_sim

