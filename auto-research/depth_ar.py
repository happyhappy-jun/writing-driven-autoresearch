"""Depth-AR: predict a skipped block's residual update from the preceding depth trajectory.

Pre-norm block:  h_{l+1} = h_l + Delta_l,  Delta_l = F_l(h_l).

  Plain Skip   Delta_hat = 0
  Copy Update  Delta_hat = Delta_{l-1}
  Depth-AR(1)  Delta_hat = a_l Delta_{l-1}
  Depth-AR(2)  Delta_hat = a_l Delta_{l-1} + b_l Delta_{l-2}

Coefficients come from closed-form regression on FP64 streaming Gram accumulators;
hidden states are never stored (plan section 9).
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

import torch
import torch.nn as nn

EPS = 1e-8
METHODS = ("dense", "plain_skip", "copy", "depth_ar1", "depth_ar2",
           "var_a_normalized", "var_c_diag", "var_d_ar3", "var_ct_diag")


# --------------------------------------------------------------------------------------
# Wrapper
# --------------------------------------------------------------------------------------

@dataclass
class SkipPlan:
    """Which layers are replaced, by which predictor, with which coefficients."""
    method: str = "dense"                      # one of METHODS
    layers: tuple = ()                         # layer indices to replace
    coef: dict = field(default_factory=dict)   # idx -> (alpha,) or (alpha, beta)

    def replaces(self, idx: int) -> bool:
        return self.method != "dense" and idx in self.layers


class _Ctx:
    """Per-forward state: rolling window of the last three residual updates, plus stats."""

    def __init__(self):
        self.win = []           # [Delta_{l-1}, Delta_{l-2}, Delta_{l-3}], most recent first
        self.returns_tuple = None
        self.acc = None         # Accumulators, or None to disable stat collection
        self.mask = None        # [B,T] bool, True = real token
        self.trace = None       # {idx: (h_in, delta)} for the boundary check only

    def reset(self):
        self.win = []

    def push(self, delta):
        self.win.insert(0, delta)
        del self.win[3:]

    @property
    def prev(self):
        return self.win[0] if len(self.win) > 0 else None

    @property
    def prev2(self):
        return self.win[1] if len(self.win) > 1 else None


class DepthARLayer(nn.Module):
    """Wraps one decoder block. Dense mode returns the block's output bit-for-bit."""

    def __init__(self, inner: nn.Module, idx: int, ctx: _Ctx, plan_box: list):
        super().__init__()
        self.inner = inner
        self.idx = idx
        self.ctx = ctx
        self.plan_box = plan_box  # single-element list so the plan can be swapped in place

    @property
    def plan(self) -> SkipPlan:
        return self.plan_box[0]

    def _predict(self, h):
        m, ctx = self.plan.method, self.ctx
        if m == "plain_skip" or ctx.prev is None:
            return torch.zeros_like(h)
        if m == "copy":
            return ctx.prev
        coef = self.plan.coef.get(self.idx)
        if coef is None:
            raise KeyError(f"no fitted coefficient for layer {self.idx} under {m}")

        if m == "var_a_normalized":          # s * Delta_{l-1}/||Delta_{l-1}||, per token
            u = ctx.prev / (ctx.prev.norm(dim=-1, keepdim=True) + EPS)
            return coef[0] * u
        if m == "var_c_diag":                # a (vector) elementwise-* Delta_{l-1}
            return coef.to(h.dtype) * ctx.prev
        if m == "var_ct_diag":
            # Cross-token: Delta_hat_l(t) = a . Delta_{l-1}(t) + b . Delta_{l-1}(t-1)
            # The t-1 term is zero at t=0 (no preceding token), so position 0 falls back to
            # the within-token term alone -- the same convention used when fitting.
            a_, b_ = coef
            prev = ctx.prev
            shifted = torch.zeros_like(prev)
            shifted[:, 1:] = prev[:, :-1]
            return a_.to(h.dtype) * prev + b_.to(h.dtype) * shifted

        # AR(p): truncates to however many real updates exist at this depth.
        p = {"depth_ar1": 1, "depth_ar2": 2, "var_d_ar3": 3}[m]
        out = None
        for j in range(min(p, len(ctx.win))):
            term = coef[j] * ctx.win[j]
            out = term if out is None else out + term
        return out

    def forward(self, hidden_states, **kw):
        ctx = self.ctx
        h = hidden_states

        if self.plan.replaces(self.idx):
            delta = self._predict(h)
            out_h = h + delta
            ctx.push(delta)
            return (out_h,) if ctx.returns_tuple else out_h

        out = self.inner(hidden_states, **kw)
        is_tuple = isinstance(out, tuple)
        if ctx.returns_tuple is None:
            ctx.returns_tuple = is_tuple
        out_h = out[0] if is_tuple else out

        # Delta is only observed; it is never fed back into the dense path, so dense
        # output stays bit-identical to the unwrapped model.
        delta = out_h - h
        if ctx.acc is not None:
            ctx.acc.observe_win(self.idx, h, delta, ctx.win, ctx.mask)
        if ctx.trace is not None:
            ctx.trace[self.idx] = (h.detach(), delta.detach())
        ctx.push(delta)
        return out


