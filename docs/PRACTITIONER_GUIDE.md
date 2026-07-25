# Practitioner Guide

## Simple Story

When memory or split budget is tight and access is skewed, CertiGap beats naive structures by spending structural effort only where requests are concentrated.

## When CertiGap Wins

- read-heavy workloads;
- hot/cold key distributions;
- static or slowly changing key sets;
- situations where a small structural budget must be focused carefully.

## When CertiGap Loses Or Is Unnecessary

- fully uniform access;
- frequently mutating data structures;
- systems where you can afford a full high-quality index anyway;
- teams that need ultra-simple constant-time construction rather than higher-quality planning.

## Three Ready Use Cases

1. Skewed key-value lookup:
   hot keys should get the cheapest paths.
2. Static hot/cold product catalog:
   popular items deserve more structure than rarely accessed ones.
3. Read-heavy embedded index:
   limited memory budget but predictable skew in queries.

## Why A Practitioner Might Care

- better quality than simple local heuristics;
- measurable tradeoff between quality and runtime;
- explicit certificate support on small and medium cases;
- reusable Python API and optional C++ core.
