"""Pull models + corpus. 7B FIRST -- it is the long pole (~15GB); everything else trails."""
import sys, time
from huggingface_hub import snapshot_download

# Skip redundant weight formats; Qwen2.5 ships safetensors.
IGNORE = ["*.bin", "*.pth", "*.msgpack", "*.h5", "*.onnx"]

JOBS = [
    ("Qwen/Qwen2.5-7B", "model", None, IGNORE),
    ("Qwen/Qwen2.5-1.5B", "model", None, IGNORE),
    ("Salesforce/wikitext", "dataset",
     ["wikitext-103-raw-v1/*", "wikitext-2-raw-v1/*"], None),
]

for repo, kind, pats, ig in JOBS:
    t = time.time()
    try:
        p = snapshot_download(repo_id=repo, repo_type=kind, allow_patterns=pats,
                              ignore_patterns=ig, max_workers=8)
        print(f"OK {repo} ({time.time()-t:.0f}s) -> {p}", flush=True)
    except Exception as e:
        print(f"FAIL {repo}: {e}", flush=True)
print("FETCH_DONE", flush=True)
