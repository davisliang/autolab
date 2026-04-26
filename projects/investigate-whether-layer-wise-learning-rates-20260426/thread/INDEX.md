# Thread index

_6 artifacts_  

## Idea (1)

| id | author | summary |
|----|--------|---------|
| `IDEA-001` | orchestrator | investigate whether layer-wise learning rates help small MLPs on MNIST |

## Hypothesis (5)

| id | author | summary |
|----|--------|---------|
| `HYP-001` | user | Trust-region-style per-layer LR scaling outperforms uniform LR |
| `HYP-002` | idea-expander | Gradient-norm-inverse per-layer LR outperforms uniform LR on MNIST MLP |
| `HYP-003` | idea-expander | Geometric depth-decay LR (deeper layers = smaller LR) improves MNIST MLP accuracy |
| `HYP-004` | idea-expander | PID-controller per-layer LR (control-theory transplant) converges faster than Adam on MNIST MLP |
| `HYP-005` | idea-expander | Layer-wise LR reduces epochs needed to first reach 97% val accuracy vs uniform LR on MNIST MLP |
