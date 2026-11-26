import ctypes
import os
import time
import wave

import pydx12 as dx

HERE = os.path.dirname(os.path.abspath(__file__))
NTDDI_WIN10 = 0x0A000000

# XAudio2 needs COM initialized on the calling thread
ctypes.windll.ole32.CoInitializeEx(None, 0)


def test_xaudio2():
    audio = dx.XAudio2CreateWithVersionInfo(0, dx.XAUDIO2_DEFAULT_PROCESSOR, NTDDI_WIN10)
    master = audio.CreateMasteringVoice()
    assert isinstance(master, dx.IXAudio2MasteringVoice)
    asset = wave.open(os.path.join(HERE, 'CantinaBand3.wav'), 'rb')
    data = asset.readframes(asset.getnframes())
    fmt = dx.WAVEFORMATEX(wFormatTag=dx.WAVE_FORMAT_PCM, nChannels=asset.getnchannels(),
                          nSamplesPerSec=asset.getframerate(), wBitsPerSample=asset.getsampwidth() * 8)
    fmt.nBlockAlign = fmt.nChannels * asset.getsampwidth()
    fmt.nAvgBytesPerSec = fmt.nSamplesPerSec * fmt.nBlockAlign
    voice = audio.CreateSourceVoice(fmt)
    buf = dx.XAUDIO2_BUFFER(pAudioData=data)
    assert buf.AudioBytes == len(data)
    voice.SubmitSourceBuffer(buf)
    assert voice.GetState(0).BuffersQueued == 1
    voice.DestroyVoice()
    master.DestroyVoice()


def test_xaudio2_callback():
    class Callback(dx.ComImplementation):
        _interfaces_ = (dx.IXAudio2EngineCallback,)

        def __init__(self):
            super().__init__()
            self.calls = 0

        def OnProcessingPassStart(self):
            self.calls += 1

    audio = dx.XAudio2CreateWithVersionInfo(0, dx.XAUDIO2_DEFAULT_PROCESSOR, NTDDI_WIN10)
    cb = Callback()
    audio.RegisterForCallbacks(cb)
    master = audio.CreateMasteringVoice()
    time.sleep(0.2)
    audio.UnregisterForCallbacks(cb)
    master.DestroyVoice()
    assert cb.calls > 0


def test_xinput():
    r, state = dx.XInputGetState(0)
    assert r in (0, 1167)  # ERROR_SUCCESS or ERROR_DEVICE_NOT_CONNECTED
    assert isinstance(state, dx.XINPUT_STATE)
