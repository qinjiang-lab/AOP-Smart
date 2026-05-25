# AOP-Smart

AOP-Smart is a software system that enhances the capability of Large Language Models (LLMs) in the Adverse Outcome Pathway (AOP) domain using a Retrieval-Augmented Generation (RAG) framework.

---

## Requirements

Before using this software, please ensure that:

- Python is installed on your system  
- You have prepared the **Base URL** and **API Key** for your LLM service  

---

## LLM API Resources (for reference)

- DeepSeek: https://platform.deepseek.com/  
- GPT (OpenAI): https://platform.openai.com/  
- Gemini: https://aistudio.google.com/  
- OpenRouter (aggregated LLM platform with 100+ models): https://openrouter.ai/  

---

## Installation & Usage

### Windows

For Windows users, simply run:

```
Windows_Run.bat
```

This will automatically install the required `openai` library. No manual setup is needed.

---

### macOS / Linux

For macOS and Linux users:

1. Install the required library:

```
pip install openai
```

or
```
pip3 install openai
```
2. Run the program:
```
python AOP-Smart.py
```
or
```
python3 AOP-Smart.py
```

---

## How to Use

After launching the interface:

1. In the **configuration panel (left side)**:
   - Enter the **Base URL** of your LLM service  
   - Enter your **API Key**

2. Click **"Fetch Models"** to retrieve available models  

3. Select a model from the list  

4. Enter your question in the **Task input field**  

5. Click **"RUN"** and wait for the result

workflow.pdf documents my personal usage process for reference only.

---


## Notes

- The performance depends on the selected LLM and API configuration  
- Make sure your API key has sufficient quota and permissions  
- If you need to change the XML version, please delete the `AOP-Smart.json` and `Index.txt` files first. After that, Windows users can simply rerun the `.bat` file, while macOS and Linux users should run:
```
python XML_analysis.py
```
---

## Overview

AOP-Smart integrates structured AOP knowledge (KEs, KERs, and AOPs) with LLM reasoning, improving reliability and reducing hallucination in domain-specific tasks.

## Citation

If you find this work useful, please cite:

AOP-Smart has been published as a preprint on arXiv.

```
@article{niu2026aop,
  title={AOP-Smart: A RAG-Enhanced Large Language Model Framework for Adverse Outcome Pathway Analysis},
  author={Niu, Qinjiang and Yan, Lu},
  journal={arXiv preprint arXiv:2604.10874},
  year={2026}
}
```
