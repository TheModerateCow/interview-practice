def longest_compliant_window(requests: list[int], errors: list[int], budget_ppm: int) -> int:
    n = len(requests)
    # Minute i weighs errors*1e6 - requests*budget; a window is compliant when its weights sum to <= 0,
    # i.e. prefix[j] <= prefix[i] for the window covering minutes i..j-1.
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + errors[i] * 1_000_000 - requests[i] * budget_ppm
    # Only a running maximum of prefix can be the best start: an earlier start that is at least as high wins.
    starts: list[int] = []
    for i in range(n + 1):
        if not starts or prefix[i] > prefix[starts[-1]]:
            starts.append(i)
    best = 0
    for j in range(n, -1, -1):
        while starts and prefix[starts[-1]] >= prefix[j]:
            best = max(best, j - starts.pop())
        if not starts:
            break
    return best
