#include <sqlite3ext.h>
SQLITE_EXTENSION_INIT3

#include "certigap.hpp"
#include "certigap_sqlite_vtab.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <map>
#include <memory>
#include <new>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr int kKeyEqual = 1;
constexpr int kKeyLower = 2;
constexpr int kKeyLowerStrict = 4;
constexpr int kKeyUpper = 8;
constexpr int kKeyUpperStrict = 16;
constexpr int kRightEqual = 32;

struct CertiGapVTab {
    sqlite3_vtab base{};
    sqlite3* database = nullptr;
    std::string schema;
    std::string name;
    std::string shadow;
    std::map<sqlite3_int64, double> rows;
    std::vector<sqlite3_int64> keys;
    std::unique_ptr<certigap::Index> index;
    bool in_transaction = false;
    std::map<sqlite3_int64, double> transaction_snapshot;
    std::map<int, std::map<sqlite3_int64, double>> savepoints;
};

struct CertiGapCursor {
    sqlite3_vtab_cursor base{};
    std::vector<std::pair<sqlite3_int64, double>> rows;
    std::size_t position = 0;
    bool range_mode = false;
    sqlite3_int64 range_left = 0;
    sqlite3_int64 range_right = 0;
    double range_sum = 0.0;
};

CertiGapVTab* table(sqlite3_vtab* value) {
    return reinterpret_cast<CertiGapVTab*>(value);
}

CertiGapVTab* table(sqlite3_vtab_cursor* value) {
    return table(value->pVtab);
}

CertiGapCursor* cursor(sqlite3_vtab_cursor* value) {
    return reinterpret_cast<CertiGapCursor*>(value);
}

std::string quote_identifier(const std::string& value) {
    char* escaped = sqlite3_mprintf("%w", value.c_str());
    if (escaped == nullptr) throw std::bad_alloc();
    std::string result = "\"" + std::string(escaped) + "\"";
    sqlite3_free(escaped);
    return result;
}

std::string qualified(const CertiGapVTab& value) {
    return quote_identifier(value.schema) + "." + quote_identifier(value.shadow);
}

int set_error(CertiGapVTab* value, int code, const std::string& message) {
    sqlite3_free(value->base.zErrMsg);
    value->base.zErrMsg = sqlite3_mprintf("%s", message.c_str());
    return code;
}

int execute(sqlite3* database, const std::string& sql) {
    return sqlite3_exec(database, sql.c_str(), nullptr, nullptr, nullptr);
}

int mutate_shadow(
    CertiGapVTab* value,
    const std::string& sql,
    const std::vector<std::pair<int, sqlite3_int64>>& integers,
    const std::vector<std::pair<int, double>>& numbers
) {
    sqlite3_stmt* statement = nullptr;
    int result = sqlite3_prepare_v2(
        value->database, sql.c_str(), -1, &statement, nullptr
    );
    if (result != SQLITE_OK) {
        return set_error(value, result, sqlite3_errmsg(value->database));
    }
    for (const auto& [position, argument] : integers) {
        result = sqlite3_bind_int64(statement, position, argument);
        if (result != SQLITE_OK) break;
    }
    for (const auto& [position, argument] : numbers) {
        if (result != SQLITE_OK) break;
        result = sqlite3_bind_double(statement, position, argument);
    }
    if (result == SQLITE_OK) result = sqlite3_step(statement);
    if (result == SQLITE_DONE) result = SQLITE_OK;
    const std::string message = sqlite3_errmsg(value->database);
    const int finalize_result = sqlite3_finalize(statement);
    if (result == SQLITE_OK && finalize_result != SQLITE_OK) {
        result = finalize_result;
    }
    if (result != SQLITE_OK) return set_error(value, result, message);
    return SQLITE_OK;
}

void rebuild(CertiGapVTab* value) {
    value->keys.clear();
    std::vector<double> values;
    value->keys.reserve(value->rows.size());
    values.reserve(value->rows.size());
    for (const auto& [key, number] : value->rows) {
        value->keys.push_back(key);
        values.push_back(number);
    }
    if (values.empty()) {
        value->index.reset();
    } else {
        value->index = std::make_unique<certigap::Index>(values);
    }
}

