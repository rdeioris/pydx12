#include "pydx12.h"

PYDX12_TYPE_COM(IXAudio2);
PYDX12_TYPE_HANDLE(IXAudio2Voice, IXAudio2Voice*, IXAudio2* xaudio2);
PYDX12_TYPE_HANDLE(IXAudio2MasteringVoice, IXAudio2MasteringVoice*, IXAudio2* xaudio2);
PYDX12_TYPE_HANDLE(IXAudio2SourceVoice, IXAudio2SourceVoice*, IXAudio2* xaudio2);

PYDX12_TYPE(WAVEFORMATEX);
PYDX12_GETTER_SETTER(WAVEFORMATEX, wFormatTag, UnsignedLong, WORD);
PYDX12_GETTER_SETTER(WAVEFORMATEX, nChannels, UnsignedLong, WORD);
PYDX12_GETTER_SETTER(WAVEFORMATEX, nSamplesPerSec, UnsignedLong, DWORD);
PYDX12_GETTER_SETTER(WAVEFORMATEX, nAvgBytesPerSec, UnsignedLong, DWORD);
PYDX12_GETTER_SETTER(WAVEFORMATEX, nBlockAlign, UnsignedLong, WORD);
PYDX12_GETTER_SETTER(WAVEFORMATEX, wBitsPerSample, UnsignedLong, WORD);
PYDX12_GETTER_SETTER(WAVEFORMATEX, cbSize, UnsignedLong, WORD);
PYDX12_GETSETTERS(WAVEFORMATEX) = {
	PYDX12_DECLARE_GETTER_SETTER(WAVEFORMATEX, wFormatTag),
	PYDX12_DECLARE_GETTER_SETTER(WAVEFORMATEX, nChannels),
	PYDX12_DECLARE_GETTER_SETTER(WAVEFORMATEX, nSamplesPerSec),
	PYDX12_DECLARE_GETTER_SETTER(WAVEFORMATEX, nAvgBytesPerSec),
	PYDX12_DECLARE_GETTER_SETTER(WAVEFORMATEX, nBlockAlign),
	PYDX12_DECLARE_GETTER_SETTER(WAVEFORMATEX, wBitsPerSample),
	PYDX12_DECLARE_GETTER_SETTER(WAVEFORMATEX, cbSize),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(XAUDIO2_BUFFER);
PYDX12_GETTER_SETTER(XAUDIO2_BUFFER, Flags, UnsignedLong, UINT32);
PYDX12_GETTER_SETTER(XAUDIO2_BUFFER, AudioBytes, UnsignedLong, UINT32);
PYDX12_BUFFER_GETTER_SETTER(XAUDIO2_BUFFER, pAudioData, BYTE);
PYDX12_GETTER_SETTER(XAUDIO2_BUFFER, PlayBegin, UnsignedLong, UINT32);
PYDX12_GETTER_SETTER(XAUDIO2_BUFFER, PlayLength, UnsignedLong, UINT32);
PYDX12_GETTER_SETTER(XAUDIO2_BUFFER, LoopBegin, UnsignedLong, UINT32);
PYDX12_GETTER_SETTER(XAUDIO2_BUFFER, LoopLength, UnsignedLong, UINT32);
PYDX12_GETTER_SETTER(XAUDIO2_BUFFER, LoopCount, UnsignedLong, UINT32);
PYDX12_GETSETTERS(XAUDIO2_BUFFER) = {
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_BUFFER, Flags),
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_BUFFER, AudioBytes),
	PYDX12_DECLARE_GETTER_SETTER_CHUNK(XAUDIO2_BUFFER, pAudioData),
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_BUFFER, PlayBegin),
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_BUFFER, PlayLength),
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_BUFFER, LoopBegin),
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_BUFFER, LoopLength),
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_BUFFER, LoopCount),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(XAUDIO2_VOICE_STATE);
PYDX12_GETTER_SETTER(XAUDIO2_VOICE_STATE, BuffersQueued, UnsignedLong, UINT32);
PYDX12_GETTER_SETTER(XAUDIO2_VOICE_STATE, SamplesPlayed, UnsignedLongLong, UINT64);
PYDX12_GETSETTERS(XAUDIO2_VOICE_STATE) = {
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_VOICE_STATE, BuffersQueued),
	PYDX12_DECLARE_GETTER_SETTER(XAUDIO2_VOICE_STATE, SamplesPlayed),
	{ NULL }  /* Sentinel */
};

