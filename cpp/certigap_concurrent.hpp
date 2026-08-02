#pragma once

#include "certigap_tracking.hpp"

#include <atomic>
#include <deque>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <thread>


namespace certigap {

struct ConcurrentPrefixPolicy {
    std::size_t max_update_log_entries = 65536;
    std::size_t max_catchup_rounds = 8;
    std::size_t recommendation_range_queries = 4096;
    std::size_t max_snapshot_bytes =
        std::numeric_limits<std::size_t>::max();
};

struct ConcurrentPrefixExplanation {
    std::size_t size = 0;
    std::uint64_t version = 0;
    std::uint64_t snapshot_version = 0;
    bool snapshot_active = false;
    bool rebuild_in_progress = false;
    bool rebuild_recommended = false;
    std::size_t update_log_entries = 0;
    std::size_t estimated_snapshot_bytes = 0;
    std::uint64_t rebuilds_started = 0;
    std::uint64_t rebuilds_published = 0;
    std::uint64_t rebuilds_aborted = 0;
    std::uint64_t invalidations = 0;
    std::uint64_t budget_rejections = 0;
};

class ConcurrentPrefixIndex {
private:
    struct PrefixSnapshot;

public:
    class SnapshotReadView {
    public:
        explicit SnapshotReadView(const ConcurrentPrefixIndex& owner)
            : owner_(&owner) {
            owner_->snapshot_readers_.fetch_add(1, std::memory_order_seq_cst);
            snapshot_ = owner_->snapshot_.load(std::memory_order_seq_cst);
            if (!snapshot_) {
                owner_->snapshot_readers_.fetch_sub(
                    1, std::memory_order_seq_cst);
            }
        }

        ~SnapshotReadView() { release(); }

        SnapshotReadView(const SnapshotReadView&) = delete;
        SnapshotReadView& operator=(const SnapshotReadView&) = delete;

        SnapshotReadView(SnapshotReadView&& other) noexcept
            : owner_(other.owner_), snapshot_(other.snapshot_) {
            other.owner_ = nullptr;
            other.snapshot_ = nullptr;
        }

        SnapshotReadView& operator=(SnapshotReadView&&) = delete;

        double get(int key) const {
            owner_->validate_key(key);
            return unchecked_get(key);
        }

        double range_query(int left, int right) const {
            owner_->validate_range(left, right);
            return unchecked_range_query(left, right);
        }

        double unchecked_get(int key) const {
            if (snapshot_) return snapshot_->get(key);
            return owner_->unchecked_get(key);
        }

        double unchecked_range_query(int left, int right) const {
            if (!snapshot_) return owner_->unchecked_range_query(left, right);
            return snapshot_->range_query(left, right);
        }

        bool active() const { return snapshot_ != nullptr; }
        std::uint64_t version() const {
            return snapshot_ ? snapshot_->version : 0;
        }

    private:
        const ConcurrentPrefixIndex* owner_ = nullptr;
        const PrefixSnapshot* snapshot_ = nullptr;

        void release() {
            if (owner_ && snapshot_) {
                owner_->snapshot_readers_.fetch_sub(
                    1, std::memory_order_seq_cst);
            }
            owner_ = nullptr;
            snapshot_ = nullptr;
        }
    };

    explicit ConcurrentPrefixIndex(
        const std::vector<double>& values,
        ConcurrentPrefixPolicy policy = {}
    )
        : policy_(validate_policy(policy)),
          values_(validated_values(values)), fenwick_(values_) {}

    ~ConcurrentPrefixIndex() { wait_for_rebuild(); }

    ConcurrentPrefixIndex(const ConcurrentPrefixIndex&) = delete;
    ConcurrentPrefixIndex& operator=(const ConcurrentPrefixIndex&) = delete;
    ConcurrentPrefixIndex(ConcurrentPrefixIndex&&) = delete;
    ConcurrentPrefixIndex& operator=(ConcurrentPrefixIndex&&) = delete;

    double get(int key) const {
        validate_key(key);
        return unchecked_get(key);
    }

    double range_query(int left, int right) const {
        validate_range(left, right);
        return unchecked_range_query(left, right);
    }

    void point_update(int key, double value) {
        validate_key(key);
        if (!std::isfinite(value)) {
            throw std::invalid_argument("update value must be finite");
        }
        unchecked_point_update(key, value);
    }

    double unchecked_get(int key) const {
        snapshot_readers_.fetch_add(1, std::memory_order_seq_cst);
        const PrefixSnapshot* snapshot = snapshot_.load(
            std::memory_order_seq_cst);
        if (snapshot) {
            const double result = snapshot->get(key);
            snapshot_readers_.fetch_sub(1, std::memory_order_seq_cst);
            return result;
        }
        snapshot_readers_.fetch_sub(1, std::memory_order_seq_cst);
        std::shared_lock<std::shared_mutex> lock(core_mutex_);
        return fenwick_.get(key);
    }

