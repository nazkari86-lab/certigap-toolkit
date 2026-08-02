#include <sqlite3ext.h>
SQLITE_EXTENSION_INIT1

#include "certigap.hpp"
#include "certigap_sqlite_vtab.hpp"

#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

struct Registry {
    std::mutex mutex;
    std::unordered_map<std::string, std::unique_ptr<certigap::Index>> indexes;
};

using RegistryHandle = std::shared_ptr<Registry>;

Registry& registry(sqlite3_context* context) {
    auto* handle = static_cast<RegistryHandle*>(sqlite3_user_data(context));
    return **handle;
}

void destroy_handle(void* value) {
    delete static_cast<RegistryHandle*>(value);
}

std::string text_argument(sqlite3_value* value, const char* label) {
    if (sqlite3_value_type(value) != SQLITE_TEXT) {
        throw std::invalid_argument(std::string(label) + " must be text");
    }
    const auto* text = sqlite3_value_text(value);
    if (text == nullptr || text[0] == '\0') {
        throw std::invalid_argument(std::string(label) + " must not be empty");
    }
    return reinterpret_cast<const char*>(text);
}

int integer_argument(sqlite3_value* value, const char* label) {
    if (sqlite3_value_type(value) != SQLITE_INTEGER) {
        throw std::invalid_argument(std::string(label) + " must be an integer");
    }
    const sqlite3_int64 raw = sqlite3_value_int64(value);
    if (raw < 1 || raw > 2147483647) {
        throw std::invalid_argument(std::string(label) + " is out of range");
    }
    return static_cast<int>(raw);
}

double number_argument(sqlite3_value* value, const char* label) {
    if (
        sqlite3_value_type(value) != SQLITE_FLOAT
        && sqlite3_value_type(value) != SQLITE_INTEGER
    ) {
        throw std::invalid_argument(std::string(label) + " must be numeric");
    }
    const double result = sqlite3_value_double(value);
    if (!std::isfinite(result)) {
        throw std::invalid_argument(std::string(label) + " must be finite");
    }
    return result;
}

std::vector<double> parse_values(const std::string& json) {
    const char* cursor = json.c_str();
    auto skip_space = [&]() {
        while (*cursor == ' ' || *cursor == '\n' || *cursor == '\r'
               || *cursor == '\t') {
            ++cursor;
        }
    };
    skip_space();
    if (*cursor++ != '[') {
        throw std::invalid_argument("values must be a JSON numeric array");
    }
    std::vector<double> values;
    skip_space();
    if (*cursor == ']') {
        throw std::invalid_argument("values must not be empty");
    }
    while (true) {
        skip_space();
        const char* number_start = cursor;
        if (*cursor == '-') ++cursor;
        if (*cursor == '0') {
            ++cursor;
            if (*cursor >= '0' && *cursor <= '9') {
                throw std::invalid_argument("values contain a leading zero");
            }
        } else if (*cursor >= '1' && *cursor <= '9') {
            while (*cursor >= '0' && *cursor <= '9') ++cursor;
        } else {
            throw std::invalid_argument("values contain an invalid number");
        }
        if (*cursor == '.') {
            ++cursor;
            if (*cursor < '0' || *cursor > '9') {
                throw std::invalid_argument("values contain an invalid fraction");
            }
            while (*cursor >= '0' && *cursor <= '9') ++cursor;
        }
        if (*cursor == 'e' || *cursor == 'E') {
            ++cursor;
            if (*cursor == '+' || *cursor == '-') ++cursor;
            if (*cursor < '0' || *cursor > '9') {
                throw std::invalid_argument("values contain an invalid exponent");
            }
            while (*cursor >= '0' && *cursor <= '9') ++cursor;
        }
        const std::string token(number_start, cursor);
        errno = 0;
        char* end = nullptr;
        const double value = std::strtod(token.c_str(), &end);
        if (
            end != token.c_str() + token.size()
            || errno == ERANGE
            || !std::isfinite(value)
        ) {
            throw std::invalid_argument("values contain an invalid number");
        }
        values.push_back(value);
        skip_space();
        if (*cursor == ']') {
            ++cursor;
            break;
        }
        if (*cursor++ != ',') {
            throw std::invalid_argument("values JSON has invalid separators");
        }
    }
    skip_space();
    if (*cursor != '\0') {
        throw std::invalid_argument("values JSON has trailing content");
    }
    return values;
}

certigap::Index& find_index(Registry& state, const std::string& name) {
    const auto found = state.indexes.find(name);
    if (found == state.indexes.end()) {
        throw std::invalid_argument("unknown CertiGap index: " + name);
    }
    return *found->second;
}

template <class Function>
void guarded(sqlite3_context* context, Function&& function) {
    try {
        function();
    } catch (const std::exception& error) {
        sqlite3_result_error(context, error.what(), -1);
    } catch (...) {
        sqlite3_result_error(context, "unknown CertiGap extension error", -1);
    }
}

