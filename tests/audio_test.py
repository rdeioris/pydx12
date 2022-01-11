import unittest
import weakref
import sys
from pydx12 import *
import wave


class AudioTests(unittest.TestCase):

    def test_xaudio2create(self):
        audio = XAudio2Create()
        self.assertIsInstance(audio, IXAudio2)
        asset = wave.open('CantinaBand3.wav', 'rb')
        sound_data = asset.readframes(asset.getnframes())
        master_voice = audio.CreateMasteringVoice()
        self.assertIsInstance(master_voice, IXAudio2MasteringVoice)
        format = WAVEFORMATEX(wFormatTag=WAVE_FORMAT_PCM)
        format.nChannels=asset.getnchannels()
        format.nSamplesPerSec=asset.getframerate()
        format.wBitsPerSample=asset.getsampwidth() * 8
        format.nBlockAlign = format.nChannels * asset.getsampwidth()
        format.nAvgBytesPerSec = format.nSamplesPerSec * format.nBlockAlign
        source_voice = audio.CreateSourceVoice(format)
        self.assertIsInstance(source_voice, IXAudio2SourceVoice)
        buffer = XAUDIO2_BUFFER()
        buffer.AudioBytes = len(sound_data)
        buffer.pAudioData = sound_data
        source_voice.SubmitSourceBuffer(buffer)
        state = source_voice.GetState()
        self.assertEqual(state.BuffersQueued, 1)