add_executable(quantum_daemon
    src/main.cpp
)

target_include_directories(quantum_daemon PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/modules/qkd/include
    ${CMAKE_SOURCE_DIR}/modules/security/include
)

target_link_libraries(quantum_daemon PRIVATE
    qkd_engine
    OpenSSL::Crypto
)

target_compile_features(quantum_daemon PRIVATE cxx_std_20)
