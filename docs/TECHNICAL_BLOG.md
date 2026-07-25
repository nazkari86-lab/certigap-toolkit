# Technical Blog Draft

## Title

CertiGap: A Search Structure That Decides How Much Order Is Worth Building

## Hook

Most search structures assume the goal is to organize *all* keys well.
CertiGap asks a different question:

> If you only have a small structural budget, which parts of the order are actually worth materializing?

## Main Idea

Instead of fully refining the entire key space, CertiGap builds a partial search tree.
Some regions are resolved with explicit splits; others remain interval leaves and fall back to local binary search only when needed.

This is useful when:

- the workload is skewed;
- hot keys matter more than cold keys;
- you cannot afford a full high-quality structure.

## Why Greedy Is Not Enough

Local greedy splitting can miss the right preparatory split.
Our counterexample search already finds cases where greedy is much worse than exact, while beam search recovers the optimum.

## What The Prototype Delivers

- exact frontier DP;
- beam-search heuristic;
- certificates with lower and upper bounds;
- speed/quality tradeoff benchmarks;
- English and Russian competition packages.

## Simple Takeaway

If budget is tight and queries are skewed, the right question is not
"how do I optimize the full tree?"
but
"how much of the order should I even bother materializing?"
