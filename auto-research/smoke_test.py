"""Offline smoke: 3 candidates, one of which crashes."""
import obs

session = obs.new_session_id()
print("session:", session)

@obs.op
def evaluate(candidate: int) -> float:
    if candidate == 2:
        raise RuntimeError("simulated experiment crash")
    return 1.0 - candidate * 0.1

for i in range(1, 4):
    try:
        with obs.candidate_run(
            session_id=session, iteration=i,
            hypothesis=f"candidate {i}: lower lr",
            objective_name="val_bpb",
            config={"seed": 0, "lr": 0.01 * i},
        ) as run:
            score = evaluate(i)
            run.log({"objective/value": score, "loop/iteration": i})
            run.summary["objective/final"] = score
    except RuntimeError as e:
        print(f"  iter {i} failed as expected: {e}")
