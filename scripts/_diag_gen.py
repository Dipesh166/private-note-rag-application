import sys, json, struct
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

snap = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/model.safetensors"
with open(snap, "rb") as f:
    n = struct.unpack("<Q", f.read(8))[0]
    hdr = json.loads(f.read(n))
print("safetensors keys:", len(hdr))
print("has lm_head.weight:", "lm_head.weight" in hdr)
print("has model.embed_tokens.weight:", "model.embed_tokens.weight" in hdr)

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16, low_cpu_mem_usage=True)
model.to("cuda")
model.eval()

print("tie_word_embeddings:", model.config.tie_word_embeddings)
print("lm_head.weight is embed_tokens.weight:",
      model.lm_head.weight.data_ptr() == model.model.embed_tokens.weight.data_ptr())

messages = [
    {"role": "system", "content": "You are a helpful assistant. Answer using only the context."},
    {"role": "user", "content": "CONTEXT:\n--- Block 1 [sample.pdf \u00b7 page 1] ---\nChunk size is 1000 characters with 150 overlap.\n\nQUESTION:\nWhat is the chunk size?"},
]
enc = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", return_dict=True)
inputs = enc["input_ids"].to("cuda")
with torch.inference_mode():
    out = model.generate(input_ids=inputs, attention_mask=enc.get("attention_mask").to("cuda"),
                         max_new_tokens=128, do_sample=False, pad_token_id=tok.eos_token_id)
text = tok.decode(out[0][inputs.shape[-1]:], skip_special_tokens=True)
print("=== GREEDY OUTPUT ===")
print(repr(text))

msgs2 = [{"role": "user", "content": "Say hello in one short sentence."}]
enc2 = tok.apply_chat_template(msgs2, add_generation_prompt=True, return_tensors="pt", return_dict=True)
with torch.inference_mode():
    out2 = model.generate(input_ids=enc2["input_ids"].to("cuda"),
                          attention_mask=enc2.get("attention_mask").to("cuda"),
                          max_new_tokens=32, do_sample=False, pad_token_id=tok.eos_token_id)
print("=== PLAIN OUTPUT ===")
print(repr(tok.decode(out2[0][enc2["input_ids"].shape[-1]:], skip_special_tokens=True)))
