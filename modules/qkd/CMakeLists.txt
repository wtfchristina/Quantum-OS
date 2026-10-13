add_library(qkd_engine STATIC
    src/bb84.cpp
    src/etsi014_kme.cpp
)

target_include_directories(qkd_engine PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(qkd_engine PUBLIC cxx_std_20)

add_executable(test_qkd_bb84 tests/test_bb84.cpp)
target_link_libraries(test_qkd_bb84 PRIVATE qkd_engine)
