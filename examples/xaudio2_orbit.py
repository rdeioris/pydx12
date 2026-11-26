"""3D audio: a synthesized loop orbiting around you, with XAudio2 and X3DAudio.

- the sound (a little arpeggio with an echo) is synthesized with numpy and looped by a source voice
- every 20 ms X3DAudio computes panning, distance attenuation, the low-pass filter of a sound
  behind you and the Doppler shift for the emitter's position and velocity
- the source voice also feeds a submix voice running the XAudio2 reverb, scaled by X3DAudio's
  reverb level, so the room gets wetter as the sound moves away
- a volume meter effect on the mastering voice reports the real output levels: the terminal shows
  where the sound is and the left/right peaks it produces

Usage: python examples/xaudio2_orbit.py [--seconds 12] [--radius 4]
"""
import argparse
import ctypes
import math
import time

import numpy

import pydx12 as dx

RATE = 48000
NTDDI_WIN10 = 0x0A000000


def synth_loop():
    """Two bars of a minor arpeggio: plucked saw waves with a short echo, mono float32."""
    beat = 0.125
    notes = [57, 60, 64, 69, 72, 69, 64, 60, 55, 59, 62, 67, 71, 67, 62, 59]  # MIDI numbers
    out = numpy.zeros(int(len(notes) * beat * RATE), numpy.float32)
    t = numpy.arange(int(beat * 2 * RATE)) / RATE
    for i, note in enumerate(notes):
        freq = 440.0 * 2 ** ((note - 69) / 12)
        saw = 2.0 * (t * freq % 1.0) - 1.0
        tone = (saw + 0.5 * numpy.sin(2 * math.pi * freq * t)) * numpy.exp(-t * 9)
        start = int(i * beat * RATE)
        end = min(start + len(tone), len(out))
        out[start:end] += tone[:end - start]
    echo = int(0.375 * RATE)
    out[echo:] += 0.35 * out[:-echo]
    return (out / numpy.abs(out).max() * 0.8).astype(numpy.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=12.0)
    ap.add_argument('--radius', type=float, default=4.0, help='orbit radius in metres')
    args = ap.parse_args()

    ctypes.windll.ole32.CoInitializeEx(None, 0)  # XAudio2 needs COM on this thread
    xaudio = dx.XAudio2CreateWithVersionInfo(0, dx.XAUDIO2_DEFAULT_PROCESSOR, NTDDI_WIN10)

    # mastering voice with a volume meter, so we can watch what reaches the speakers
    meter = dx.CreateAudioVolumeMeter()
    master = xaudio.CreateMasteringVoice(pEffectChain=dx.XAUDIO2_EFFECT_CHAIN(pEffectDescriptors=[
        dx.XAUDIO2_EFFECT_DESCRIPTOR(pEffect=meter, InitialState=1, OutputChannels=2)]))
    speakers = master.GetVoiceDetails().InputChannels
    channel_mask = master.GetChannelMask()
    print('output: %d channels (mask 0x%X)' % (speakers, channel_mask))

    # reverb submix
    reverb = dx.CreateAudioReverb()
    room = xaudio.CreateSubmixVoice(1, RATE, pEffectChain=dx.XAUDIO2_EFFECT_CHAIN(pEffectDescriptors=[
        dx.XAUDIO2_EFFECT_DESCRIPTOR(pEffect=reverb, InitialState=1, OutputChannels=1)]))
    params = dx.XAUDIO2FX_REVERB_PARAMETERS(
        WetDryMix=100, ReflectionsDelay=12, ReverbDelay=20, RearDelay=dx.XAUDIO2FX_REVERB_DEFAULT_REAR_DELAY,
        SideDelay=dx.XAUDIO2FX_REVERB_DEFAULT_REAR_DELAY, PositionLeft=dx.XAUDIO2FX_REVERB_DEFAULT_POSITION,
        PositionRight=dx.XAUDIO2FX_REVERB_DEFAULT_POSITION,
        PositionMatrixLeft=dx.XAUDIO2FX_REVERB_DEFAULT_POSITION_MATRIX,
        PositionMatrixRight=dx.XAUDIO2FX_REVERB_DEFAULT_POSITION_MATRIX,
        EarlyDiffusion=15, LateDiffusion=15, LowEQGain=8, LowEQCutoff=4, HighEQGain=8, HighEQCutoff=6,
        RoomFilterFreq=5000, RoomFilterMain=-6, RoomFilterHF=-12, ReflectionsGain=-3, ReverbGain=0,
        DecayTime=2.2, Density=100, RoomSize=60)
    room.SetEffectParameters(0, params)

    # the orbiting sound: a mono float32 loop sent both to the speakers and to the room
    pcm = synth_loop()
    fmt = dx.WAVEFORMATEX(wFormatTag=dx.WAVE_FORMAT_IEEE_FLOAT, nChannels=1, nSamplesPerSec=RATE,
                          wBitsPerSample=32, nBlockAlign=4, nAvgBytesPerSec=RATE * 4)
    sends = dx.XAUDIO2_VOICE_SENDS(pSends=[dx.XAUDIO2_SEND_DESCRIPTOR(pOutputVoice=master),
                                           dx.XAUDIO2_SEND_DESCRIPTOR(pOutputVoice=room)])
    source = xaudio.CreateSourceVoice(fmt, dx.XAUDIO2_VOICE_USEFILTER, 2.0, pSendList=sends)
    source.SubmitSourceBuffer(dx.XAUDIO2_BUFFER(pAudioData=pcm.tobytes(), LoopCount=dx.XAUDIO2_LOOP_INFINITE))

    # X3DAudio state
    x3d = dx.X3DAUDIO_HANDLE()
    dx.X3DAudioInitialize(channel_mask, dx.X3DAUDIO_SPEED_OF_SOUND, x3d)
    listener = dx.X3DAUDIO_LISTENER()
    listener.OrientFront = dx.X3DAUDIO_VECTOR(0, 0, 1)
    listener.OrientTop = dx.X3DAUDIO_VECTOR(0, 1, 0)
    # distances are measured in units of CurveDistanceScaler metres; the reverb send grows with distance
    reverb_curve = dx.X3DAUDIO_DISTANCE_CURVE(pPoints=[dx.X3DAUDIO_DISTANCE_CURVE_POINT(0.0, 0.0),
                                                       dx.X3DAUDIO_DISTANCE_CURVE_POINT(1.0, 0.9)])
    emitter = dx.X3DAUDIO_EMITTER(ChannelCount=1, CurveDistanceScaler=args.radius * 3, DopplerScaler=1.0,
                                  InnerRadius=0.5, pReverbCurve=ctypes.pointer(reverb_curve))
    emitter.OrientFront = dx.X3DAUDIO_VECTOR(0, 0, 1)
    emitter.OrientTop = dx.X3DAUDIO_VECTOR(0, 1, 0)
    matrix = (ctypes.c_float * speakers)()
    dsp = dx.X3DAUDIO_DSP_SETTINGS(pMatrixCoefficients=matrix, SrcChannelCount=1, DstChannelCount=speakers)
    flags = (dx.X3DAUDIO_CALCULATE_MATRIX | dx.X3DAUDIO_CALCULATE_DOPPLER | dx.X3DAUDIO_CALCULATE_LPF_DIRECT |
             dx.X3DAUDIO_CALCULATE_REVERB)

    peaks = (ctypes.c_float * 2)()
    rms = (ctypes.c_float * 2)()
    levels = dx.XAUDIO2FX_VOLUMEMETER_LEVELS(pPeakLevels=peaks, pRMSLevels=rms, ChannelCount=2)

    source.Start()
    print('a sound is orbiting you: front -> right -> back -> left (Ctrl+C to stop)\n')
    start = time.perf_counter()
    angular = 2 * math.pi / 5.0  # one lap every 5 seconds
    # an ellipse, long from front to back: on a circle around you there would be no Doppler shift
    side, depth = args.radius, args.radius * 3
    try:
        while (now := time.perf_counter() - start) < args.seconds:
            angle = now * angular
            # clockwise seen from above: +x is right, +z is in front of the listener
            emitter.Position = dx.X3DAUDIO_VECTOR(side * math.sin(angle), 0, depth * math.cos(angle))
            emitter.Velocity = dx.X3DAUDIO_VECTOR(side * angular * math.cos(angle), 0,
                                                  -depth * angular * math.sin(angle))
            dx.X3DAudioCalculate(x3d, listener, emitter, flags, dsp)
            source.SetOutputMatrix(master, 1, speakers, matrix)
            source.SetOutputMatrix(room, 1, 1, (ctypes.c_float * 1)(dsp.ReverbLevel))
            source.SetFrequencyRatio(dsp.DopplerFactor)
            # muffle the sound when it is behind you (conversion from Microsoft's X3DAudio sample)
            source.SetFilterParameters(dx.XAUDIO2_FILTER_PARAMETERS(
                Type=dx.LowPassFilter, Frequency=2.0 * math.sin(math.pi / 6.0 * dsp.LPFDirectCoefficient),
                OneOverQ=1.0))

            master.GetEffectParameters(0, ctypes.byref(levels), ctypes.sizeof(levels))
            radar = [' '] * 25
            radar[int(round((math.sin(angle) + 1) * 12))] = '@'
            where = 'front' if math.cos(angle) > 0.5 else 'back ' if math.cos(angle) < -0.5 else '     '
            print('\r  L [%s] R  %s  peak L %4.2f R %4.2f  doppler %4.2f  reverb %4.2f ' % (
                ''.join(radar), where, peaks[0], peaks[1], dsp.DopplerFactor, dsp.ReverbLevel), end='', flush=True)
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    print()
    source.Stop()
    source.DestroyVoice()
    room.DestroyVoice()
    master.DestroyVoice()


if __name__ == '__main__':
    main()
