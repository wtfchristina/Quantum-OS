cmake_minimum_required(VERSION 3.24)
project(QuantumOS_Unified VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(OpenSSL REQUIRED)

# QKD and Security subsystems
add_subdirectory(modules/qkd)
add_subdirectory(daemon)

# Add remaining submodules if their CMakeLists exist
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/core/CMakeLists.txt")
    add_subdirectory(core)
endif()

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/modules/physics/CMakeLists.txt")
    add_subdirectory(modules/physics)
endif()
