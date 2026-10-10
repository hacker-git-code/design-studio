"""Local inference with transformers (for `--llm hf:<path>`)."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=2)
def _load(path: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype="auto",
                                                 device_map="auto" if torch.cuda.is_available() else None)
    model.eval()
    return tok, model


def generate_dna_json(path: str, brief: str, max_new_tokens: int = 400) -> str:
    import torch

    from ..brief import SYSTEM_PROMPT

    tok, model = _load(path)
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Brief: {brief}"}]
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.eos_token_id)
    return tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