class DepthARModel:
    """Wraps a causal LM in place. Swap `.plan` between forwards; no re-wrapping."""

    def __init__(self, model, layers_attr="model.layers"):
        self.model = model
        self.ctx = _Ctx()
        self.plan_box = [SkipPlan()]
        obj = model
        for part in layers_attr.split("."):
            obj = getattr(obj, part)
        self.layer_list = obj
        self.n_layers = len(obj)
        for i in range(self.n_layers):
            obj[i] = DepthARLayer(obj[i], i, self.ctx, self.plan_box)

    @property
    def plan(self) -> SkipPlan:
        return self.plan_box[0]

    @plan.setter
    def plan(self, p: SkipPlan):
        self.plan_box[0] = p

    def eligible_layers(self):
        """Never layer 0 (no preceding update) and never the last layer (persona 7)."""
        return list(range(1, self.n_layers - 1))

    def forward(self, input_ids, attention_mask, acc=None, trace=None):
        self.ctx.reset()
        self.ctx.acc = acc
        self.ctx.trace = trace
        self.ctx.mask = attention_mask.bool()
        out = self.model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False)
        self.ctx.acc = None
        self.ctx.trace = None
        return out.logits


# --------------------------------------------------------------------------------------
# FP64 streaming accumulators  (plan section 9)
# --------------------------------------------------------------------------------------

