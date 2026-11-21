# Credits and sources

## What was reused
| Item | Source | How it was used |
|---|---|---|
| Chatbot pattern (Hugging Face model plus a Gradio chat interface) | KDnuggets (2023), "Build AI chatbot in 5 minutes with Hugging Face and Gradio" | Starting idea only. All application code in this repository was written for this project and extends the pattern with safety checks, retrieval, planners, tracking, and tests. |
| Gradio 5 | Abid et al. (2019), https://www.gradio.app | Web interface (library, not modified) |
| Transformers, PyTorch | Hugging Face, https://github.com/huggingface/transformers | Loading and running the language model (libraries, not modified) |
| sentence-transformers | Reimers & Gurevych (2019), https://www.sbert.net | Embeddings with all-MiniLM-L6-v2 (Apache 2.0) |
| Qwen2.5-1.5B-Instruct | Qwen Team (2024), https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct (Apache 2.0) | Primary language model |
| Other open models (for example Llama-3.2-1B-Instruct) | Meta and others, on Hugging Face | Not used in this project. The code can load them by changing `FITBUDDY_MODEL` (check each license first) |
| NumPy | https://numpy.org | Similarity search |

## Content written by the group
The 163 notes in `knowledge/`, the 221 dishes and cooking methods (`meals.py`, `recipes.py`), and the 55 exercises (`exercises.py`) were written for
this project from general public guidance, mainly the U.S. Physical Activity Guidelines for Americans, 2nd edition (HHS, 2018). They are not copied
from any website or book. They have not been reviewed by a certified trainer or dietitian.

## Design influences
- Amershi et al. (2019), Guidelines for human-AI interaction (status visibility, efficient correction, explanation).
- Miller (2026), Stanford HAI article on the Bloom coach (supportive, non-prescriptive coaching tone).
- Lewis et al. (2020), retrieval-augmented generation.

## AI assistance
[Group: state here how an AI assistant (Claude, Anthropic) was used, for example "to draft and debug code, tests, and documents", and confirm
this matches your course policy.]