static PyObject* pydx12_IXAudio2_CreateMasteringVoice(pydx12_IXAudio2* self, PyObject* args)
{
	UINT32 input_channels = 0;
	UINT32 input_sample_rate = 0;
	UINT32 flags = 0;
	PyObject* py_device_id = NULL;
	PyObject* py_effect_chain = NULL;
	AUDIO_STREAM_CATEGORY stream_category = AudioCategory_GameEffects;
	if (!PyArg_ParseTuple(args, "|IIIOOL", &input_channels, &input_sample_rate, &flags, &py_device_id, &py_effect_chain, &stream_category))
		return NULL;

	IXAudio2MasteringVoice* mastering_voice;
	PYDX12_CALL_HRESULT(self->com_ptr->CreateMasteringVoice, &mastering_voice, input_channels, input_sample_rate, flags, NULL, NULL, stream_category);
	PYDX12_HANDLE_NEW_WITH_COM(IXAudio2MasteringVoice, mastering_voice, DestroyVoice, xaudio2);
}

static PyObject* pydx12_IXAudio2_CreateSourceVoice(pydx12_IXAudio2* self, PyObject* args)
{
	PyObject* py_source_format;
	UINT32 flags = 0;
	float max_frequency_ratio = 2.0;
	PyObject* py_callback = NULL;
	PyObject* py_send_list = NULL;
	PyObject* py_effect_chain = NULL;

	if (!PyArg_ParseTuple(args, "O|IfOOO", &py_source_format, &flags, &max_frequency_ratio, &py_callback, &py_send_list, &py_effect_chain))
		return NULL;

	PYDX12_ARG_CHECK(WAVEFORMATEX, source_format);

	IXAudio2SourceVoice* source_voice;
	PYDX12_CALL_HRESULT(self->com_ptr->CreateSourceVoice, &source_voice, source_format, flags, max_frequency_ratio, NULL, NULL, NULL);

	PYDX12_HANDLE_NEW_WITH_COM(IXAudio2SourceVoice, source_voice, DestroyVoice, xaudio2);
}

PYDX12_METHODS(IXAudio2) = {
	{"CreateMasteringVoice", (PyCFunction)pydx12_IXAudio2_CreateMasteringVoice, METH_VARARGS, "Creates and configures a mastering voice"},
	{"CreateSourceVoice", (PyCFunction)pydx12_IXAudio2_CreateSourceVoice, METH_VARARGS, "Creates and configures a source voice"},
	{NULL} /* Sentinel */
};

