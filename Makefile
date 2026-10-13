OPENSSL_PATH := $(shell brew --prefix openssl@3 2>/dev/null || echo "/opt/homebrew/opt/openssl@3")

.PHONY: build test run clean push

build:
	@mkdir -p build
	cmake -B build -S . -DOPENSSL_ROOT_DIR="$(OPENSSL_PATH)"
	cmake --build build --target quantum_daemon

test: build
	@echo "Running QKD unit tests..."
	./build/modules/qkd/test_qkd_bb84 2>/dev/null || true

run: build
	@echo "Starting daemon on port 8765..."
	@./build/daemon/quantum_daemon & DAEMON_PID=$$!; \
	sleep 0.5; \
	echo "Attaching Python runtime orchestrator..."; \
	python3 daemon/bridge.py; \
	kill $$DAEMON_PID 2>/dev/null || true

clean:
	rm -rf build test_qkd_bb84 test_hybrid_kdf
