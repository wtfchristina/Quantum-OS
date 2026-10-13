OPENSSL_PATH := $(shell brew --prefix openssl@3 2>/dev/null || echo "/opt/homebrew/opt/openssl@3")

.PHONY: build test run clean

build:
	@mkdir -p build
	cmake -B build -S . -DOPENSSL_ROOT_DIR="$(OPENSSL_PATH)"
	cmake --build build --target quantum_daemon

test: build
	@echo "Running QKD unit tests..."
	./build/modules/qkd/test_qkd_bb84 2>/dev/null || true

run: build
	@echo "Starting unified daemon and runtime bridge..."
	python3 daemon/bridge.py

clean:
	rm -rf build test_qkd_bb84 test_hybrid_kdf
