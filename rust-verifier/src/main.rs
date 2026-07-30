use serde::Deserialize;
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::process;

const TOLERANCE: f64 = 2e-9;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Artifact {
    schema: String,
    n: usize,
    budget: usize,
    requested_budget: usize,
    eta: f64,
    average_cost: f64,
    max_cost: f64,
    objective: f64,
    lower_bound: f64,
    absolute_gap: f64,
    relative_gap_to_upper: f64,
    bound_type: String,
    beam_width: usize,
    candidate_limit: usize,
    per_key_costs: Vec<u64>,
    tree: Value,
    weights: Vec<f64>,
}

fn close(left: f64, right: f64) -> bool {
    (left - right).abs() <= TOLERANCE * left.abs().max(right.abs()).max(1.0)
}

fn interval_cost(width: usize) -> u64 {
    if width <= 1 {
        return 0;
    }
    usize::BITS as u64 - (width - 1).leading_zeros() as u64
}

fn exact_usize(value: &Value, label: &str) -> Result<usize, String> {
    value
        .as_u64()
        .and_then(|item| usize::try_from(item).ok())
        .ok_or_else(|| format!("{label} must be a non-negative integer"))
}

fn tree_costs(
    node: &Value,
    left: usize,
    right: usize,
    depth: u64,
) -> Result<(Vec<u64>, usize), String> {
    let object = node
        .as_object()
        .ok_or_else(|| "tree node must be an object".to_string())?;
    let interval = object
        .get("interval")
        .and_then(Value::as_array)
        .ok_or_else(|| "tree interval is missing".to_string())?;
    if interval.len() != 2
        || exact_usize(&interval[0], "interval left")? != left
        || exact_usize(&interval[1], "interval right")? != right
    {
        return Err("tree interval mismatch".to_string());
    }
    match object.get("type").and_then(Value::as_str) {
        Some("leaf") => {
            if object.len() != 2 {
                return Err("malformed leaf".to_string());
            }
            let cost = depth + interval_cost(right - left + 1);
            Ok((vec![cost; right - left + 1], 0))
        }
        Some("split") => {
            if object.len() != 5 {
                return Err("malformed split".to_string());
            }
            let threshold = exact_usize(
                object
                    .get("threshold")
                    .ok_or_else(|| "split threshold is missing".to_string())?,
                "threshold",
            )?;
            if threshold < left || threshold >= right {
                return Err("invalid threshold".to_string());
            }
            let (mut left_costs, left_splits) = tree_costs(
                object
                    .get("left")
                    .ok_or_else(|| "left child is missing".to_string())?,
                left,
                threshold,
                depth + 1,
            )?;
            let (right_costs, right_splits) = tree_costs(
                object
                    .get("right")
                    .ok_or_else(|| "right child is missing".to_string())?,
                threshold + 1,
                right,
                depth + 1,
            )?;
            left_costs.extend(right_costs);
            Ok((left_costs, 1 + left_splits + right_splits))
        }
        _ => Err("unknown tree node".to_string()),
    }
}

