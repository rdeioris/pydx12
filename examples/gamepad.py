"""Gamepad, keyboard and mouse with GameInput, falling back to XInput.

A live drawing of the first gamepad: sticks, triggers, buttons and D-pad light up as you use them,
A rumbles the motors and the triggers drive the trigger motors (on pads that have them).
With GameInput the keys you hold and the mouse buttons, movement and wheel are shown too: one API
for every device.

GameInput needs GameInputRedist.dll (NuGet package Microsoft.GameInput): pass its folder with
--gameinput, or put the DLL next to python.exe. Without it the example uses XInput, built into Windows.

Usage: python examples/gamepad.py [--gameinput DIR] [--xinput] [--frames N]
"""
import argparse
import os
import time
import tkinter

import pydx12 as dx

BUTTONS = [  # name, x, y, GameInput flag, XInput flag
    ('A', 470, 210, dx.GameInputGamepadA, 0x1000),
    ('B', 510, 170, dx.GameInputGamepadB, 0x2000),
    ('X', 430, 170, dx.GameInputGamepadX, 0x4000),
    ('Y', 470, 130, dx.GameInputGamepadY, 0x8000),
    ('View', 280, 150, dx.GameInputGamepadView, 0x0020),
    ('Menu', 360, 150, dx.GameInputGamepadMenu, 0x0010),
    ('LB', 170, 84, dx.GameInputGamepadLeftShoulder, 0x0100),
    ('RB', 470, 84, dx.GameInputGamepadRightShoulder, 0x0200),
]
DPAD = [  # dx, dy, GameInput flag, XInput flag
    (0, -1, dx.GameInputGamepadDPadUp, 0x0001), (0, 1, dx.GameInputGamepadDPadDown, 0x0002),
    (-1, 0, dx.GameInputGamepadDPadLeft, 0x0004), (1, 0, dx.GameInputGamepadDPadRight, 0x0008),
]
STICK_BUTTONS = (dx.GameInputGamepadLeftThumbstick, 0x0040), (dx.GameInputGamepadRightThumbstick, 0x0080)


class Pad:
    """The gamepad state both backends produce: buttons as GameInput flags, axes in [-1, 1] / [0, 1]."""
    def __init__(self):
        self.connected = False
        self.buttons = 0
        self.lx = self.ly = self.rx = self.ry = 0.0
        self.lt = self.rt = 0.0


class GameInputBackend:
    name = 'GameInput'

    def __init__(self):
        self.gi = dx.GameInputInitialize()
        self.rumbling = None

    def read(self):
        pad = Pad()
        try:
            reading = self.gi.GetCurrentReading(dx.GameInputKindGamepad)
        except dx.DXError:  # GAMEINPUT_E_READING_NOT_FOUND: no gamepad
            return pad, None
        ok, state = reading.GetGamepadState()
        pad.connected = ok
        pad.buttons = state.buttons
        pad.lx, pad.ly = state.leftThumbstickX, state.leftThumbstickY
        pad.rx, pad.ry = state.rightThumbstickX, state.rightThumbstickY
        pad.lt, pad.rt = state.leftTrigger, state.rightTrigger
        return pad, reading.GetDevice()

    def rumble(self, device, low, high, left_trigger, right_trigger):
        if device is not None:
            device.SetRumbleState(dx.GameInputRumbleParams(lowFrequency=low, highFrequency=high,
                                                           leftTrigger=left_trigger, rightTrigger=right_trigger))

    def keys(self):
        try:
            reading = self.gi.GetCurrentReading(dx.GameInputKindKeyboard)
        except dx.DXError:
            return []
        count = reading.GetKeyCount()
        if not count:
            return []
        _, states = reading.GetKeyState(count)
        return [state.virtualKey for state in states]

    def mouse(self):
        try:
            reading = self.gi.GetCurrentReading(dx.GameInputKindMouse)
        except dx.DXError:
            return None
        ok, state = reading.GetMouseState()
        return state if ok else None


class XInputBackend:
    name = 'XInput'
    ERROR_SUCCESS = 0

    def read(self):
        pad = Pad()
        result, state = dx.XInputGetState(0)
        if result != self.ERROR_SUCCESS:
            return pad, None
        g = state.Gamepad
        pad.connected = True
        for _, _, _, gi_flag, xi_flag in BUTTONS:
            if g.wButtons & xi_flag:
                pad.buttons |= gi_flag
        for _, _, gi_flag, xi_flag in DPAD:
            if g.wButtons & xi_flag:
                pad.buttons |= gi_flag
        for gi_flag, xi_flag in STICK_BUTTONS:
            if g.wButtons & xi_flag:
                pad.buttons |= gi_flag
        pad.lx, pad.ly = g.sThumbLX / 32768, g.sThumbLY / 32768
        pad.rx, pad.ry = g.sThumbRX / 32768, g.sThumbRY / 32768
        pad.lt, pad.rt = g.bLeftTrigger / 255, g.bRightTrigger / 255
        return pad, 0

    def rumble(self, device, low, high, left_trigger, right_trigger):
        # XInput has no trigger motors: fold them into the main ones
        dx.XInputSetState(0, dx.XINPUT_VIBRATION(wLeftMotorSpeed=int(min(1, low + left_trigger) * 65535),
                                                 wRightMotorSpeed=int(min(1, high + right_trigger) * 65535)))

    def keys(self):
        return []

    def mouse(self):
        return None