int load_shadow(CertiGapVTab* value) {
    std::map<sqlite3_int64, double> loaded;
    sqlite3_stmt* statement = nullptr;
    const std::string sql =
        "SELECT key,value FROM " + qualified(*value) + " ORDER BY key";
    int result = sqlite3_prepare_v2(
        value->database, sql.c_str(), -1, &statement, nullptr
    );
    if (result != SQLITE_OK) return result;
    while ((result = sqlite3_step(statement)) == SQLITE_ROW) {
        const sqlite3_int64 key = sqlite3_column_int64(statement, 0);
        const double number = sqlite3_column_double(statement, 1);
        if (key < 1 || !std::isfinite(number)) {
            sqlite3_finalize(statement);
            return SQLITE_CORRUPT;
        }
        loaded[key] = number;
    }
    if (result == SQLITE_DONE) result = SQLITE_OK;
    const int finalize_result = sqlite3_finalize(statement);
    if (result == SQLITE_OK && finalize_result != SQLITE_OK) {
        result = finalize_result;
    }
    if (result == SQLITE_OK) {
        value->rows = std::move(loaded);
        rebuild(value);
    }
    return result;
}

int connect_table(
    sqlite3* database,
    int argc,
    const char* const* argv,
    bool create,
    sqlite3_vtab** output,
    char** error
) {
    if (argc != 3) {
        *error = sqlite3_mprintf("certigap_vtab takes no module arguments");
        return SQLITE_MISUSE;
    }
    auto value = std::make_unique<CertiGapVTab>();
    value->database = database;
    value->schema = argv[1];
    value->name = argv[2];
    value->shadow = value->name + "_data";
    int result = SQLITE_OK;
    if (create) {
        const std::string sql =
            "CREATE TABLE " + qualified(*value)
            + "(key INTEGER PRIMARY KEY CHECK(key>=1),"
              "value REAL NOT NULL CHECK(typeof(value) IN ('integer','real')))";
        result = execute(database, sql);
    }
    if (result == SQLITE_OK) {
        result = sqlite3_declare_vtab(
            database,
            "CREATE TABLE x(key INTEGER PRIMARY KEY,value REAL NOT NULL,"
            "right_key INTEGER HIDDEN,range_sum REAL HIDDEN,selected TEXT HIDDEN)"
        );
    }
    if (result == SQLITE_OK) {
        sqlite3_vtab_config(database, SQLITE_VTAB_CONSTRAINT_SUPPORT, 1);
        result = load_shadow(value.get());
    }
    if (result != SQLITE_OK) {
        *error = sqlite3_mprintf("certigap_vtab: %s", sqlite3_errmsg(database));
        return result;
    }
    *output = &value.release()->base;
    return SQLITE_OK;
}

int create_table(
    sqlite3* database,
    void*,
    int argc,
    const char* const* argv,
    sqlite3_vtab** output,
    char** error
) {
    return connect_table(database, argc, argv, true, output, error);
}

int connect_existing(
    sqlite3* database,
    void*,
    int argc,
    const char* const* argv,
    sqlite3_vtab** output,
    char** error
) {
    return connect_table(database, argc, argv, false, output, error);
}

