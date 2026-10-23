"""
threshold_test.py  -  MEMBER 2: Task 3, the threshold experiment.
Run:   python threshold_test.py
Tries different thresholds on all 24 test questions and shows what goes wrong at each one.

  false answer  = the question has NO answer in the records, but the app answered anyway
  missed answer = the answer IS in the records, but the app said "not found"
  wrong source  = the app answered, but with the wrong kind of document
"""

from test_search import ORIGINAL, NEW, logic

CASES = ORIGINAL + NEW
THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.30]

print(f"{'threshold':>9} | {'accuracy':>9} | {'false answers':>13} | {'missed answers':>14} | {'wrong source':>12}")
print("-" * 70)
for t in THRESHOLDS:
    correct = false_answer = missed = wrong_source = 0
    for pid, question, expected in CASES:
        results = logic.search_documents(pid, question, threshold=t)
        got = results[0]["doc"]["type"] if results else None
        if got == expected:
            correct += 1
        elif expected is None:
            false_answer += 1
        elif got is None:
            missed += 1
        else:
            wrong_source += 1
    print(f"{t:>9.2f} | {correct:>2}/{len(CASES)} {correct / len(CASES) * 100:>3.0f}% | "
          f"{false_answer:>13} | {missed:>14} | {wrong_source:>12}")
