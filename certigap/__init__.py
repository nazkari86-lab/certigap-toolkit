from .api import CertiGapToolkit, FitResult, baseline_learned_segment, solve_with
from .anytime_tv import anytime_tv_branch_and_bound
from .anytime_verifier import AnytimeVerificationError, verify_anytime_tv_certificate
from .autodro import (
    AutoDROFitResult,
    AutoDROVerificationError,
    CertiGapAutoDRO,
    ExecutionCostModel,
    UncertaintyModel,
    fit_autodro,
    multinomial_uncertainty,
    verify_autodro_selection_artifact,
    worst_case_tv_expectation,
)
from .autoindex import (
    AutoIndexConstraints,
    CompiledAutoIndex,
    TraceOperation,
    WorkloadTrace,
    compile_autoindex,
    analytical_portfolio_costs,
)
from .autoindex_verifier import (
    AutoIndexVerificationError,
    verify_autoindex_artifact,
)
from .tracking_autoindex import (
    TrackingAutoIndex,
    TrackingPolicy,
    start_tracking_autoindex,
)
from .tracking_autoindex_verifier import (
    TrackingAutoIndexVerificationError,
    verify_tracking_autoindex_certificate,
)
from .branch_and_bound import branch_and_bound_exact
from .cpp_bindings import CppCertiGap
from .direct_tv import enumerate_partial_trees, exact_tree_space_manifest
from .dynamic_range import DynamicCertiRange, RangeNode, RangeSnapshot
from .dynamic_range_verifier import (
    DynamicRangeVerificationError,
    verify_dynamic_range_certificate,
)
from .exact_verifier import verify_serialized_tree_exact
from .generalized import (
    evaluate_tree_with_fallback,
    fixed_rounds_profile,
    generalized_frontier_dp_best,
    midpoint_binary_profile,
)
from .hardware import calibrate_hardware, calibration_source_path
from .hybrid import (
    HybridConstraints,
    HybridIndex,
    PrefixBlockIndex,
    compile_hybrid_index,
    synthesize_hybrid_partitions,
)
from .hybrid_verifier import (
    HybridVerificationError,
    verify_hybrid_certificate,
)
from .online import (
    OnlineRegretCertificate,
    expectation_shift_bound,
    online_regret_certificate,
    total_variation_distance,
)
from .martingale_safe_autoindex import (
    MartingaleSafeCompiledAutoIndex,
    MartingaleSafeSelectionPolicy,
    compile_martingale_safe_autoindex,
)
from .martingale_safe_autoindex_verifier import (
    MartingaleSafeAutoIndexVerificationError,
    verify_martingale_safe_autoindex_certificate,
)
from .martingale_safe_compiler import (
    compile_martingale_safe_spec,
    generate_martingale_safe_cpp_header,
    load_martingale_safe_compile_spec,
)
from .measured_deployment import (
    MeasuredCompiledAutoIndex,
    MeasuredDeploymentPolicy,
    compile_measured_autoindex,
    paired_latency_decision,
)
from .measured_deployment_verifier import (
    MeasuredDeploymentVerificationError,
    verify_measured_deployment_artifact,
)
from .pruned_verifier import (
    PrunedBeamVerificationError,
    verify_pruned_beam_certificate,
)
from .range_optimizer import range_aware_beam_search, score_range_workload
from .range_optimizer_verifier import (
    RangeOptimizerVerificationError,
    make_range_optimizer_artifact,
    verify_range_optimizer_artifact,
)
from .safe_autoindex import (
    SafeCompiledAutoIndex,
    SafeSelectionPolicy,
    compile_safe_autoindex,
)
from .safe_autoindex_verifier import (
    SafeAutoIndexVerificationError,
    verify_safe_autoindex_certificate,
)
from .safe_compiler import (
    compile_safe_spec,
    generate_safe_cpp_header,
    load_safe_compile_spec,
)
from .sequential_safe_autoindex import (
    SequentialSafeCompiledAutoIndex,
    SequentialSafeSelectionPolicy,
    compile_sequential_safe_autoindex,
)
from .sequential_safe_autoindex_verifier import (
    SequentialSafeAutoIndexVerificationError,
    verify_sequential_safe_autoindex_certificate,
)
from .sequential_safe_compiler import (
    compile_sequential_safe_spec,
    generate_sequential_safe_cpp_header,
    load_sequential_safe_compile_spec,
)
from .sqlite_extension import (
    build_sqlite_extension,
    extension_source_path,
    virtual_table_source_path,
)
from .spec import AdaptiveSpec, compile_from_spec
from .dsl import (
    ProofCarryingIndex,
    ProofCarryingSpec,
    compile_proof_carrying_index,
)
from .dsl_verifier import DSLVerificationError, verify_dsl_certificate
from .delta import (
    DeltaSpec,
    ProofCarryingDeltaIndex,
    compile_proof_carrying_delta_index,
)
from .delta_verifier import DeltaVerificationError, verify_delta_certificate
from .adaptive_profile import (
    parse_adaptive_profile,
    parse_adaptive_profile_text,
)
from .adaptive_array import AdaptiveArray, AdaptiveArrayPolicy
from .synthesis import (
    HardwareProfile,
    SynthesisConstraints,
    SynthesizedIndex,
    VariableBlockIndex,
    compile_synthesized_index,
    migration_decision,
    synthesize_partitions,
)
from .synthesis_verifier import (
    SynthesisVerificationError,
    verify_synthesis_certificate,
)
from .core import (
    CertificateError,
    IntervalLeaf,
    SplitNode,
    all_budget_optima,
    baseline_balanced,
    baseline_weighted_median,
    beam_search_best,
    benchmark_case,
    brute_force_best,
    candidate_restricted_frontier_dp_best,
    combined_lower_bound,
    cost_cap_dp_best,
    counterexample_search,
    certify_tree,
    entropy_lower_bound,
    effective_budget,
    evaluate_tree,
    frontier_dp_best,
    greedy_best,
    heuristic_best,
    hot_block_distribution,
    interval_cost,
    lagrangian_lower_bound,
    make_distribution,
    mass_quantile_thresholds,
    max_cost_lower_bound,
    normalize_weights,
    power_of_two_greedy_family,
    split_count,
    validate_problem,
)
from .verifier import VerificationError, verify_branch_and_bound_certificate, verify_certificate_artifact, verify_tree
from .workload import CertiRangeWorkload

