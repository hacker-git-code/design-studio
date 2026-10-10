"""Merge the LoRA adapter into the base model and prepare an Ollama package.

    python -m atelier.llm.merge_export --adapter checkpoints/atelier-dna --out checkpoints/atelier-dna-merged

Then, for a fast local model with Ollama (CPU is fine for a 1.5B model):

    git clone https://github.com/ggml-org/llama.cpp
    pip install -r llama.cpp/requirements.txt
    python llama.cpp/convert_hf_to_gguf.py checkpoints/atelier-dna-merged --outfile checkpoints/atelier-dna.gguf --outtype q8_0
    ollama create atelier-dna -f checkpoints/Modelfile
    atelier new "your brief" --llm ollama:atelier-dna
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="checkpoints/atelier-dna")
    ap.add_argument("--base")
    ap.add_argument("--out", default="checkpoints/atelier-dna-merged")
    a = ap.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    meta = Path(a.adapter) / "atelier.json"
    base = a.base or (json.loads(meta.read_text())["base"] if meta.exists() else "Qwen/Qwen2.5-1.5B-Instruct")
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.float16)
    model = PeftModel.from_pretrained(model, a.adapter).merge_and_unload()
    model.save_pretrained(a.out, safe_serialization=True)
    AutoTokenizer.from_pretrained(a.adapter).save_pretrained(a.out)

    from ..brief import SYSTEM_PROMPT

    mf = Path(a.out).parent / "Modelfile"
    mf.write_text(f'FROM ./atelier-dna.gguf\nPARAMETER temperature 0.1\nPARAMETER num_ctx 2048\nSYSTEM """{SYSTEM_PROMPT}"""\n')
    print(f"merged model -> {a.out}\nOllama Modelfile -> {mf}")


if __name__ == "__main__":
    main()
