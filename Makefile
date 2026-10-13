OPENSSL_PATH := $(shell brew --prefix openssl@3 2>/dev/null || echo "/opt/homebrew/opt/openssl@3")

.PHONY: all build test start stop clean push

all: build

build:
	@mkdir -p build
	cmake -B build -S . -DOPENSSL_ROOT_DIR="$(OPENSSL_PATH)"
	cmake --build build --target test_qkd_bb84 quantum_daemon

test: build
	@echo "==> Running BB84 Protocol & KME Tests..."
	./build/modules/qkd/test_qkd_bb84

start:
	@./bin/start-cockpit

stop:
	@echo "Terminating any running processes on 3000 / 8765..."
	@lsof -ti :3000 | xargs kill -9 2>/dev/null || true
	@lsof -ti :8765 | xargs kill -9 2>/dev/null || true
	@pkill -f "daemon/bridge.py" 2>/dev/null || true
	@echo "All stopped."

clean: stop
	rm -rf build apps/cockpit/telemetry.json apps/cockpit/attack.flag

verify: build
	@./bin/verify-stack
