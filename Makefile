.PHONY: setup run run-real native clean phase0

setup:            ## install core deps into a venv
	cd core && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run:              ## start core in MOCK mode (no phones needed)
	cd core && . .venv/bin/activate && ORCH_MOCK=true python -m core

run-real:         ## start core against real devices (needs Phase 0 done)
	cd core && . .venv/bin/activate && ORCH_MOCK=false python -m core

native:           ## run the SwiftUI client (macOS)
	cd native && swift run

phase0:           ## smoke-test a device (pass UDID=...)
	bash core/scripts/phase0_smoke.sh $(UDID)

clean:
	rm -rf core/.venv core/data core/**/__pycache__