void build(sqlite3_context* context, int argc, sqlite3_value** argv) {
    guarded(context, [&] {
        if (argc != 2) throw std::invalid_argument("certigap_build expects 2 arguments");
        const std::string name = text_argument(argv[0], "name");
        const auto values = parse_values(text_argument(argv[1], "values"));
        auto index = std::make_unique<certigap::Index>(values);
        Registry& state = registry(context);
        std::lock_guard<std::mutex> lock(state.mutex);
        state.indexes[name] = std::move(index);
        sqlite3_result_int64(context, static_cast<sqlite3_int64>(values.size()));
    });
}

void get(sqlite3_context* context, int argc, sqlite3_value** argv) {
    guarded(context, [&] {
        if (argc != 2) throw std::invalid_argument("certigap_get expects 2 arguments");
        const std::string name = text_argument(argv[0], "name");
        const int key = integer_argument(argv[1], "key");
        Registry& state = registry(context);
        std::lock_guard<std::mutex> lock(state.mutex);
        sqlite3_result_double(context, find_index(state, name).get(key));
    });
}

void range_sum(sqlite3_context* context, int argc, sqlite3_value** argv) {
    guarded(context, [&] {
        if (argc != 3) throw std::invalid_argument("certigap_range_sum expects 3 arguments");
        const std::string name = text_argument(argv[0], "name");
        const int left = integer_argument(argv[1], "left");
        const int right = integer_argument(argv[2], "right");
        Registry& state = registry(context);
        std::lock_guard<std::mutex> lock(state.mutex);
        sqlite3_result_double(
            context, find_index(state, name).range_query(left, right)
        );
    });
}

void update(sqlite3_context* context, int argc, sqlite3_value** argv) {
    guarded(context, [&] {
        if (argc != 3) throw std::invalid_argument("certigap_update expects 3 arguments");
        const std::string name = text_argument(argv[0], "name");
        const int key = integer_argument(argv[1], "key");
        const double value = number_argument(argv[2], "value");
        Registry& state = registry(context);
        std::lock_guard<std::mutex> lock(state.mutex);
        find_index(state, name).point_update(key, value);
        sqlite3_result_double(context, value);
    });
}

void optimize(sqlite3_context* context, int argc, sqlite3_value** argv) {
    guarded(context, [&] {
        if (argc != 1) throw std::invalid_argument("certigap_optimize expects 1 argument");
        const std::string name = text_argument(argv[0], "name");
        Registry& state = registry(context);
        std::lock_guard<std::mutex> lock(state.mutex);
        auto& index = find_index(state, name);
        index.optimize();
        const auto selected = index.selected_name();
        sqlite3_result_text(
            context, selected.data(), static_cast<int>(selected.size()), SQLITE_TRANSIENT
        );
    });
}

void selected(sqlite3_context* context, int argc, sqlite3_value** argv) {
    guarded(context, [&] {
        if (argc != 1) throw std::invalid_argument("certigap_selected expects 1 argument");
        const std::string name = text_argument(argv[0], "name");
        Registry& state = registry(context);
        std::lock_guard<std::mutex> lock(state.mutex);
        const auto value = find_index(state, name).selected_name();
        sqlite3_result_text(
            context, value.data(), static_cast<int>(value.size()), SQLITE_TRANSIENT
        );
    });
}

void drop(sqlite3_context* context, int argc, sqlite3_value** argv) {
    guarded(context, [&] {
        if (argc != 1) throw std::invalid_argument("certigap_drop expects 1 argument");
        const std::string name = text_argument(argv[0], "name");
        Registry& state = registry(context);
        std::lock_guard<std::mutex> lock(state.mutex);
        sqlite3_result_int(context, static_cast<int>(state.indexes.erase(name)));
    });
}

int register_function(
    sqlite3* database,
    const RegistryHandle& state,
    const char* name,
    int arguments,
    void (*function)(sqlite3_context*, int, sqlite3_value**)
) {
    return sqlite3_create_function_v2(
        database,
        name,
        arguments,
        SQLITE_UTF8 | SQLITE_DIRECTONLY,
        new RegistryHandle(state),
        function,
        nullptr,
        nullptr,
        destroy_handle
    );
}

}  // namespace

extern "C" int sqlite3_certigap_init(
    sqlite3* database,
    char** error,
    const sqlite3_api_routines* api
) {
    SQLITE_EXTENSION_INIT2(api);
    const auto state = std::make_shared<Registry>();
    const struct {
        const char* name;
        int arguments;
        void (*function)(sqlite3_context*, int, sqlite3_value**);
    } functions[] = {
        {"certigap_build", 2, build},
        {"certigap_get", 2, get},
        {"certigap_range_sum", 3, range_sum},
        {"certigap_update", 3, update},
        {"certigap_optimize", 1, optimize},
        {"certigap_selected", 1, selected},
        {"certigap_drop", 1, drop},
    };
    for (const auto& specification : functions) {
        const int result = register_function(
            database,
            state,
            specification.name,
            specification.arguments,
            specification.function
        );
        if (result != SQLITE_OK) {
            if (error != nullptr) {
                *error = sqlite3_mprintf(
                    "failed to register %s: %s",
                    specification.name,
                    sqlite3_errstr(result)
                );
            }
            return result;
        }
    }
    return certigap_register_vtab(database, error);
}
