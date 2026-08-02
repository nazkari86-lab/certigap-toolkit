cmake_minimum_required(VERSION 3.16)
project(CertiGap VERSION 1.16.0 LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
find_package(Threads REQUIRED)

option(CERTIGAP_BUILD_EXAMPLES "Build CertiGap C++ examples" OFF)
option(CERTIGAP_BUILD_SQLITE_EXTENSION "Build SQLite loadable extension" OFF)

add_library(certigap INTERFACE)
add_library(CertiGap::certigap ALIAS certigap)
target_compile_features(certigap INTERFACE cxx_std_17)
target_link_libraries(certigap INTERFACE Threads::Threads)
target_include_directories(
    certigap
    INTERFACE
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/cpp>"
        "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/certigap>"
)

if(CERTIGAP_BUILD_EXAMPLES)
    add_executable(
        certigap_online_example
        examples/online_single_file.cpp
    )
    target_link_libraries(
        certigap_online_example PRIVATE CertiGap::certigap
    )
    add_executable(
        certigap_adaptive_array_example
        examples/adaptive_array.cpp
    )
    target_link_libraries(
        certigap_adaptive_array_example PRIVATE CertiGap::certigap
    )
endif()

if(CERTIGAP_BUILD_SQLITE_EXTENSION)
    find_path(SQLITE3EXT_INCLUDE_DIR sqlite3ext.h REQUIRED)
    add_library(
        certigap_sqlite MODULE
        cpp/certigap_sqlite.cpp
        cpp/certigap_sqlite_vtab.cpp
    )
    target_compile_features(certigap_sqlite PRIVATE cxx_std_17)
    target_include_directories(
        certigap_sqlite PRIVATE
            "${CMAKE_CURRENT_SOURCE_DIR}/cpp"
            "${SQLITE3EXT_INCLUDE_DIR}"
    )
    set_target_properties(
        certigap_sqlite PROPERTIES
            PREFIX ""
            OUTPUT_NAME "certigap"
    )
    if(APPLE)
        # SQLite resolves extension API symbols from the loading process.
        target_link_options(
            certigap_sqlite PRIVATE "LINKER:-undefined,dynamic_lookup"
        )
    endif()
endif()

install(
    TARGETS certigap
    EXPORT CertiGapTargets
)
install(
    FILES
        cpp/certigap.hpp
        cpp/certigap_adaptive.hpp
        cpp/certigap_autoindex.hpp
        cpp/certigap_tracking.hpp
        cpp/certigap_concurrent.hpp
        cpp/certigap_synth.hpp
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/certigap"
)
install(
    EXPORT CertiGapTargets
    FILE CertiGapTargets.cmake
    NAMESPACE CertiGap::
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/CertiGap"
)

configure_package_config_file(
    cmake/CertiGapConfig.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/CertiGapConfig.cmake"
    INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/CertiGap"
)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/CertiGapConfigVersion.cmake"
    VERSION "${PROJECT_VERSION}"
    COMPATIBILITY SameMajorVersion
)
install(
    FILES
        "${CMAKE_CURRENT_BINARY_DIR}/CertiGapConfig.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/CertiGapConfigVersion.cmake"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/CertiGap"
)
configure_file(
    cmake/certigap.pc.in
    "${CMAKE_CURRENT_BINARY_DIR}/certigap.pc"
    @ONLY
)
install(
    FILES "${CMAKE_CURRENT_BINARY_DIR}/certigap.pc"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/pkgconfig"
)