    double unchecked_range_query(int left, int right) const {
        snapshot_readers_.fetch_add(1, std::memory_order_seq_cst);
        const PrefixSnapshot* snapshot = snapshot_.load(
            std::memory_order_seq_cst);
        if (snapshot) {
            const double result = snapshot->range_query(left, right);
            snapshot_readers_.fetch_sub(1, std::memory_order_seq_cst);
            return result;
        }
        snapshot_readers_.fetch_sub(1, std::memory_order_seq_cst);
        range_queries_since_update_.fetch_add(1, std::memory_order_relaxed);
        std::shared_lock<std::shared_mutex> lock(core_mutex_);
        return fenwick_.range_query(left, right);
    }

    void unchecked_point_update(int key, double value) {
        std::unique_lock<std::shared_mutex> lock(core_mutex_);
        if (version_ == std::numeric_limits<std::uint64_t>::max()) {
            throw std::length_error("concurrent prefix version overflow");
        }
        PrefixSnapshot* previous = snapshot_.exchange(
            nullptr, std::memory_order_seq_cst);
        if (previous) {
            invalidations_.fetch_add(1, std::memory_order_relaxed);
            retired_snapshot_ = std::move(active_snapshot_);
        }
        collect_retired_snapshot();
        snapshot_version_.store(0, std::memory_order_relaxed);
        fenwick_.point_update(key, value);
        values_[key - 1] = value;
        ++version_;
        update_log_.push_back({version_, key, value});
        while (update_log_.size() > policy_.max_update_log_entries) {
            update_log_.pop_front();
        }
        range_queries_since_update_.store(0, std::memory_order_relaxed);
    }

    bool request_rebuild() {
        std::lock_guard<std::mutex> worker_lock(worker_mutex_);
        if (estimated_snapshot_bytes() > policy_.max_snapshot_bytes) {
            budget_rejections_.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        if (snapshot_active()) return false;
        {
            std::unique_lock<std::shared_mutex> core_lock(core_mutex_);
            collect_retired_snapshot();
            if (retired_snapshot_) return false;
        }
        if (rebuild_in_progress_.load(std::memory_order_acquire)) return false;
        if (worker_.joinable()) worker_.join();
        rebuild_in_progress_.store(true, std::memory_order_release);
        rebuilds_started_.fetch_add(1, std::memory_order_relaxed);
        try {
            worker_ = std::thread([this] {
                try {
                    build_and_publish();
                } catch (...) {
                    rebuilds_aborted_.fetch_add(1, std::memory_order_relaxed);
                }
                rebuild_in_progress_.store(false, std::memory_order_release);
            });
        } catch (...) {
            rebuilds_aborted_.fetch_add(1, std::memory_order_relaxed);
            rebuild_in_progress_.store(false, std::memory_order_release);
            throw;
        }
        return true;
    }

    void wait_for_rebuild() {
        std::thread worker;
        {
            std::lock_guard<std::mutex> lock(worker_mutex_);
            if (worker_.joinable()) worker.swap(worker_);
        }
        if (worker.joinable()) worker.join();
    }

    bool rebuild_now() {
        const std::uint64_t before = rebuilds_published_.load(
            std::memory_order_relaxed);
        if (!request_rebuild()) return snapshot_active();
        wait_for_rebuild();
        return rebuilds_published_.load(std::memory_order_relaxed) > before;
    }

    bool snapshot_active() const {
        return snapshot_.load(std::memory_order_seq_cst) != nullptr;
    }

    SnapshotReadView snapshot_view() const {
        return SnapshotReadView(*this);
    }

    bool rebuild_recommended() const {
        return !snapshot_active()
            && !rebuild_in_progress_.load(std::memory_order_acquire)
            && range_queries_since_update_.load(std::memory_order_relaxed)
                >= policy_.recommendation_range_queries;
    }

    std::size_t estimated_snapshot_bytes() const {
        constexpr std::size_t vectors = 2 * sizeof(double);
        if (values_.size()
            > (std::numeric_limits<std::size_t>::max()
                - sizeof(PrefixSnapshot) - sizeof(double)) / vectors) {
            return std::numeric_limits<std::size_t>::max();
        }
        return sizeof(PrefixSnapshot)
            + vectors * values_.size() + sizeof(double);
    }

    ConcurrentPrefixExplanation explain() const {
        std::shared_lock<std::shared_mutex> lock(core_mutex_);
        return {
            values_.size(), version_,
            snapshot_version_.load(std::memory_order_relaxed),
            snapshot_active(),
            rebuild_in_progress_.load(std::memory_order_acquire),
            rebuild_recommended(), update_log_.size(),
            estimated_snapshot_bytes(),
            rebuilds_started_.load(std::memory_order_relaxed),
            rebuilds_published_.load(std::memory_order_relaxed),
            rebuilds_aborted_.load(std::memory_order_relaxed),
            invalidations_.load(std::memory_order_relaxed),
            budget_rejections_.load(std::memory_order_relaxed),
        };
    }

    std::size_t size() const { return values_.size(); }

    bool snapshot_atomics_lock_free() const {
        return snapshot_.is_lock_free() && snapshot_readers_.is_lock_free();
    }

private:
    struct UpdateRecord {
        std::uint64_t version = 0;
        int key = 1;
        double value = 0.0;
    };

    struct PrefixSnapshot {
        PrefixSnapshot(std::vector<double> source, std::uint64_t version_value)
            : values(std::move(source)), prefix(values.size() + 1, 0.0),
              version(version_value) {
            rebuild();
        }

        double get(int key) const { return values[key - 1]; }

        double range_query(int left, int right) const {
            return prefix[right] - prefix[left - 1];
        }

        void apply(const std::vector<UpdateRecord>& updates) {
            for (const auto& update : updates) {
                values[update.key - 1] = update.value;
                version = update.version;
            }
            rebuild();
        }

        void rebuild() {
            prefix[0] = 0.0;
            for (std::size_t index = 0; index < values.size(); ++index) {
                prefix[index + 1] = prefix[index] + values[index];
            }
        }

        std::vector<double> values;
        std::vector<double> prefix;
        std::uint64_t version = 0;
    };

    ConcurrentPrefixPolicy policy_;
    std::vector<double> values_;
    detail::FenwickRuntime fenwick_;
    mutable std::shared_mutex core_mutex_;
    std::uint64_t version_ = 0;
    std::deque<UpdateRecord> update_log_;
    mutable std::atomic<PrefixSnapshot*> snapshot_{nullptr};
    mutable std::atomic<std::uint64_t> snapshot_readers_{0};
    std::unique_ptr<PrefixSnapshot> active_snapshot_;
    std::unique_ptr<PrefixSnapshot> retired_snapshot_;
    std::atomic<std::uint64_t> snapshot_version_{0};
    mutable std::atomic<std::uint64_t> range_queries_since_update_{0};
    std::atomic<bool> rebuild_in_progress_{false};
    std::atomic<std::uint64_t> rebuilds_started_{0};
    std::atomic<std::uint64_t> rebuilds_published_{0};
    std::atomic<std::uint64_t> rebuilds_aborted_{0};
    std::atomic<std::uint64_t> invalidations_{0};
    std::atomic<std::uint64_t> budget_rejections_{0};
    mutable std::mutex worker_mutex_;
    std::thread worker_;

    void collect_retired_snapshot() {
        if (
            retired_snapshot_
            && snapshot_readers_.load(std::memory_order_seq_cst) == 0
        ) retired_snapshot_.reset();
    }

    static ConcurrentPrefixPolicy validate_policy(
        ConcurrentPrefixPolicy policy
    ) {
        if (
            policy.max_update_log_entries == 0
            || policy.max_catchup_rounds == 0
            || policy.recommendation_range_queries == 0
            || policy.max_snapshot_bytes == 0
        ) throw std::invalid_argument("invalid concurrent prefix policy");
        return policy;
    }

    static std::vector<double> validated_values(
        const std::vector<double>& values
    ) {
        if (values.empty()) throw std::invalid_argument("values must not be empty");
        if (values.size()
            > static_cast<std::size_t>(std::numeric_limits<int>::max())) {
            throw std::length_error("key universe exceeds int range");
        }
        for (double value : values) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument("values must be finite");
            }
        }
        return values;
    }

