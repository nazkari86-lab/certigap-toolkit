cmake_minimum_required(VERSION 3.16)
project(certigap_autoindex_example LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

get_filename_component(CERTIGAP_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(GENERATED_HEADER "${CMAKE_CURRENT_BINARY_DIR}/generated_index.hpp")
set(SELECTION_ARTIFACT "${CMAKE_CURRENT_BINARY_DIR}/selection.json")

add_custom_command(
    OUTPUT "${GENERATED_HEADER}" "${SELECTION_ARTIFACT}"
    COMMAND
        "${CMAKE_COMMAND}" -E env "PYTHONPATH=${CERTIGAP_ROOT}"
        "${Python3_EXECUTABLE}" -m certigap.cli compile
        "${CMAKE_CURRENT_LIST_DIR}/trace.json"
        --artifact "${SELECTION_ARTIFACT}"
        --header "${GENERATED_HEADER}"
    DEPENDS
        "${CMAKE_CURRENT_LIST_DIR}/trace.json"
        "${CERTIGAP_ROOT}/certigap/compiler.py"
        "${CERTIGAP_ROOT}/certigap/cli.py"
        "${CERTIGAP_ROOT}/cpp/certigap_autoindex.hpp"
    VERBATIM
)

add_executable(
    certigap_autoindex_example
    main.cpp
    "${GENERATED_HEADER}"
)
target_compile_features(certigap_autoindex_example PRIVATE cxx_std_17)
target_include_directories(
    certigap_autoindex_example
    PRIVATE
        "${CMAKE_CURRENT_BINARY_DIR}"
        "${CERTIGAP_ROOT}/cpp"
)
