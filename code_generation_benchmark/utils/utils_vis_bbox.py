import cv2
import numpy as np

# draw rectangle in an image

def draw_rectangle(image, bbox, color=(0, 255, 0), thickness=2):
    """
    Draw a rectangle on an image.
    
    Args:
        image: numpy array of shape (H, W, 3), the image to draw on
        bbox: tuple of (x_min, y_min, x_max, y_max) or list [x_min, y_min, x_max, y_max]
        color: tuple of (B, G, R), the color of the rectangle
        thickness: int, thickness of the rectangle lines
    
    Returns:
        numpy array: the image with rectangle drawn
    """
    x_min, y_min, x_max, y_max = [int(coord) for coord in bbox]
    cv2.rectangle(image, (x_min, y_min), (x_max, y_max), color, thickness)
    return image

def draw_rectangles(image, bboxes, colors=None, thickness=2):
    """
    Draw multiple rectangles on an image.
    
    Args:
        image: numpy array of shape (H, W, 3), the image to draw on
        bboxes: list of bounding boxes, each bbox is (x_min, y_min, x_max, y_max) or [x_min, y_min, x_max, y_max]
        colors: list of colors corresponding to each bbox, if None, use default color
        thickness: int, thickness of the rectangle lines
    
    Returns:
        numpy array: the image with rectangles drawn
    """
    result = image.copy()
    for i, bbox in enumerate(bboxes):
        if colors is not None and i < len(colors):
            color = colors[i]
        else:
            color = (0, 255, 0)  # Default to green
        result = draw_rectangle(result, bbox, color, thickness)
    return result

def draw_labeled_rectangle(image, bbox, label, color=(0, 255, 0), thickness=2, text_color=(255, 255, 255), font_scale=0.6):
    """
    Draw a rectangle with a label on an image.
    
    Args:
        image: numpy array, the image to draw on
        bbox: tuple of (x_min, y_min, x_max, y_max)
        label: str, the label text
        color: tuple, the color of the rectangle
        thickness: int, thickness of the rectangle lines
        text_color: tuple, color of the text
        font_scale: float, font scale
    
    Returns:
        numpy array: the image with labeled rectangle drawn
    """
    result = draw_rectangle(image.copy(), bbox, color, thickness)
    x_min, y_min, _, _ = [int(coord) for coord in bbox]
    
    # Get text size
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(label, font, font_scale, 1)[0]
    
    # Draw text background
    cv2.rectangle(result, 
                  (x_min, y_min - text_size[1] - 5),
                  (x_min + text_size[0], y_min),
                  color, -1)
    
    # Draw text
    cv2.putText(result, label, (x_min, y_min - 5),
                font, font_scale, text_color, 1, cv2.LINE_AA)
    
    return result

def get_bboxes(json_path):
    """
    Get bounding boxes from a JSON file.
    
    Args:
        json_path: str, path to the JSON file
    
    Returns:
        list of tuples: each tuple is (x_min, y_min, x_max, y_max)
    """
    import json
    with open(json_path, 'r') as f:
        data = json.load(f)
    bb = data['bounding_box']
    xx, yy, ww, hh = bb['x'], bb['y'], bb['width'], bb['height']
    
    bboxes = []
    def traverse_dict(d):
        if isinstance(d, dict):
            bb = d.get('bounding_box')
            if bb:
                x, y, w, h = bb['x'], bb['y'], bb['width'], bb['height']
                bboxes.append(((x-xx)/ww, (y-yy)/hh, (x+w-xx)/ww, (y+h-yy)/hh))
            traverse_dict(d.get('children', []))
        elif isinstance(d, list):
            for item in d:
                traverse_dict(item)
    traverse_dict(data)
    
    return bboxes

def vis_bboxes(json_path, image_path=None):
    if not image_path:
        image_path = json_path.replace('.json', '.png')
    bboxes = get_bboxes(json_path)
    image = cv2.imread(image_path)
    w, h = image.shape[1], image.shape[0]
    bboxes = [(int(x_min*w), int(y_min*h), int(x_max*w), int(y_max*h)) for x_min, y_min, x_max, y_max in bboxes]
    image = draw_rectangles(image, bboxes)
    # save image
    cv2.imwrite(json_path.replace('.json', '_bbox.png'), image)

def vis_one_bbox(bbox, origin_image_path, save_path):
    image = cv2.imread(origin_image_path)
    w, h = image.shape[1], image.shape[0]
    bbox = (int(bbox[0]*w), int(bbox[1]*h), int(bbox[2]*w), int(bbox[3]*h))
    image = draw_rectangle(image, bbox)
    cv2.imwrite(save_path, image)

def vis_bboxes_with_indexes(bboxes, origin_image_path, save_path):
    image = cv2.imread(origin_image_path)
    w, h = image.shape[1], image.shape[0]
    for idx, bbox in enumerate(bboxes):
        bbox = (int(bbox[0]*w), int(bbox[1]*h), int(bbox[2]*w), int(bbox[3]*h))
        image = draw_labeled_rectangle(image, bbox, str(idx))
    cv2.imwrite(save_path, image)
