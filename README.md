# ChartGalaxy

[**🤗 ChartGalaxy**](https://huggingface.co/datasets/ChartGalaxy/ChartGalaxy)

This repo contains the associated code for the paper "ChartGalaxy: A Dataset for Infographic Chart Understanding and Generation"

<!-- ## 🔔 News -->

## Introduction

### ChartGalaxy

ChartGalaxy is a million-scale dataset of synthetic and real infographic charts with data tables, supporting applications in infographic chart understanding, code generation, and chart generation. The dataset addresses the challenge that existing datasets are mostly limited to plain charts, failing to capture the diverse range of design styles and layouts that are key characteristics of infographic charts.

### Overview

- **Size**: 1,255,606 infographic charts (1,151,087 synthetic + 104,519 real)
- **Content**: Each infographic chart is paired with the tabular data used to create it
- **Chart Types**: 75 chart types with 330 chart variations
- **Layout Templates**: 68 layout templates

### Data Collection and Creation

ChartGalaxy was constructed through:

1. **Real Infographic Chart Collection**: Charts were collected from 19 reputable chart-rich websites, such as Pinterest, Visual Capitalist, Statista, and Information is Beautiful.

2. **Synthetic Infographic Chart Creation**: Following an inductive structuring process that:
   - Identifies 75 chart types (e.g., bar charts) and 330 chart variations reflecting different visual element styles
   - Extracts 68 layout templates defining spatial relationships among elements
   - Programmatically generates synthetic charts based on these patterns

## 🎯 Applications

The utility of ChartGalaxy is demonstrated through three representative applications:

### 1. 🧠 Infographic Chart Understanding

Fine-tuning on ChartGalaxy improves the performance of foundation models on infographic chart understanding. 

### 2. 💻 Infographic Chart Code Generation

A benchmark for assessing LVLMs' code generation for infographic charts. The benchmark evaluates the similarity between charts rendered by the generated D3.js code and ground-truth ones at two levels of granularity: high-level (overall visual similarity) and low-level (average similarity across fine-grained SVG elements).

#### Overview

The benchmark assesses chart code generation at two levels:
- **Low-level**: Element-wise similarity between generated and reference SVGs
- **High-level**: Overall visual fidelity and functionality assessment

#### Installation

```bash
git clone https://github.com/ChartGalaxy/ChartGalaxy.git
cd ChartGalaxy/code_generation_benchmark
```

#### Usage

1. Configure settings in `code_generation_benchmark/configs/default_config.yaml`:
   ```yaml
   prompts:
     high_level_eval_prompt_file: eval_high_level.txt
     chat_prompt_file: chat_direct_prompt.txt

   VLM:
     max_tokens: null
     thinking_budget: 1024
     temperature: 0.0
     top_p: 1.0

   models:
     # Uncomment the models you want to evaluate
     # - gpt-4o-2024-11-20
     # - claude-3-7-sonnet-20250219
     # - gemini-2.5-pro-preview-05-06
     # - Qwen/Qwen2.5-VL-72B-Instruct

   dirs:
     output_dir: ./output
     log_dir: ./logs
     data_root_dir: ./data
     clip_cache_dir: ./model-ckpts

   eval_model: gpt-4o-2024-11-20
   n_workers: 10
   ```

2. Run the benchmark:
   ```bash
   python -m code_generation_benchmark.main
   ```

#### Data Structure

Each chart folder in `data_root_dir` should contain:
- `chart.svg`: Original chart in SVG format

The system will generate:
- `convert_chart.html`: HTML rendering of reference chart
- `convert_chart.png`: PNG screenshot of reference chart
- `convert_chart.json`: Element structure of reference chart
- Model-specific outputs in subfolders

#### Results

Results are saved in model-specific subfolders with:
- Generated HTML/PNG renderings
- Evaluation metrics in JSON format
- Detailed logs in `log_dir`
  

### 3. 🖼️ Example-based Infographic Chart Generation

An example-based method that transforms user-provided tabular data into an infographic chart, aligning with the layout and visual style of a given example chart. User studies show this method outperforms GPT-Image-1 on fidelity, aesthetics, and creativity.


## Contact
- chartgalaxy@163.com

