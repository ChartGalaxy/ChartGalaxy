from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
import re

def rgb_to_lab(rgb):
    """
    Convert an RGB color to Lab color space.
    RGB values should be in the range [0, 255].
    """
    # Create an sRGBColor object from RGB values
    rgb_color = sRGBColor(rgb[0], rgb[1], rgb[2], is_upscaled=True)
    
    # Convert to Lab color space
    lab_color = convert_color(rgb_color, LabColor)
    
    return lab_color

def parse_color_to_visual_rgb(color_str, opacity=1.0, background=(255, 255, 255)):
    color_str = color_str.strip().lower()
    r, g, b, a = 0, 0, 0, 1.0

    # hex: #rrggbb
    if re.match(r'^#([0-9a-f]{6})$', color_str):
        r = int(color_str[1:3], 16)
        g = int(color_str[3:5], 16)
        b = int(color_str[5:7], 16)

    # hex shorthand: #rgb
    elif re.match(r'^#([0-9a-f]{3})$', color_str):
        r = int(color_str[1]*2, 16)
        g = int(color_str[2]*2, 16)
        b = int(color_str[3]*2, 16)

    # rgb or rgba
    elif match := re.match(r'^rgba?\(([^)]+)\)$', color_str):
        parts = match.group(1).split(',')
        if len(parts) >= 3:
            r = int(float(parts[0].strip()))
            g = int(float(parts[1].strip()))
            b = int(float(parts[2].strip()))
            if len(parts) == 4:
                a = float(parts[3].strip())

    else:
        raise ValueError(f"Unsupported color format: {color_str}")

    final_alpha = a * opacity

    bg_r, bg_g, bg_b = background
    r_final = round(r * final_alpha + bg_r * (1 - final_alpha))
    g_final = round(g * final_alpha + bg_g * (1 - final_alpha))
    b_final = round(b * final_alpha + bg_b * (1 - final_alpha))

    return [r_final, g_final, b_final]


def color_similarity_ciede2000(c1, c2, o1=1.0, o2=1.0):
    """
    Calculate the color similarity between two RGB colors using the CIEDE2000 formula.
    Returns a similarity score between 0 and 1, where 1 means identical.
    """
    rgb1 = parse_color_to_visual_rgb(c1, opacity=o1)
    rgb2 = parse_color_to_visual_rgb(c2, opacity=o2)

    # Convert RGB colors to Lab
    lab1 = rgb_to_lab(rgb1)
    lab2 = rgb_to_lab(rgb2)
    
    # Calculate the Delta E (CIEDE2000)
    delta_e = delta_e_cie2000(lab1, lab2)
    
    # Normalize the Delta E value to get a similarity score
    # Note: The normalization method here is arbitrary and can be adjusted based on your needs.
    # A delta_e of 0 means identical colors. Higher values indicate more difference.
    # For visualization purposes, we consider a delta_e of 100 to be completely different.
    similarity = max(0, 1 - (delta_e / 100))
    
    return similarity

