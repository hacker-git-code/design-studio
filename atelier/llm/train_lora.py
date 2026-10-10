"""LoRA fine-tune a small open model to turn briefs into Brand DNA JSON.

Default base: Qwen/Qwen2.5-1.5B-Instruct (Apache-2.0, free to use commercially).
Runs on a free Colab T4 (fp16) or any 12GB+ GPU; ~20-60 min for 6k examples.
Uses plain transformers.Trainer + PEFT (no TRL), with the loss computed on
the JSON answer only, so it also runs on CPU for small smoke tests.

    pip install -e ".[llm]"
    atelier llm dataset -o llm_data -n 6000
    python -m atelier.llm.train_lora --data llm_data --out checkpoints/atelier-dna
    python -m atelier.llm.merge_export --adapter checkpoints/atelier-dna --out checkpoints/atelier-dna-merged
    atelier llm eval --data llm_data --backend hf:checkpoints/atelier-dna-merged
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
from pathlib import Path


def encode(tok, messages, max_len):
    """input_ids for system+user+assistant; labels mask everything but the answer."""
    prompt = tok.apply_chat_template(messages[:2], add_generation_prompt=True, tokenize=False)
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    a_ids = tok(messages[2]["content"] + (tok.eos_token or ""), add_special_tokens=False)["input_ids"]
    ids = (p_ids + a_ids)[:max_len]
    labels = ([-100] * len(p_ids) + a_ids)[:max_len]
    return {"input_ids": ids, "labels": labels}


def load_rows(path: Path, tok, max_len):
    rows = []
    for line in Path(path).read_text().splitlines():
        r = encode(tok, json.loads(line)["messages"], max_len)
        if any(x != -100 for x in r["labels"]):
            rows.append(r)
    return rows


class Collator:
    def __init__(self, pad_id):
        self.pad_id = pad_id

    def __call__(self, batch):
        import torch

        n = max(len(b["input_ids"]) for b in batch)
        ids = torch.full((len(batch), n), self.pad_id, dtype=torch.long)
        labels = torch.full((len(batch), n), -100, dtype=torch.long)
        mask = torch.zeros((len(batch), n), dtype=torch.long)
        for i, b in enumerate(batch):
            k = len(b["input_ids"])
            ids[i, :k] = torch.tensor(b["input_ids"])
            labels[i, :k] = torch.tensor(b["labels"])
            mask[i, :k] = 1
        return {"input_ids": ids, "labels": labels, "attention_mask": mask}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="llm_data")
    ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--out", default="checkpoints/atelier-dna")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=768)
    ap.add_argument("--max-steps", type=int, default=-1, help="cap steps (smoke tests)")
    ap.add_argument("--load-4bit", action="store_true", help="QLoRA (needs bitsandbytes); for small GPUs")
    a = ap.parse_args(argv)

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    cuda = torch.cuda.is_available()
    bf16 = cuda and torch.cuda.is_bf16_supported()
    fp16 = cuda and not bf16
    tok = AutoTokenizer.from_pretrained(a.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    dtype = torch.bfloat16 if bf16 else torch.float16 if fp16 else torch.float32
    model_kw = {"dtype": dtype}
    if a.load_4bit:
        from peft import prepare_model_for_kbit_training
        from transformers import BitsAndBytesConfig

        model_kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype)
    model = AutoModelForCausalLM.from_pretrained(a.base, **model_kw)
    if a.load_4bit:
        model = prepare_model_for_kbit_training(model)
    if fp16:
        model = model.float()  # fp16 AMP needs fp32 master weights (T4); LoRA keeps it small
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=a.rank, lora_alpha=a.rank * 2, lora_dropout=0.05,
                                             target_modules="all-linear", task_type="CAUSAL_LM"))
    model.print_trainable_parameters()

    train = load_rows(Path(a.data) / "train.jsonl", tok, a.max_len)
    val = load_rows(Path(a.data) / "val.jsonl", tok, a.max_len)
    steps = math.ceil(len(train) / (a.batch * a.grad_accum) * a.epochs)
    kw = dict(output_dir=a.out, num_train_epochs=a.epochs, max_steps=a.max_steps, learning_rate=a.lr,
              per_device_train_batch_size=a.batch, per_device_eval_batch_size=a.batch, gradient_accumulation_steps=a.grad_accum,
              lr_scheduler_type="cosine", warmup_steps=max(1, int(0.03 * steps)), logging_steps=20, eval_strategy="steps",
              eval_steps=200, save_steps=200, save_total_limit=2, bf16=bf16, fp16=fp16, report_to="none",
              remove_unused_columns=False)
    params = inspect.signature(TrainingArguments.__init__).parameters
    if "eval_strategy" not in params:
        kw["evaluation_strategy"] = kw.pop("eval_strategy")
    args = TrainingArguments(**{k: v for k, v in kw.items() if k in params})
    trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=val, data_collator=Collator(tok.pad_token_id))
    trainer.train()
    print("eval:", trainer.evaluate())
    model.save_pretrained(a.out)
    tok.save_pretrained(a.out)
    (Path(a.out) / "atelier.json").write_text(json.dumps({"base": a.base, "data": a.data}))
    print(f"LoRA adapter saved to {a.out}")


if __name__ == "__main__":
    main()
