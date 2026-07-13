"""alin14 stack verification: CUDA visible, sm_86, a REAL bf16 matmul, transformers import."""
import json, os, sys

import torch

out = {}
out["torch"] = torch.__version__
out["cuda_build"] = torch.version.cuda
out["cuda_available"] = torch.cuda.is_available()
assert out["cuda_available"], "torch.cuda.is_available() is False"

out["device_count"] = torch.cuda.device_count()
out["visible"] = os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>")
out["device_name"] = torch.cuda.get_device_name(0)
cap = torch.cuda.get_device_capability(0)
out["capability"] = list(cap)
out["capability_is_8_6"] = (cap == (8, 6))
out["bf16_supported"] = torch.cuda.is_bf16_supported()

# A real bf16 matmul -- not a dtype declaration, an actual multiply we check numerically.
a = torch.randn(512, 512, device="cuda", dtype=torch.bfloat16)
b = torch.randn(512, 512, device="cuda", dtype=torch.bfloat16)
c = a @ b
torch.cuda.synchronize()
out["matmul_dtype"] = str(c.dtype)
out["matmul_shape"] = list(c.shape)
out["matmul_finite"] = bool(torch.isfinite(c).all().item())
# Correctness vs an fp32 reference: bf16 has ~3 decimal digits, so compare relatively.
ref = a.float() @ b.float()
rel = ((c.float() - ref).norm() / ref.norm()).item()
out["matmul_rel_err_vs_fp32"] = rel
out["matmul_ok"] = out["matmul_finite"] and rel < 1e-2

import transformers
out["transformers"] = transformers.__version__
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: F401
out["transformers_automodel_import"] = True

out["ALL_OK"] = bool(out["cuda_available"] and out["capability_is_8_6"]
                     and out["bf16_supported"] and out["matmul_ok"])

print(json.dumps(out, indent=2), flush=True)
d = os.path.expanduser("~/depthar_results")
os.makedirs(d, exist_ok=True)
with open(os.path.join(d, "verify_gpu_alin14.json"), "w") as f:
    json.dump(out, f, indent=2)
print("VERIFY_GREEN" if out["ALL_OK"] else "VERIFY_RED", flush=True)
sys.exit(0 if out["ALL_OK"] else 1)