def key_name(vk):
    if 0x30 <= vk <= 0x5A:
        return chr(vk)
    names = {0x08: 'Backspace', 0x09: 'Tab', 0x0D: 'Enter', 0x10: 'Shift', 0x11: 'Ctrl', 0x12: 'Alt', 0x1B: 'Esc',
             0x20: 'Space', 0x25: 'Left', 0x26: 'Up', 0x27: 'Right', 0x28: 'Down', 0xA0: 'LShift', 0xA1: 'RShift',
             0xA2: 'LCtrl', 0xA3: 'RCtrl', 0xA4: 'LAlt', 0xA5: 'RAlt', 0x5B: 'Win'}
    if 0x70 <= vk <= 0x87:
        return 'F%d' % (vk - 0x6F)
    return names.get(vk, '0x%02X' % vk)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gameinput', help='folder containing GameInputRedist.dll')
    ap.add_argument('--xinput', action='store_true', help='use XInput even if GameInput is available')
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames (0 = run until closed)')
    args = ap.parse_args()

    backend: GameInputBackend | XInputBackend | None = None
    if not args.xinput:
        if args.gameinput:
            os.add_dll_directory(os.path.abspath(args.gameinput))
        try:
            backend = GameInputBackend()
        except (OSError, NotImplementedError, dx.DXError) as e:
            print('GameInput not available (%s), using XInput' % e)
    if backend is None:
        backend = XInputBackend()

    root = tkinter.Tk()
    root.title('pydx12: input with %s' % backend.name)
    canvas = tkinter.Canvas(root, width=640, height=400, bg='#15171c', highlightthickness=0)
    canvas.pack()
    closed = []
    root.protocol('WM_DELETE_WINDOW', lambda: closed.append(True))

    off, on, line = '#2a2e38', '#4fc3f7', '#5b6170'
    frames = 0
    while not closed and (not args.frames or frames < args.frames):
        pad, device = backend.read()
        canvas.delete('all')
        # body
        canvas.create_oval(110, 90, 290, 330, fill='#1e2129', outline=line, width=2)
        canvas.create_oval(350, 90, 530, 330, fill='#1e2129', outline=line, width=2)
        canvas.create_rectangle(200, 110, 440, 250, fill='#1e2129', outline='')
        canvas.create_text(320, 30, fill='#c0c4cc', font=('Segoe UI', 13),
                           text='%s: %s' % (backend.name, 'gamepad connected' if pad.connected else 'no gamepad'))
        # triggers
        for x, value, label in ((140, pad.lt, 'LT'), (440, pad.rt, 'RT')):
            canvas.create_rectangle(x, 40, x + 60, 52, outline=line)
            canvas.create_rectangle(x, 40, x + 60 * value, 52, fill=on, outline='')
            canvas.create_text(x + 30, 62, text=label, fill='#8a909c', font=('Segoe UI', 8))
        # sticks
        for cx, cy, sx, sy, (gi_flag, _) in ((200, 180, pad.lx, pad.ly, STICK_BUTTONS[0]),
                                             (400, 250, pad.rx, pad.ry, STICK_BUTTONS[1])):
            pressed = pad.buttons & gi_flag
            canvas.create_oval(cx - 36, cy - 36, cx + 36, cy + 36, outline=line, width=2)
            canvas.create_oval(cx + sx * 24 - 14, cy - sy * 24 - 14, cx + sx * 24 + 14, cy - sy * 24 + 14,
                               fill=on if pressed else '#3a3f4b', outline=on)
        # d-pad
        for ddx, ddy, gi_flag, _ in DPAD:
            x, y = 250 + ddx * 22, 250 + ddy * 22
            canvas.create_rectangle(x - 10, y - 10, x + 10, y + 10, fill=on if pad.buttons & gi_flag else off,
                                    outline=line)
        # buttons
        for name, x, y, gi_flag, _ in BUTTONS:
            fill = on if pad.buttons & gi_flag else off
            if name in ('LB', 'RB'):
                canvas.create_rectangle(x - 30, y - 9, x + 30, y + 9, fill=fill, outline=line)
            else:
                r = 16 if len(name) == 1 else 11
                canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=line)
            canvas.create_text(x, y, text=name, fill='white', font=('Segoe UI', 8, 'bold'))
        # rumble: A shakes the big motors, the triggers drive the trigger motors
        a_down = 1.0 if pad.buttons & dx.GameInputGamepadA else 0.0
        if pad.connected:
            backend.rumble(device, a_down * 0.6, a_down * 0.3, pad.lt * 0.5, pad.rt * 0.5)
        # keyboard and mouse (GameInput only)
        keys = backend.keys()
        mouse = backend.mouse()
        if backend.name == 'GameInput':
            canvas.create_text(20, 360, anchor='w', fill='#c0c4cc', font=('Consolas', 10),
                               text='keys: %s' % (' '.join(key_name(k) for k in keys) or '-'))
            if mouse is not None:
                b = mouse.buttons
                canvas.create_text(20, 382, anchor='w', fill='#c0c4cc', font=('Consolas', 10),
                                   text='mouse: x %d y %d wheel %d  buttons %s%s%s' % (
                                       mouse.positionX, mouse.positionY, mouse.wheelY,
                                       'L' if b & dx.GameInputMouseLeftButton else '-',
                                       'M' if b & dx.GameInputMouseMiddleButton else '-',
                                       'R' if b & dx.GameInputMouseRightButton else '-'))
        root.update()
        time.sleep(1 / 120)
        frames += 1
    if isinstance(backend, XInputBackend):
        backend.rumble(None, 0, 0, 0, 0)
    root.destroy()
    print('%d frames with %s' % (frames, backend.name))


if __name__ == '__main__':
    main()