    void validate_key(int key) const {
        if (key < 1 || key > static_cast<int>(values_.size())) {
            throw std::out_of_range("concurrent prefix key out of range");
        }
    }

    void validate_range(int left, int right) const {
        if (
            left < 1 || right < left
            || right > static_cast<int>(values_.size())
        ) throw std::out_of_range("invalid concurrent prefix range");
    }

    void build_and_publish() {
        std::vector<double> base_values;
        std::uint64_t applied_version = 0;
        {
            std::shared_lock<std::shared_mutex> lock(core_mutex_);
            base_values = values_;
            applied_version = version_;
        }
        auto candidate = std::make_unique<PrefixSnapshot>(
            std::move(base_values), applied_version);

        for (std::size_t round = 0; round < policy_.max_catchup_rounds; ++round) {
            std::vector<UpdateRecord> pending;
            {
                std::unique_lock<std::shared_mutex> lock(core_mutex_);
                if (version_ == applied_version) {
                    candidate->version = applied_version;
                    collect_retired_snapshot();
                    if (retired_snapshot_) {
                        rebuilds_aborted_.fetch_add(1, std::memory_order_relaxed);
                        return;
                    }
                    active_snapshot_ = std::move(candidate);
                    snapshot_.store(
                        active_snapshot_.get(), std::memory_order_seq_cst);
                    snapshot_version_.store(
                        applied_version, std::memory_order_relaxed);
                    rebuilds_published_.fetch_add(1, std::memory_order_relaxed);
                    return;
                }
                if (
                    update_log_.empty()
                    || update_log_.front().version > applied_version + 1
                ) {
                    rebuilds_aborted_.fetch_add(1, std::memory_order_relaxed);
                    return;
                }
                for (const auto& update : update_log_) {
                    if (update.version > applied_version) pending.push_back(update);
                }
            }
            if (pending.empty()) {
                rebuilds_aborted_.fetch_add(1, std::memory_order_relaxed);
                return;
            }
            candidate->apply(pending);
            applied_version = candidate->version;
        }
        rebuilds_aborted_.fetch_add(1, std::memory_order_relaxed);
    }
};

}  // namespace certigap
