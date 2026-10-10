"""LoRA fine-tune a small open model to turn briefs into Brand DNA JSON.

Default base: Qwen/Qwen2.5-1.5B-Instruct (Apache-2.0, free to use commercially).
Runs on a free Colab T4 (fp16) or any 12GB+ GPU; ~20-60 min for 6k examples.

    pip install -e ".[llm]"
    atelier llm dataset -o llm_data -n 6000
    python -m atelier.llm.train_lora --data llm_data --out checkpoints/atelier-dna
    python -m atelier.llm.merge_export --adapter checkpoints/atelier-dna --out checkpoints/atelier-dna-merged
    atelier llm eval --backend hf:checkpoints/atelier-dna-merged
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path


def to_prompt_completion(path: Path):
    rows = []
    for line in Path(path).read_text().splitlines():
        m = json.loads(line)["messages"]
        rows.append({"prompt": m[:2], "completion": m[2:]})
    return rows


def main():
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
    ap.add_argument("--load-4bit", action="store_true", help="QLoRA (needs bitsandbytes); for small GPUs")
    a = ap.parse_args()

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    fp16 = torch.cuda.is_available() and not bf16
    tok = AutoTokenizer.from_pretrained(a.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    model_kw = dict(torch_dtype=torch.bfloat16 if bf16 else torch.float16 if fp16 else torch.float32)
    if a.load_4bit:
        from transformers import BitsAndBytesConfig

        model_kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                             bnb_4bit_compute_dtype=model_kw["torch_dtype"])
    model = AutoModelForCausalLM.from_pretrained(a.base, **model_kw)

    train = Dataset.from_list(to_prompt_completion(Path(a.data) / "train.jsonl"))
    val = Dataset.from_list(to_prompt_completion(Path(a.data) / "val.jsonl"))

    lora = LoraConfig(r=a.rank, lora_alpha=a.rank * 2, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")

    cfg_kw = dict(output_dir=a.out, num_train_epochs=a.epochs, learning_rate=a.lr, per_device_train_batch_size=a.batch,
                  per_device_eval_batch_size=a.batch, gradient_accumulation_steps=a.grad_accum, lr_scheduler_type="cosine",
                  warmup_ratio=0.03, logging_steps=20, eval_strategy="steps", eval_steps=200, save_steps=200,
                  save_total_limit=2, bf16=bf16, fp16=fp16, gradient_checkpointing=True, report_to="none")
    params = inspect.signature(SFTConfig.__init__).parameters
    # TRL renamed max_seq_length -> max_length; loss on the JSON answer only
    cfg_kw["max_length" if "max_length" in params else "max_seq_length"] = a.max_len
    if "completion_only_loss" in params:
        cfg_kw["completion_only_loss"] = True
    cfg = SFTConfig(**cfg_kw)

    tr_kw = dict(model=model, args=cfg, train_dataset=train, eval_dataset=val, peft_config=lora)
    tr_params = inspect.signature(SFTTrainer.__init__).parameters
    tr_kw["processing_class" if "processing_class" in tr_params else "tokenizer"] = tok
    trainer = SFTTrainer(**tr_kw)
    trainer.train()
    trainer.save_model(a.out)
    tok.save_pretrained(a.out)
    (Path(a.out) / "atelier.json").write_text(json.dumps({"base": a.base, "data": a.data}))
    print(f"LoRA adapter saved to {a.out}")


if __name__ == "__main__":
    main()
