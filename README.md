# chia-suspend
A chia-blockchain suspension utility used to pause plotting in a manner that can be resumed after a system shutdown/reboot. This python wrapper leverages plotman (https://github.com/ericaltendorf/plotman/) and Checkpoint/Restore In Userspace, or CRIU (https://criu.org), the latter of which likely may mean that this utility will work on Linux only.

Currently set up to run/call 'sudo criu' internally. Untested, but this may required passwordless sudo, as is the case in my plotting VM.

Written by a self-taught programmer who is keen to receive constructive criticism and/or contributions.
