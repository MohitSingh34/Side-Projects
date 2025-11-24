#!/usr/bin/env python3
import sys, termios, tty, time, asyncio

last_typed = time.time()
typing = False

async def detect_typing(timeout=3):
    """Detect when user starts and stops typing in real time."""
    global last_typed, typing

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    print("Start typing (press Ctrl+C to exit):\n")
    try:
        tty.setcbreak(fd)  # switch to character-by-character mode
        while True:
            await asyncio.sleep(0.05)
            if is_input_available(fd):
                ch = sys.stdin.read(1)
                last_typed = time.time()
                if not typing:
                    typing = True
                    print("[💬] Typing detected...")
                if ch == "\n":
                    print("(Enter pressed)")
            else:
                if typing and time.time() - last_typed > timeout:
                    typing = False
                    print("[⏸️] Typing stopped (user idle now)")
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\n[✅] Exiting cleanly.")


def is_input_available(fd):
    import select
    return fd in select.select([fd], [], [], 0)[0]


if __name__ == "__main__":
    asyncio.run(detect_typing())