class Accumulators:
    """Per-layer FP64 streaming sufficient statistics. No hidden state is retained.

    For layer l, with lags x_j = Delta_{l-1-j} (j=0,1,2) and target y = Delta_l:
        G[j,k] = sum <x_j, x_k>        (3x3 Gram)
        b[j]   = sum <x_j, y>
        C      = sum <y,y>
    One dense pass therefore fits AR(1), AR(2), AR(3), and both cheap variants:
        sA     = sum <y, x_0/||x_0||>  -> Variant A (normalized direction)
        pc_num/pc_den (per channel)    -> Variant C (diagonal)
    """

    SCALARS = ("C", "cos", "relmag", "n", "sA")

    def __init__(self, n_layers: int, d_model: int | None = None, device="cpu"):
        self.n_layers = n_layers
        self.d_model = d_model
        self.s = {i: {k: 0.0 for k in self.SCALARS} for i in range(n_layers)}
        self.G = {i: torch.zeros(3, 3, dtype=torch.float64) for i in range(n_layers)}
        self.b = {i: torch.zeros(3, dtype=torch.float64) for i in range(n_layers)}
        self.pc_num = {i: None for i in range(n_layers)}   # lazily sized to d_model
        self.pc_den = {i: None for i in range(n_layers)}
        # cross-token per-channel 2x2 system: x0 = Delta_{l-1}(t), x1 = Delta_{l-1}(t-1)
        self.ct = {i: None for i in range(n_layers)}       # dict of d-vectors

    @staticmethod
    def _dot(a, b, mask):
        return (a.float() * b.float()).sum(-1)[mask].double().sum().item()

    def observe(self, idx, h, delta, prev, prev2, mask):
        """`prev`/`prev2` are unused: the rolling window arrives via observe_win."""
        raise RuntimeError("use observe_win")

    def observe_win(self, idx, h, delta, win, mask):
        s = self.s[idx]
        s["n"] += int(mask.sum().item())
        s["C"] += self._dot(delta, delta, mask)

        dn = delta.float().norm(dim=-1)
        hn = h.float().norm(dim=-1)
        s["relmag"] += (dn[mask] / (hn[mask] + EPS)).double().sum().item()
        if not win:
            return

        for j, xj in enumerate(win):
            self.b[idx][j] += self._dot(xj, delta, mask)
            for k, xk in enumerate(win):
                if k >= j:
                    v = self._dot(xj, xk, mask)
                    self.G[idx][j, k] += v
                    if k != j:
                        self.G[idx][k, j] += v

        x0 = win[0]
        x0n = x0.float().norm(dim=-1)
        s["cos"] += (((x0.float() * delta.float()).sum(-1) /
                      (x0n * dn + EPS))[mask]).double().sum().item()
        # Variant A: <y, unit(x0)> summed; the optimal scale is sA / n.
        u = x0.float() / (x0n.unsqueeze(-1) + EPS)
        s["sA"] += (u * delta.float()).sum(-1)[mask].double().sum().item()

        # Variant C: per-channel least squares, one scalar per channel.
        m = mask.unsqueeze(-1)
        xf, yf = x0.float() * m, delta.float() * m
        num = (xf * yf).sum(dim=(0, 1)).double()
        den = (xf * xf).sum(dim=(0, 1)).double()
        if self.pc_num[idx] is None:
            self.pc_num[idx] = torch.zeros_like(num)
            self.pc_den[idx] = torch.zeros_like(den)
        self.pc_num[idx] += num
        self.pc_den[idx] += den

        # -- cross-token: one 2x2 normal system per channel -----------------------------
        # x1 is x0 shifted one token later; position 0 has no predecessor, so it is
        # excluded from the fit via `m1` rather than being fed a zero it would learn from.
        x1 = torch.zeros_like(x0)
        x1[:, 1:] = x0[:, :-1]
        m1 = mask.clone()
        m1[:, 0] = False                      # no t-1 at the first position
        m1 = m1 & torch.cat([torch.zeros_like(mask[:, :1]), mask[:, :-1]], 1)  # t-1 real too
        mm = m1.unsqueeze(-1)
        x0f, x1f, yf2 = x0.float() * mm, x1.float() * mm, delta.float() * mm
        if self.ct[idx] is None:
            self.ct[idx] = {k: torch.zeros(x0.shape[-1], dtype=torch.float64,
                                           device=x0.device)
                            for k in ("S00", "S01", "S11", "T0", "T1")}
        c = self.ct[idx]
        c["S00"] += (x0f * x0f).sum(dim=(0, 1)).double()
        c["S01"] += (x0f * x1f).sum(dim=(0, 1)).double()
        c["S11"] += (x1f * x1f).sum(dim=(0, 1)).double()
        c["T0"] += (x0f * yf2).sum(dim=(0, 1)).double()
        c["T1"] += (x1f * yf2).sum(dim=(0, 1)).double()

    # -- closed-form fits -------------------------------------------------------------

    def _solve(self, idx, p):
        """Ridge solve of the leading pxp system. Degrades gracefully if rank-deficient."""
        G = self.G[idx][:p, :p].clone()
        b = self.b[idx][:p].clone()
        tr = torch.diagonal(G).sum().item()
        if tr <= 0:
            return tuple([0.0] * p)
        G += torch.eye(p, dtype=torch.float64) * (1e-6 * tr / p)
        try:
            x = torch.linalg.solve(G, b)
        except Exception:
            x = torch.linalg.lstsq(G, b.unsqueeze(-1)).solution.squeeze(-1)
        return tuple(x.tolist())

    def fit_ar1(self, idx) -> float:
        return self._solve(idx, 1)[0]

    def fit_ar2(self, idx):
        return self._solve(idx, 2)

    def fit_ar3(self, idx):
        return self._solve(idx, 3)

    def fit_normalized(self, idx):
        s = self.s[idx]
        return (s["sA"] / s["n"],) if s["n"] else (0.0,)

    def fit_diag(self, idx, ridge: float = 1e-2):
        """Per-channel ridge: a_c = num_c / (den_c + lambda), lambda = ridge * mean_c(den_c).

        Without the ridge, channels carrying almost no update energy still get a coefficient
        (num/den of two tiny numbers), which produces |a_c| in the tens and lets a skipped
        layer amplify noise instead of predicting signal. The ridge is scaled to the layer's
        own mean channel energy so a single global `ridge` transfers across layers and models.
        """
        num, den = self.pc_num[idx], self.pc_den[idx]
        if num is None:
            return None
        lam = ridge * den.mean()
        return (num / (den + lam + 1e-12)).float()

    def fit_crosstoken(self, idx, ridge: float = 1e-2):
        """Per-channel closed-form 2x2 ridge solve.

        For each channel c independently:
            [S00 + lam,  S01      ] [a]   [T0]
            [S01,        S11 + lam] [b] = [T1]
        lam is scaled to the channel-mean energy, as in fit_diag, so one global `ridge`
        transfers across layers and models. Solved in closed form, no iteration.
        """
        c = self.ct[idx]
        if c is None:
            return None
        lam = ridge * (c["S00"].mean() + c["S11"].mean()) / 2.0
        s00, s11, s01 = c["S00"] + lam, c["S11"] + lam, c["S01"]
        det = s00 * s11 - s01 * s01
        det = torch.where(det.abs() < 1e-12, torch.full_like(det, 1e-12), det)
        a = (s11 * c["T0"] - s01 * c["T1"]) / det
        b = (s00 * c["T1"] - s01 * c["T0"]) / det
        return a.float(), b.float()

    def predictability_crosstoken(self, idx, coef) -> float:
        """||y - a.x0 - b.x1||^2 from the accumulated per-channel statistics only."""
        C = self.s[idx]["C"]
        c = self.ct[idx]
        if C <= 0.0 or c is None:
            return float("nan")
        a, b = (x.double().to(c["S00"].device) for x in coef)
        resid = (C
                 - 2.0 * ((a * c["T0"]).sum() + (b * c["T1"]).sum()).item()
                 + (a * a * c["S00"]).sum().item()
                 + 2.0 * (a * b * c["S01"]).sum().item()
                 + (b * b * c["S11"]).sum().item())
        return 1.0 - resid / C

    # -- held-out scores ---------------------------------------------------------------

    def predictability(self, idx, coef) -> float:
        """P_l = 1 - sum||Delta_l - Delta_hat||^2 / sum||Delta_l||^2, from statistics only."""
        C = self.s[idx]["C"]
        if C <= 0.0:
            return float("nan")
        p = len(coef)
        a = torch.tensor(coef, dtype=torch.float64)
        G = self.G[idx][:p, :p]
        b = self.b[idx][:p]
        resid = C - 2.0 * (a @ b).item() + (a @ G @ a).item()
        return 1.0 - resid / C

    def predictability_normalized(self, idx, coef) -> float:
        """||y - s*u||^2 = C - 2 s <y,u> + s^2 n,  since ||u||=1 per token."""
        s_, C, n = self.s[idx], self.s[idx]["C"], self.s[idx]["n"]
        if C <= 0.0:
            return float("nan")
        sc = coef[0]
        return 1.0 - (C - 2.0 * sc * s_["sA"] + sc * sc * n) / C

    def predictability_diag(self, idx, a) -> float:
        """||y - a*x0||^2 = C - 2 sum_c a_c num_c + sum_c a_c^2 den_c."""
        C = self.s[idx]["C"]
        num, den = self.pc_num[idx], self.pc_den[idx]
        if C <= 0.0 or num is None:
            return float("nan")
        ad = a.double().to(num.device)
        resid = C - 2.0 * (ad * num).sum().item() + (ad * ad * den).sum().item()
        return 1.0 - resid / C

    def cosine(self, idx) -> float:
        s = self.s[idx]
        return s["cos"] / s["n"] if s["n"] else float("nan")

    def rel_magnitude(self, idx) -> float:
        s = self.s[idx]
        return s["relmag"] / s["n"] if s["n"] else float("nan")