int best_index(sqlite3_vtab*, sqlite3_index_info* info) {
    int equal = -1;
    int lower = -1;
    int upper = -1;
    int right = -1;
    bool lower_strict = false;
    bool upper_strict = false;
    for (int index = 0; index < info->nConstraint; ++index) {
        const auto& constraint = info->aConstraint[index];
        if (!constraint.usable) continue;
        if (constraint.iColumn == 0) {
            if (constraint.op == SQLITE_INDEX_CONSTRAINT_EQ) {
                equal = index;
            } else if (
                constraint.op == SQLITE_INDEX_CONSTRAINT_GT
                || constraint.op == SQLITE_INDEX_CONSTRAINT_GE
            ) {
                if (lower < 0 || constraint.op == SQLITE_INDEX_CONSTRAINT_GT) {
                    lower = index;
                    lower_strict = constraint.op == SQLITE_INDEX_CONSTRAINT_GT;
                }
            } else if (
                constraint.op == SQLITE_INDEX_CONSTRAINT_LT
                || constraint.op == SQLITE_INDEX_CONSTRAINT_LE
            ) {
                if (upper < 0 || constraint.op == SQLITE_INDEX_CONSTRAINT_LT) {
                    upper = index;
                    upper_strict = constraint.op == SQLITE_INDEX_CONSTRAINT_LT;
                }
            }
        } else if (
            constraint.iColumn == 2
            && constraint.op == SQLITE_INDEX_CONSTRAINT_EQ
        ) {
            right = index;
        }
    }

    int argument = 1;
    int strategy = 0;
    std::string description;
    if (equal >= 0) {
        info->aConstraintUsage[equal].argvIndex = argument++;
        info->aConstraintUsage[equal].omit = 1;
        strategy |= kKeyEqual;
        description = "key_eq";
    } else {
        if (lower >= 0) {
            info->aConstraintUsage[lower].argvIndex = argument++;
            info->aConstraintUsage[lower].omit = 1;
            strategy |= kKeyLower;
            if (lower_strict) strategy |= kKeyLowerStrict;
            description = lower_strict ? "key_gt" : "key_ge";
        }
        if (upper >= 0) {
            info->aConstraintUsage[upper].argvIndex = argument++;
            info->aConstraintUsage[upper].omit = 1;
            strategy |= kKeyUpper;
            if (upper_strict) strategy |= kKeyUpperStrict;
            if (!description.empty()) description += "_";
            description += upper_strict ? "key_lt" : "key_le";
        }
    }
    if (right >= 0 && equal >= 0) {
        info->aConstraintUsage[right].argvIndex = argument++;
        info->aConstraintUsage[right].omit = 1;
        strategy |= kRightEqual;
        description += "_range_sum";
    }
    if (description.empty()) description = "full_scan";
    info->idxNum = strategy;
    info->idxStr = sqlite3_mprintf("%s", description.c_str());
    info->needToFreeIdxStr = 1;
    if (strategy & kKeyEqual) {
        info->estimatedCost = 4.0;
        info->estimatedRows = 1;
        info->idxFlags = SQLITE_INDEX_SCAN_UNIQUE;
    } else if (strategy & (kKeyLower | kKeyUpper)) {
        info->estimatedCost = 100.0;
        info->estimatedRows = 100;
    } else {
        info->estimatedCost = 1000000.0;
        info->estimatedRows = 1000000;
    }
    if (
        info->nOrderBy == 1 && info->aOrderBy[0].iColumn == 0
        && info->aOrderBy[0].desc == 0
    ) {
        info->orderByConsumed = 1;
    }
    return SQLITE_OK;
}

int disconnect(sqlite3_vtab* raw) {
    delete table(raw);
    return SQLITE_OK;
}

int destroy(sqlite3_vtab* raw) {
    CertiGapVTab* value = table(raw);
    const int result = execute(
        value->database, "DROP TABLE " + qualified(*value)
    );
    if (result != SQLITE_OK) {
        return set_error(value, result, sqlite3_errmsg(value->database));
    }
    delete value;
    return SQLITE_OK;
}

int open_cursor(sqlite3_vtab* raw, sqlite3_vtab_cursor** output) {
    auto value = std::make_unique<CertiGapCursor>();
    value->base.pVtab = raw;
    *output = &value.release()->base;
    return SQLITE_OK;
}

int close_cursor(sqlite3_vtab_cursor* raw) {
    delete cursor(raw);
    return SQLITE_OK;
}

sqlite3_int64 integer_filter(sqlite3_value* value) {
    if (sqlite3_value_type(value) != SQLITE_INTEGER) {
        throw std::invalid_argument("key constraints must be integers");
    }
    return sqlite3_value_int64(value);
}

