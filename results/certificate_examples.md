# CertiGap Certificate Examples

## zipf, n=8, B=2, eta=0.15

- Upper bound: `2.879325`
- Lower bound: `2.526758`
- Reported entropy-bound gap: `0.139534`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 8], 'threshold': 2}, {'interval': [3, 8], 'threshold': 4}]`

## hot_middle, n=12, B=3, eta=0.15

- Upper bound: `3.291667`
- Lower bound: `2.694186`
- Reported entropy-bound gap: `0.221767`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 12], 'threshold': 6}, {'interval': [7, 12], 'threshold': 8}, {'interval': [1, 6], 'threshold': 4}]`

## hot_tail, n=16, B=4, eta=0.30

- Upper bound: `3.854545`
- Lower bound: `2.894329`
- Reported entropy-bound gap: `0.331758`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 16], 'threshold': 13}, {'interval': [14, 16], 'threshold': 14}, {'interval': [1, 13], 'threshold': 8}, {'interval': [9, 13], 'threshold': 12}]`