void* pydx12_IXAudio2Voice_init = NULL; // no need for __init__
static void pydx12_IXAudio2Voice_dealloc(pydx12_IXAudio2Voice* self)\
{
	if (self->handle)
		self->handle->DestroyVoice();
	if (self->xaudio2)
		self->xaudio2->Release();
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* pydx12_IXAudio2SourceVoice_SubmitSourceBuffer(pydx12_IXAudio2SourceVoice* self, PyObject* args)
{
	PyObject* py_buffer;
	PyObject* py_buffer_wma = NULL;

	if (!PyArg_ParseTuple(args, "O|O", &py_buffer, &py_buffer_wma))
		return NULL;

	PYDX12_ARG_CHECK(XAUDIO2_BUFFER, buffer);

	PYDX12_CALL_HRESULT(self->handle->SubmitSourceBuffer, buffer, NULL);

	Py_RETURN_NONE;
}

static PyObject* pydx12_IXAudio2SourceVoice_Start(pydx12_IXAudio2SourceVoice* self, PyObject* args)
{
	UINT32 flags = 0;
	UINT32 operation_set = XAUDIO2_COMMIT_NOW;

	if (!PyArg_ParseTuple(args, "|LL", &flags, &operation_set))
		return NULL;

	PYDX12_CALL_HRESULT(self->handle->Start, flags, operation_set);

	Py_RETURN_NONE;
}

static PyObject* pydx12_IXAudio2SourceVoice_Stop(pydx12_IXAudio2SourceVoice* self, PyObject* args)
{
	UINT32 flags = 0;
	UINT32 operation_set = XAUDIO2_COMMIT_NOW;

	if (!PyArg_ParseTuple(args, "|LL", &flags, &operation_set))
		return NULL;

	PYDX12_CALL_HRESULT(self->handle->Stop, flags, operation_set);

	Py_RETURN_NONE;
}

static PyObject* pydx12_IXAudio2SourceVoice_FlushSourceBuffers(pydx12_IXAudio2SourceVoice* self)
{
	PYDX12_CALL_HRESULT(self->handle->FlushSourceBuffers);
	Py_RETURN_NONE;
}

static PyObject* pydx12_IXAudio2SourceVoice_GetState(pydx12_IXAudio2SourceVoice* self, PyObject* args)
{
	UINT32 flags = 0;
	if (!PyArg_ParseTuple(args, "|L", &flags))
		return NULL;
	XAUDIO2_VOICE_STATE voice_state;
	self->handle->GetState(&voice_state, flags);
	return pydx12_XAUDIO2_VOICE_STATE_instantiate(&voice_state, NULL, NULL);
}

PYDX12_METHODS(IXAudio2SourceVoice) = {
	{"SubmitSourceBuffer", (PyCFunction)pydx12_IXAudio2SourceVoice_SubmitSourceBuffer, METH_VARARGS, "Adds a new audio buffer to the voice queue"},
	{"Start", (PyCFunction)pydx12_IXAudio2SourceVoice_Start, METH_VARARGS, "Starts consumption and processing of audio by the voice"},
	{"Stop", (PyCFunction)pydx12_IXAudio2SourceVoice_Stop, METH_VARARGS, "Stops consumption of audio by the current voice"},
	{"FlushSourceBuffers", (PyCFunction)pydx12_IXAudio2SourceVoice_FlushSourceBuffers, METH_NOARGS, "Removes all pending audio buffers from the voice queue"},
	{"GetState", (PyCFunction)pydx12_IXAudio2SourceVoice_GetState, METH_VARARGS, "Returns the voice's current cursor position data"},
	{NULL} /* Sentinel */
};


int pydx12_init_audio(PyObject* m)
{
	pydx12_IXAudio2Type.tp_methods = pydx12_IXAudio2_methods;
	PYDX12_REGISTER_COM(IXAudio2, IUnknown);

	PYDX12_REGISTER_HANDLE(IXAudio2Voice);

	PYDX12_REGISTER_SUBHANDLE(IXAudio2MasteringVoice, IXAudio2Voice);

	pydx12_IXAudio2SourceVoiceType.tp_methods = pydx12_IXAudio2SourceVoice_methods;
	PYDX12_REGISTER_SUBHANDLE(IXAudio2SourceVoice, IXAudio2Voice);

	PYDX12_REGISTER_STRUCT(WAVEFORMATEX);
	PYDX12_REGISTER_STRUCT(XAUDIO2_BUFFER);
	PYDX12_REGISTER_STRUCT(XAUDIO2_VOICE_STATE);

	PYDX12_ENUM(AudioCategory_Other);
	PYDX12_ENUM(AudioCategory_ForegroundOnlyMedia);
	PYDX12_ENUM(AudioCategory_Communications);
	PYDX12_ENUM(AudioCategory_Alerts);
	PYDX12_ENUM(AudioCategory_SoundEffects);
	PYDX12_ENUM(AudioCategory_GameEffects);
	PYDX12_ENUM(AudioCategory_GameMedia);
	PYDX12_ENUM(AudioCategory_GameChat);
	PYDX12_ENUM(AudioCategory_Speech);
	PYDX12_ENUM(AudioCategory_Movie);
	PYDX12_ENUM(AudioCategory_Media);

	PYDX12_ENUM(XAUDIO2_VOICE_NOPITCH);
	PYDX12_ENUM(XAUDIO2_VOICE_NOSRC);
	PYDX12_ENUM(XAUDIO2_VOICE_USEFILTER);

	PYDX12_ENUM(XAUDIO2_COMMIT_NOW);
	PYDX12_ENUM(XAUDIO2_COMMIT_ALL);

	PYDX12_ENUM(WAVE_FORMAT_PCM);

	return 0;
}