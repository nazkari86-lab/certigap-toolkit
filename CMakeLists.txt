cmake_minimum_required(VERSION 3.16)
project(CertiGap VERSION 1.8.0 LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

option(CERTIGAP_BUILD_EXAMPLES "Build CertiGap C++ examples" OFF)

add_library(certigap INTERFACE)
add_library(CertiGap::certigap ALIAS certigap)
target_compile_features(certigap INTERFACE cxx_std_17)
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
