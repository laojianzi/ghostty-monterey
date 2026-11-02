#!/usr/bin/env python3
"""Check production hidden-window movement lease in debug and optimized AppKit fixtures.

Complements actual native handle drags; does not replace gesture routing tests.
"""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "macos/Sources/Ghostty/Surface View/SurfaceDragSource.swift").read_text()
start = source.index("        private weak var movementWindow")
end = source.index("        deinit {", start)
methods = source[start:end].replace("private ", "")
code='''import AppKit
class HiddenTitlebarTerminalWindow: NSWindow {}
class Probe: NSView {
'''+methods+'''
 override func viewWillMove(toWindow newWindow: NSWindow?) {
  if newWindow !== window { restoreWindowMovement() }
  super.viewWillMove(toWindow:newWindow)
 }
 deinit { restoreWindowMovement() }
}
@main struct Main {
 static func main() {
  _ = NSApplication.shared
  let hidden=HiddenTitlebarTerminalWindow(contentRect:NSRect(x:10,y:10,width:100,height:100),styleMask:[.titled],backing:.buffered,defer:false)
  let normal=NSWindow(contentRect:NSRect(x:10,y:10,width:100,height:100),styleMask:[.titled],backing:.buffered,defer:false)
  var probe:Probe?=Probe();hidden.contentView=probe
  for _ in 0..<20 {
   hidden.isMovable=true;probe!.suspendWindowMovement();precondition(!hidden.isMovable)
   probe!.suspendWindowMovement();probe!.restoreWindowMovement();precondition(hidden.isMovable)
  }
  hidden.isMovable=false;probe!.suspendWindowMovement();probe!.restoreWindowMovement();precondition(!hidden.isMovable)
  hidden.isMovable=true;probe!.suspendWindowMovement();probe!.removeFromSuperview();precondition(hidden.isMovable)
  normal.contentView=probe;normal.isMovable=true;probe!.suspendWindowMovement();precondition(normal.isMovable)
  hidden.contentView=probe;probe!.suspendWindowMovement();precondition(!hidden.isMovable)
  hidden.contentView=nil;probe=nil;precondition(hidden.isMovable)
  print("PASS: hidden-only suspend, idempotence, false-state preservation, detach and release")
 }
}
'''
for optimize in ("-Onone", "-O"):
    with tempfile.TemporaryDirectory(prefix="ghostty-hidden-drag-") as directory:
        work = Path(directory)
        swift = work / "main.swift"
        binary = work / "check"
        swift.write_text(code)
        subprocess.run(["xcrun", "swiftc", "-parse-as-library", optimize,
                        str(swift), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=10)