__all__ = [
    "CertificateError",
    "VerificationError",
    "IntervalLeaf",
    "SplitNode",
    "all_budget_optima",
    "anytime_tv_branch_and_bound",
    "AnytimeVerificationError",
    "AutoDROFitResult",
    "AutoDROVerificationError",
    "AutoIndexConstraints",
    "AutoIndexVerificationError",
    "analytical_portfolio_costs",
    "baseline_learned_segment",
    "baseline_balanced",
    "baseline_weighted_median",
    "beam_search_best",
    "branch_and_bound_exact",
    "benchmark_case",
    "brute_force_best",
    "candidate_restricted_frontier_dp_best",
    "build_sqlite_extension",
    "parse_adaptive_profile",
    "parse_adaptive_profile_text",
    "AdaptiveArray",
    "AdaptiveArrayPolicy",
    "AdaptiveSpec",
    "ProofCarryingIndex",
    "ProofCarryingSpec",
    "DSLVerificationError",
    "DeltaSpec",
    "ProofCarryingDeltaIndex",
    "DeltaVerificationError",
    "verify_dsl_certificate",
    "virtual_table_source_path",
    "CertiGapToolkit",
    "CompiledAutoIndex",
    "CertiRangeWorkload",
    "CertiGapAutoDRO",
    "combined_lower_bound",
    "cost_cap_dp_best",
    "counterexample_search",
    "compile_autoindex",
    "compile_from_spec",
    "compile_proof_carrying_index",
    "compile_proof_carrying_delta_index",
    "compile_martingale_safe_autoindex",
    "compile_measured_autoindex",
    "compile_martingale_safe_spec",
    "compile_safe_autoindex",
    "compile_safe_spec",
    "compile_sequential_safe_autoindex",
    "compile_sequential_safe_spec",
    "CppCertiGap",
    "certify_tree",
    "calibrate_hardware",
    "calibration_source_path",
    "entropy_lower_bound",
    "extension_source_path",
    "enumerate_partial_trees",
    "effective_budget",
    "evaluate_tree",
    "evaluate_tree_with_fallback",
    "ExecutionCostModel",
    "exact_tree_space_manifest",
    "DynamicCertiRange",
    "DynamicRangeVerificationError",
    "FitResult",
    "frontier_dp_best",
    "fixed_rounds_profile",
    "fit_autodro",
    "generalized_frontier_dp_best",
    "greedy_best",
    "heuristic_best",
    "hot_block_distribution",
    "HardwareProfile",
    "HybridConstraints",
    "HybridIndex",
    "HybridVerificationError",
    "interval_cost",
    "lagrangian_lower_bound",
    "make_distribution",
    "MartingaleSafeAutoIndexVerificationError",
    "MartingaleSafeCompiledAutoIndex",
    "MartingaleSafeSelectionPolicy",
    "MeasuredCompiledAutoIndex",
    "MeasuredDeploymentPolicy",
    "MeasuredDeploymentVerificationError",
    "max_cost_lower_bound",
    "mass_quantile_thresholds",
    "midpoint_binary_profile",
    "paired_latency_decision",
    "multinomial_uncertainty",
    "migration_decision",
    "normalize_weights",
    "OnlineRegretCertificate",
    "online_regret_certificate",
    "power_of_two_greedy_family",
    "PrefixBlockIndex",
    "PrunedBeamVerificationError",
    "RangeNode",
    "RangeSnapshot",
    "RangeOptimizerVerificationError",
    "range_aware_beam_search",
    "score_range_workload",
    "SafeAutoIndexVerificationError",
    "SafeCompiledAutoIndex",
    "SafeSelectionPolicy",
    "SequentialSafeAutoIndexVerificationError",
    "SequentialSafeCompiledAutoIndex",
    "SequentialSafeSelectionPolicy",
    "make_range_optimizer_artifact",
    "split_count",
    "SynthesisConstraints",
    "SynthesizedIndex",
    "SynthesisVerificationError",
    "synthesize_partitions",
    "expectation_shift_bound",
    "total_variation_distance",
    "TraceOperation",
    "TrackingAutoIndex",
    "TrackingAutoIndexVerificationError",
    "TrackingPolicy",
    "solve_with",
    "validate_problem",
    "UncertaintyModel",
    "verify_certificate_artifact",
    "verify_dynamic_range_certificate",
    "verify_delta_certificate",
    "verify_range_optimizer_artifact",
    "verify_branch_and_bound_certificate",
    "verify_autodro_selection_artifact",
    "verify_anytime_tv_certificate",
    "verify_autoindex_artifact",
    "verify_tracking_autoindex_certificate",
    "verify_martingale_safe_autoindex_certificate",
    "verify_measured_deployment_artifact",
    "verify_safe_autoindex_certificate",
    "verify_sequential_safe_autoindex_certificate",
    "verify_tree",
    "verify_synthesis_certificate",
    "verify_hybrid_certificate",
    "verify_pruned_beam_certificate",
    "verify_serialized_tree_exact",
    "worst_case_tv_expectation",
    "WorkloadTrace",
    "start_tracking_autoindex",
    "VariableBlockIndex",
    "compile_synthesized_index",
    "compile_hybrid_index",
    "synthesize_hybrid_partitions",
    "generate_safe_cpp_header",
    "generate_martingale_safe_cpp_header",
    "generate_sequential_safe_cpp_header",
    "load_safe_compile_spec",
    "load_martingale_safe_compile_spec",
    "load_sequential_safe_compile_spec",
]
