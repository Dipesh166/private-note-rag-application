import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
tok = AutoTokenizer.from_pretrained(MODEL)

sys_p = open("app/prompts/rag_prompts.py", encoding="utf-8").read()

long_ctx = ("--- Block 1 [AI Engineering.pdf \u00b7 page 92] ---\n" + ("Foundation models use so much data that there's a realistic concern we'll run out of internet data in the next few years. " * 40)) * 4

msgs = [
    {"role": "system", "content": sys_p[:2000]},
    {"role": "user", "content": f"CONTEXT:\n{long_ctx}\n\nQUESTION:\nWhat is the maximum upload size for this knowledge base?"},
]
enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
ids = enc["input_ids"].to("cuda")
am = enc["attention_mask"].to("cuda")
print("prompt token count:", ids.shape[-1])

for dtype, name in ((torch.float16, "fp16"), (torch.float32, "fp32")):
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=dtype, low_cpu_mem_usage=True)
    model.to("cuda").eval()
    with torch.inference_mode():
        out = model.generate(input_ids=ids, attention_mask=am, max_new_tokens=64,
                             do_sample=False, pad_token_id=tok.eos_token_id,
                             return_dict_in_generate=True, output_scores=True)
    seqs = out.sequences[0][ids.shape[-1]:]
    txt = tok.decode(seqs, skip_special_tokens=True)
    bad = sum(bool(torch.isinf(s).any() or torch.isnan(s).any()) for s in out.scores)
    m = max(float(s.abs().max()) for s in out.scores)
    print(f"[{name}] inf/nan score tensors: {bad}/{len(out.scores)} | max |logit|={m:.1f}")
    print(f"[{name}] output repr: {txt[:300]!r}")
    del model
    torch.cuda.empty_cache()
