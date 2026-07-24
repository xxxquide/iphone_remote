"""Device Bridge: a single internal contract over heterogeneous CLIs.

Real backends:
  - devicectl        (Apple CoreDevice: install/launch/openURL/screenshot)
  - WebDriverAgent   (tap/type/element tree/MJPEG)  -> wda.py
  - pymobiledevice3  (iOS 17+ tunnel + HEVC stream) -> tunnel.py / streaming.py
  - go-ios           (alternative tunnel / runwda)  -> tunnel.py

In mock mode every wrapper returns canned data so the stack runs with no phones.
"""
