import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup, NavigableString
from utils.utils_chat import safe_save_json, load_txt

def parse_element_with_style_and_bbox(driver, web_element):
    computed_style = driver.execute_script("""
        const elem = arguments[0];
        const styles = window.getComputedStyle(elem);
        const style_dict = {};
        for (let i = 0; i < styles.length; i++) {
            const prop = styles[i];
            style_dict[prop] = styles.getPropertyValue(prop);
        }
        return style_dict;
    """, web_element)

    # only keep color-related attributes in style
    color_attributes = ['fill', 'stroke', 'opacity', 'fill-opacity', 'stroke-opacity', 'stroke-width']
    computed_style = {k: v for k, v in computed_style.items() if k in color_attributes}

    bbox = driver.execute_script("""
        const elem = arguments[0];
        try {
            const box = elem.getBoundingClientRect();
            return {x: box.x, y: box.y, width: box.width, height: box.height};
        } catch (e) {
            return null;
        }
    """, web_element)
    
    svg_bbox = driver.execute_script("""
        const elem = arguments[0];
        try {
            const box = elem.getBBox();
            return {x: box.x, y: box.y, width: box.width, height: box.height};
        } catch (e) {
            return null;
        }
    """, web_element)

    return computed_style, bbox, svg_bbox

def parse_svg_tree(driver, bs_element: BeautifulSoup, selenium_element):
    tag_name = bs_element.name
    assert not isinstance(bs_element, NavigableString), "bs_element should not be NavigableString"
    
    attributes = dict(bs_element.attrs)
    computed_style, bbox, svg_bbox = None, None, None
    if selenium_element:
        computed_style, bbox, svg_bbox = parse_element_with_style_and_bbox(driver, selenium_element)

    node_info = {
        "tag": tag_name,
        "attributes": attributes,
        "computed_style": computed_style,
        "bounding_box": bbox,
        "svg_bounding_box": svg_bbox,
        "html": str(bs_element),
        "children": []
    }

    if len(bs_element.find_all(recursive=False)) > 5000:
        print(f"--- {bs_element.name} has too many children: {len(bs_element.find_all(recursive=False))}")
        return node_info

    for child in bs_element.find_all(recursive=False):
        siblings = child.find_previous_siblings(child.name)
        index = len(siblings) + 1
        child_sele = selenium_element.find_element(By.XPATH, f'./*[local-name()="{child.name}"][{index}]')
        child_info = parse_svg_tree(driver, child, child_sele)
        if child_info:
            node_info["children"].append(child_info)
    if not node_info["children"]:
        # judge if has text
        text_content = bs_element.text.strip()
        if text_content:
            node_info["text"] = text_content


    return node_info

def parse_tree_from_html(driver: webdriver.Chrome, html_path: str, save_svg=True):
    driver.get(f'file://{html_path}')
    
    time.sleep(0.2)

    svg_element = driver.find_element("css selector", "svg")
    svg_content = svg_element.get_attribute('outerHTML')    
    if save_svg:
        svg_file_path = html_path.replace('.html', '_extracted.svg')
        with open(svg_file_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
    
    soup = BeautifulSoup(svg_content, "xml")
    svg_root = soup.find('svg')

    tree_data = parse_svg_tree(driver, svg_root, svg_element)
    safe_save_json(tree_data, html_path.replace('.html', '.json'))
    return tree_data

def convert_svg_to_html(svg_path: str, html_path: str):
    svg_content = load_txt(svg_path)
    html = f"""<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Infographic Chart</title>
    </head>
    <body>
        <div id="chart-container">
          {svg_content}
        </div>
    </body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return html

def convert_g_to_html(g_str, gw, gh, html_path: str):
    html = f"""<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Infographic Chart</title>
    </head>
    <body>
        <div id="chart-container">
            <svg width="{gw}" height="{gh}">
                <g transform="translate({gw / 2}, {gh / 2})">
                    {g_str}
                </g>
            </svg>
        </div>
    </body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return html