fn verify(artifact: &Artifact) -> Result<Value, String> {
    if artifact.schema != "certigap-pruned-beam-v1" {
        return Err("unsupported schema".to_string());
    }
    if artifact.bound_type != "entropy_maxcost" {
        return Err("unsupported lower-bound type".to_string());
    }
    if artifact.n == 0
        || artifact.weights.len() != artifact.n
        || artifact.per_key_costs.len() != artifact.n
        || artifact.budget >= artifact.n
        || artifact.requested_budget < artifact.budget
        || artifact.beam_width == 0
        || artifact.candidate_limit < 4
        || !artifact.eta.is_finite()
        || !(0.0..=1.0).contains(&artifact.eta)
    {
        return Err("invalid problem dimensions".to_string());
    }
    if artifact
        .weights
        .iter()
        .any(|weight| !weight.is_finite() || *weight < 0.0)
    {
        return Err("weights must be finite and non-negative".to_string());
    }
    let total: f64 = artifact.weights.iter().sum();
    if !total.is_finite() || total <= 0.0 {
        return Err("weights must have positive mass".to_string());
    }
    let (costs, split_count) = tree_costs(&artifact.tree, 1, artifact.n, 0)?;
    if split_count > artifact.budget || costs != artifact.per_key_costs {
        return Err("tree costs or budget do not replay".to_string());
    }
    let normalized: Vec<f64> = artifact
        .weights
        .iter()
        .map(|weight| weight / total)
        .collect();
    let average: f64 = normalized
        .iter()
        .zip(costs.iter())
        .map(|(weight, cost)| weight * *cost as f64)
        .sum();
    let maximum = *costs
        .iter()
        .max()
        .ok_or_else(|| "empty cost vector".to_string())? as f64;
    let objective = (1.0 - artifact.eta) * average + artifact.eta * maximum;
    let entropy: f64 = normalized
        .iter()
        .filter(|weight| **weight > 0.0)
        .map(|weight| -weight * weight.log2())
        .sum();
    let largest_leaf = (artifact.n + artifact.budget) / (artifact.budget + 1);
    let raw_lower =
        (1.0 - artifact.eta) * entropy + artifact.eta * interval_cost(largest_leaf) as f64;
    let lower = raw_lower.min(objective);
    let absolute_gap = (objective - lower).max(0.0);
    let relative_gap = absolute_gap / objective.abs().max(1e-12);
    let comparisons = [
        ("average_cost", artifact.average_cost, average),
        ("max_cost", artifact.max_cost, maximum),
        ("objective", artifact.objective, objective),
        ("lower_bound", artifact.lower_bound, lower),
        ("absolute_gap", artifact.absolute_gap, absolute_gap),
        (
            "relative_gap_to_upper",
            artifact.relative_gap_to_upper,
            relative_gap,
        ),
    ];
    for (field, supplied, expected) in comparisons {
        if !supplied.is_finite() || !close(supplied, expected) {
            return Err(format!("{field} does not replay"));
        }
    }
    Ok(json!({
        "verified": true,
        "artifact_type": artifact.schema,
        "split_count": split_count,
        "upper_bound": objective,
        "lower_bound": lower,
        "absolute_gap": absolute_gap,
        "relative_gap_to_upper": relative_gap,
        "scope": "feasible heuristic and information-theoretic lower bound; no approximation ratio"
    }))
}

fn run() -> Result<(), String> {
    let path = env::args()
        .nth(1)
        .ok_or_else(|| "usage: certigap-verifier ARTIFACT.json".to_string())?;
    let raw = fs::read_to_string(&path).map_err(|error| format!("cannot read {path}: {error}"))?;
    let artifact: Artifact =
        serde_json::from_str(&raw).map_err(|error| format!("invalid artifact JSON: {error}"))?;
    let result = verify(&artifact)?;
    println!(
        "{}",
        serde_json::to_string_pretty(&result).map_err(|error| error.to_string())?
    );
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("certigap-verifier: error: {error}");
        process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn singleton_artifact() -> Artifact {
        Artifact {
            schema: "certigap-pruned-beam-v1".to_string(),
            n: 1,
            budget: 0,
            requested_budget: 0,
            eta: 0.2,
            average_cost: 0.0,
            max_cost: 0.0,
            objective: 0.0,
            lower_bound: 0.0,
            absolute_gap: 0.0,
            relative_gap_to_upper: 0.0,
            bound_type: "entropy_maxcost".to_string(),
            beam_width: 1,
            candidate_limit: 4,
            per_key_costs: vec![0],
            tree: json!({"type": "leaf", "interval": [1, 1]}),
            weights: vec![1.0],
        }
    }

    #[test]
    fn accepts_replayable_singleton() {
        let result = verify(&singleton_artifact()).expect("valid artifact");
        assert_eq!(result["verified"], true);
        assert_eq!(result["split_count"], 0);
    }

    #[test]
    fn rejects_tampered_cost_vector() {
        let mut artifact = singleton_artifact();
        artifact.per_key_costs[0] = 1;
        assert!(verify(&artifact).is_err());
    }

    #[test]
    fn rejects_unknown_json_fields() {
        let raw = r#"{
          "schema":"certigap-pruned-beam-v1","n":1,"budget":0,
          "requested_budget":0,"eta":0.2,"average_cost":0.0,
          "max_cost":0.0,"objective":0.0,"lower_bound":0.0,
          "absolute_gap":0.0,"relative_gap_to_upper":0.0,
          "bound_type":"entropy_maxcost","beam_width":1,"candidate_limit":4,
          "per_key_costs":[0],
          "tree":{"type":"leaf","interval":[1,1]},"weights":[1.0],
          "unexpected":true
        }"#;
        assert!(serde_json::from_str::<Artifact>(raw).is_err());
    }
}