int filter(
    sqlite3_vtab_cursor* raw,
    int strategy,
    const char*,
    int argc,
    sqlite3_value** argv
) {
    CertiGapCursor* result = cursor(raw);
    CertiGapVTab* value = table(raw);
    result->rows.clear();
    result->position = 0;
    result->range_mode = false;
    try {
        const int refresh_result = load_shadow(value);
        if (refresh_result != SQLITE_OK) {
            return set_error(
                value, refresh_result, sqlite3_errmsg(value->database)
            );
        }
        int argument = 0;
        std::optional<sqlite3_int64> equal;
        std::optional<sqlite3_int64> lower;
        std::optional<sqlite3_int64> upper;
        std::optional<sqlite3_int64> right;
        if (strategy & kKeyEqual) equal = integer_filter(argv[argument++]);
        if (strategy & kKeyLower) lower = integer_filter(argv[argument++]);
        if (strategy & kKeyUpper) upper = integer_filter(argv[argument++]);
        if (strategy & kRightEqual) right = integer_filter(argv[argument++]);
        if (argument != argc) {
            return set_error(value, SQLITE_MISUSE, "invalid planner arguments");
        }

        if (equal && right) {
            if (*equal < 1 || *right < *equal || value->index == nullptr) {
                return SQLITE_OK;
            }
            const auto left_position = std::lower_bound(
                value->keys.begin(), value->keys.end(), *equal
            );
            const auto after_right = std::upper_bound(
                value->keys.begin(), value->keys.end(), *right
            );
            if (left_position == value->keys.end() || left_position == after_right) {
                return SQLITE_OK;
            }
            const int left_rank = static_cast<int>(
                std::distance(value->keys.begin(), left_position)
            ) + 1;
            const int right_rank = static_cast<int>(
                std::distance(value->keys.begin(), after_right)
            );
            result->range_mode = true;
            result->range_left = *equal;
            result->range_right = *right;
            result->range_sum = value->index->range_query(left_rank, right_rank);
            return SQLITE_OK;
        }

        auto begin = value->rows.begin();
        auto end = value->rows.end();
        if (equal) {
            begin = value->rows.lower_bound(*equal);
            end = begin;
            if (end != value->rows.end()) ++end;
            if (begin == value->rows.end() || begin->first != *equal) {
                begin = end = value->rows.end();
            }
        } else {
            if (lower) {
                begin = (strategy & kKeyLowerStrict)
                    ? value->rows.upper_bound(*lower)
                    : value->rows.lower_bound(*lower);
            }
            if (upper) {
                end = (strategy & kKeyUpperStrict)
                    ? value->rows.lower_bound(*upper)
                    : value->rows.upper_bound(*upper);
            }
        }
        for (auto iterator = begin; iterator != end; ++iterator) {
            result->rows.push_back(*iterator);
        }
        return SQLITE_OK;
    } catch (const std::exception& error) {
        return set_error(value, SQLITE_ERROR, error.what());
    }
}

int next(sqlite3_vtab_cursor* raw) {
    ++cursor(raw)->position;
    return SQLITE_OK;
}

int eof(sqlite3_vtab_cursor* raw) {
    const CertiGapCursor* value = cursor(raw);
    if (value->range_mode) return value->position > 0;
    return value->position >= value->rows.size();
}

