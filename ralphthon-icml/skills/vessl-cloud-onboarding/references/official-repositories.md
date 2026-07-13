# Official VESSL Resources

Use current `vessl-ai` repositories and `docs.cloud.vessl.ai` for implementation guidance. Verify a live command before running it because CLI and inventory details can change.

## Autoresearch source of truth

- Cookbook repository: <https://github.com/vessl-ai/vessl-cloud-cookbook>
- Autoresearch recipe: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/autoresearch>
- Ralphthon pin: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/97a0af14b0acae042162b1f70f17fbe2d570afa2/autoresearch>
- Official walkthrough: <https://docs.cloud.vessl.ai/examples/autoresearch>

At the Ralphthon pin, the recipe keeps Karpathy's `prepare.py` and baseline `train.py` unchanged and adds VESSL `vesslctl job create` wrappers, an object-volume cache, Job polling, and log retrieval. Its published benchmark targets H100. Ralphthon does not edit that benchmark; it explicitly selects a live single-A100 spec and treats A100 results as a separate environment.

## More current cookbook material

- Cookbook index: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main>
- Gemma 4 fine-tuning: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/gemma4-finetuning>
- GPU cost benchmark: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/gpu-cost-benchmark>
- AQR finance workflow: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/aqr-finance>
- Recipe template: <https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/_template>
- VESSL AI GitHub organization: <https://github.com/vessl-ai>

Treat these as optional examples, not automatic dependencies of autoresearch. Review their licenses, versions, side effects, and compute assumptions before reuse.

## More public VESSL AI repositories

The organization also publishes material outside the main cookbook. These links are for discovery, not an execution SOT for this campaign:

- Physical AI hackathon demo: <https://github.com/vessl-ai/physical-ai-hackathon-demo>
- Multi-node NCCL example: <https://github.com/vessl-ai/nccl-multinode-example>
- Kubernetes/VESSL Cloud integration patterns: <https://github.com/vessl-ai/vessl-cloud-integration>
- MCP tool orchestrator: <https://github.com/vessl-ai/mcpctl>
- Agent toolkit examples: <https://github.com/vessl-ai/hyperpocket>
- AI-agent research material: <https://github.com/vessl-ai/ai-agent-research>

Check each repository's current README, license, maintenance status, product generation, and cost model before reuse. None of them overrides the pinned autoresearch recipe or current `vesslctl` documentation.

## Agent and documentation integrations

- AI tools guide: <https://docs.cloud.vessl.ai/cli/ai-tools>
- VESSL documentation MCP: <https://docs.cloud.vessl.ai/mcp>
- Secrets overview: <https://docs.cloud.vessl.ai/admin/secrets/overview>

The current CLI can expose its agent skill metadata with `vesslctl skill show --output json` and install it with `vesslctl skill install --target cross-client`. Installation changes user-level tool configuration, so explain the change and obtain confirmation before running it. The Ralphthon skills remain usable without installing that extra skill.

## Legacy—not an execution SOT

Older repositories such as <https://github.com/vessl-ai/examples> and <https://github.com/vessl-ai/vessl-training-recipes> can contain useful historical examples, including legacy W&B environment patterns. Do not use them as the current VESSL Cloud source of truth and do not copy legacy `vessl` CLI, MLOps Organization/Project, or raw `WANDB_KEY` patterns into this workflow. Current execution uses `cloud.vessl.ai` and `vesslctl`.