# --------------------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------------------

@torch.no_grad()
def eval_nll(dm: DepthARModel, batches, acc=None, chunk: int = 256) -> float:
    """Mean next-token NLL over non-padding targets only.

    The softmax is taken over sequence chunks rather than the whole tensor at once. Qwen's
    vocabulary is ~152k, so casting a [B,T,V] logit tensor to fp32 in one go costs GBs and
    OOMs a 24GB card at 7B. Chunking changes the arithmetic not at all -- each target's NLL
    is computed from its own row of logits -- but it caps peak memory at B*chunk*V.
    """
    total, count = 0.0, 0
    for ids, mask in batches:
        logits = dm.forward(ids, mask, acc=acc)
        tgt = ids[:, 1:]
        # A target counts only if both it and its context position are real tokens.
        valid = (mask[:, 1:] * mask[:, :-1]).bool()
        n_pred = tgt.shape[1]
        for s in range(0, n_pred, chunk):
            e = min(s + chunk, n_pred)
            # logits[:, i] predicts ids[:, i+1] == tgt[:, i]
            lp = torch.log_softmax(logits[:, s:e].float(), dim=-1)
            nll = -lp.gather(-1, tgt[:, s:e].unsqueeze(-1)).squeeze(-1)
            v = valid[:, s:e]
            total += nll[v].double().sum().item()
            count += int(v.sum().item())
            del lp, nll
        del logits
    return total / count


@torch.no_grad()
def collect_stats(dm: DepthARModel, batches) -> Accumulators:
    """One dense pass; fills FP64 Gram accumulators for every layer."""
    acc = Accumulators(dm.n_layers)
    dm.plan = SkipPlan()  # dense
    for ids, mask in batches:
        dm.forward(ids, mask, acc=acc)
    return acc


def select_non_adjacent(scores: dict, k: int, min_gap: int = 2) -> list:
    """Top-k by score with at least one surviving layer between skips (persona section 2).

    min_gap=2 means selected indices differ by >= 2, i.e. layer l and l+1 are never both cut.
    """
    chosen = []
    for idx in sorted(scores, key=lambda i: scores[i], reverse=True):
        if all(abs(idx - c) >= min_gap for c in chosen):
            chosen.append(idx)
        if len(chosen) == k:
            break
    return sorted(chosen)


def recovery_nll(l_ar: float, l_dense: float, l_skip: float) -> float:
    """1 - (L_AR - L_dense) / (L_skip - L_dense)   (plan section 7)."""
    denom = l_skip - l_dense
    if abs(denom) < 1e-12:
        return float("nan")
    return 1.0 - (l_ar - l_dense) / denom


def write_result(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path
