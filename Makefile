.PHONY: setup run run-real native clean phase0 doctor test

setup:            ## install core deps into a venv
	cd core && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run:              ## start core in MOCK mode (no phones needed)
	cd core && . .venv/bin/activate && ORCH_MOCK=true python -m core

run-real:         ## start core against real devices (needs Phase 0 done)
	cd core && . .venv/bin/activate && ORCH_MOCK=false python -m core

native:           ## run the SwiftUI client (macOS)
	cd native && swift run

test:             ## run the test suite
	cd core && . .venv/bin/activate && PYTHONPATH=. pytest tests

doctor:           ## Phase 0 doctor — validate the real-device setup
	cd core && . .venv/bin/activate && PYTHONPATH=. python -m core.phase0

phase0:           ## low-level smoke-test a single device (pass UDID=...)
	bash core/scripts/phase0_smoke.sh $(UDID)

clean:
	rm -rf core/.venv core/data core/**/__pycache__