int column(sqlite3_vtab_cursor* raw, sqlite3_context* context, int index) {
    CertiGapCursor* value = cursor(raw);
    CertiGapVTab* owner = table(raw);
    if (value->range_mode) {
        if (index == 0) sqlite3_result_int64(context, value->range_left);
        else if (index == 2) sqlite3_result_int64(context, value->range_right);
        else if (index == 3) sqlite3_result_double(context, value->range_sum);
        else if (index == 4 && owner->index != nullptr) {
            const auto selected = owner->index->selected_name();
            sqlite3_result_text(
                context, selected.data(), static_cast<int>(selected.size()),
                SQLITE_TRANSIENT
            );
        } else sqlite3_result_null(context);
        return SQLITE_OK;
    }
    if (value->position >= value->rows.size()) return SQLITE_ERROR;
    if (index == 0) {
        sqlite3_result_int64(context, value->rows[value->position].first);
    } else if (index == 1) {
        sqlite3_result_double(context, value->rows[value->position].second);
    } else if (index == 4 && owner->index != nullptr) {
        const auto selected = owner->index->selected_name();
        sqlite3_result_text(
            context, selected.data(), static_cast<int>(selected.size()),
            SQLITE_TRANSIENT
        );
    } else {
        sqlite3_result_null(context);
    }
    return SQLITE_OK;
}

int rowid(sqlite3_vtab_cursor* raw, sqlite3_int64* output) {
    CertiGapCursor* value = cursor(raw);
    if (value->range_mode) {
        *output = value->range_left;
    } else if (value->position < value->rows.size()) {
        *output = value->rows[value->position].first;
    } else {
        return SQLITE_ERROR;
    }
    return SQLITE_OK;
}

int update_table(
    sqlite3_vtab* raw,
    int argc,
    sqlite3_value** argv,
    sqlite3_int64* output_rowid
) {
    CertiGapVTab* value = table(raw);
    if (argc == 1) {
        const sqlite3_int64 key = sqlite3_value_int64(argv[0]);
        const int result = mutate_shadow(
            value,
            "DELETE FROM " + qualified(*value) + " WHERE key=?1",
            {{1, key}},
            {}
        );
        if (result == SQLITE_OK) {
            value->rows.erase(key);
            rebuild(value);
        }
        return result;
    }
    if (argc != 7) {
        return set_error(value, SQLITE_MISUSE, "invalid virtual-table update");
    }
    const bool insertion = sqlite3_value_type(argv[0]) == SQLITE_NULL;
    const sqlite3_int64 old_key = insertion ? 0 : sqlite3_value_int64(argv[0]);
    sqlite3_int64 new_key = 0;
    if (sqlite3_value_type(argv[2]) == SQLITE_INTEGER) {
        new_key = sqlite3_value_int64(argv[2]);
    } else if (sqlite3_value_type(argv[1]) == SQLITE_INTEGER) {
        new_key = sqlite3_value_int64(argv[1]);
    } else {
        return set_error(value, SQLITE_CONSTRAINT, "key must be an integer");
    }
    if (new_key < 1) {
        return set_error(value, SQLITE_CONSTRAINT, "key must be positive");
    }
    if (
        sqlite3_value_type(argv[3]) != SQLITE_INTEGER
        && sqlite3_value_type(argv[3]) != SQLITE_FLOAT
    ) {
        return set_error(value, SQLITE_CONSTRAINT, "value must be numeric");
    }
    const double number = sqlite3_value_double(argv[3]);
    if (!std::isfinite(number)) {
        return set_error(value, SQLITE_CONSTRAINT, "value must be finite");
    }
    if (
        (insertion || old_key != new_key)
        && value->rows.find(new_key) != value->rows.end()
    ) {
        return set_error(value, SQLITE_CONSTRAINT, "duplicate key");
    }

    int result = SQLITE_OK;
    if (insertion) {
        result = mutate_shadow(
            value,
            "INSERT INTO " + qualified(*value) + "(key,value) VALUES(?1,?2)",
            {{1, new_key}},
            {{2, number}}
        );
    } else if (old_key == new_key) {
        result = mutate_shadow(
            value,
            "UPDATE " + qualified(*value) + " SET value=?2 WHERE key=?1",
            {{1, new_key}},
            {{2, number}}
        );
    } else {
        result = mutate_shadow(
            value,
            "DELETE FROM " + qualified(*value) + " WHERE key=?1",
            {{1, old_key}},
            {}
        );
        if (result == SQLITE_OK) {
            result = mutate_shadow(
                value,
                "INSERT INTO " + qualified(*value)
                + "(key,value) VALUES(?1,?2)",
                {{1, new_key}},
                {{2, number}}
            );
        }
    }
    if (result != SQLITE_OK) return result;
    if (!insertion) value->rows.erase(old_key);
    value->rows[new_key] = number;
    rebuild(value);
    *output_rowid = new_key;
    return SQLITE_OK;
}

