# Infographic Chart Code Generation Benchmark

This is the code repository for the **Infographic Chart Code Generation Benchmark**. For more details, please refer to our [paper](https://arxiv.org/abs/2505.18668).

## Overview

The benchmark assesses chart code generation at two levels:
- **Low-level**: Element-wise similarity between generated and reference SVGs
- **High-level**: Overall visual fidelity and functionality assessment

## Installation

```bash
git clone https://github.com/ChartGalaxy/ChartGalaxy.git
cd ChartGalaxy/code_generation_benchmark
```

## Usage

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
   python main.py
   ```

## Data Structure

Each chart folder in `data_root_dir` should contain:
- `chart.svg`: Original chart in SVG format

The system will generate:
- `convert_chart.html`: HTML rendering of reference chart
- `convert_chart.png`: PNG screenshot of reference chart
- `convert_chart.json`: Element structure of reference chart
- Model-specific outputs in subfolders

## Results

Results are saved in model-specific subfolders with:
- Generated HTML/PNG renderings
- Evaluation metrics in JSON format
- Detailed logs in `log_dir`