int begin(sqlite3_vtab* raw) {
    CertiGapVTab* value = table(raw);
    const int result = load_shadow(value);
    if (result != SQLITE_OK) {
        return set_error(value, result, sqlite3_errmsg(value->database));
    }
    value->in_transaction = true;
    value->transaction_snapshot = value->rows;
    value->savepoints.clear();
    return SQLITE_OK;
}

int sync(sqlite3_vtab*) {
    return SQLITE_OK;
}

int commit(sqlite3_vtab* raw) {
    CertiGapVTab* value = table(raw);
    value->in_transaction = false;
    value->transaction_snapshot.clear();
    value->savepoints.clear();
    return SQLITE_OK;
}

int rollback(sqlite3_vtab* raw) {
    CertiGapVTab* value = table(raw);
    if (value->in_transaction) {
        value->rows = value->transaction_snapshot;
        rebuild(value);
    }
    return commit(raw);
}

int rename_table(sqlite3_vtab* raw, const char* new_name) {
    CertiGapVTab* value = table(raw);
    const std::string replacement = std::string(new_name) + "_data";
    const std::string sql =
        "ALTER TABLE " + qualified(*value) + " RENAME TO "
        + quote_identifier(replacement);
    const int result = execute(value->database, sql);
    if (result != SQLITE_OK) {
        return set_error(value, result, sqlite3_errmsg(value->database));
    }
    value->name = new_name;
    value->shadow = replacement;
    return SQLITE_OK;
}

int savepoint(sqlite3_vtab* raw, int index) {
    CertiGapVTab* value = table(raw);
    value->savepoints[index] = value->rows;
    return SQLITE_OK;
}

int release(sqlite3_vtab* raw, int index) {
    CertiGapVTab* value = table(raw);
    value->savepoints.erase(value->savepoints.lower_bound(index), value->savepoints.end());
    return SQLITE_OK;
}

int rollback_to(sqlite3_vtab* raw, int index) {
    CertiGapVTab* value = table(raw);
    const auto found = value->savepoints.find(index);
    if (found == value->savepoints.end()) return SQLITE_ERROR;
    value->rows = found->second;
    rebuild(value);
    value->savepoints.erase(std::next(found), value->savepoints.end());
    return SQLITE_OK;
}

int shadow_name(const char* suffix) {
    return sqlite3_stricmp(suffix, "data") == 0;
}

sqlite3_module make_module() {
    sqlite3_module module{};
    module.iVersion = 3;
    module.xCreate = create_table;
    module.xConnect = connect_existing;
    module.xBestIndex = best_index;
    module.xDisconnect = disconnect;
    module.xDestroy = destroy;
    module.xOpen = open_cursor;
    module.xClose = close_cursor;
    module.xFilter = filter;
    module.xNext = next;
    module.xEof = eof;
    module.xColumn = column;
    module.xRowid = rowid;
    module.xUpdate = update_table;
    module.xBegin = begin;
    module.xSync = sync;
    module.xCommit = commit;
    module.xRollback = rollback;
    module.xRename = rename_table;
    module.xSavepoint = savepoint;
    module.xRelease = release;
    module.xRollbackTo = rollback_to;
    module.xShadowName = shadow_name;
    return module;
}

const sqlite3_module kModule = make_module();

}  // namespace

int certigap_register_vtab(sqlite3* database, char** error) {
    const int result = sqlite3_create_module_v2(
        database, "certigap_vtab", &kModule, nullptr, nullptr
    );
    if (result != SQLITE_OK && error != nullptr) {
        *error = sqlite3_mprintf(
            "failed to register certigap_vtab: %s", sqlite3_errstr(result)
        );
    }
    return result;
}
