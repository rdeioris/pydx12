// Declarations the generator needs but the PIX headers only provide as C++ templates
// or as __forceinline helpers. Parsed together with pix3.h (see HEADERS in generate.py).
#pragma once
#include <d3d12.h>
#include <pix3.h>

// WinPixEventRuntime.dll exports for callers that can't use the PIXEvents.h templates.
// They take a plain string (no format arguments).
extern "C" {
void WINAPI PIXBeginEventOnCommandList(_In_ ID3D12GraphicsCommandList* commandList, UINT64 color, _In_ PCSTR formatString);
void WINAPI PIXEndEventOnCommandList(_In_ ID3D12GraphicsCommandList* commandList);
void WINAPI PIXSetMarkerOnCommandList(_In_ ID3D12GraphicsCommandList* commandList, UINT64 color, _In_ PCSTR formatString);
void WINAPI PIXBeginEventOnCommandQueue(_In_ ID3D12CommandQueue* commandQueue, UINT64 color, _In_ PCSTR formatString);
void WINAPI PIXEndEventOnCommandQueue(_In_ ID3D12CommandQueue* commandQueue);
void WINAPI PIXSetMarkerOnCommandQueue(_In_ ID3D12CommandQueue* commandQueue, UINT64 color, _In_ PCSTR formatString);
}

// pix3_win.h implements these inline by looking up an export of WinPixGpuCapturer.dll
// (installed with PIX). The generator binds them straight to those exports (FUNCTION_EXPORTS).
HRESULT WINAPI PIXGpuCaptureNextFrames(_In_ PCWSTR fileName, UINT32 numFrames);
HRESULT WINAPI PIXForceD3D11On12();
HRESULT WINAPI PIXSetHUDOptions(PIXHUDOptions hudOptions);
bool WINAPI PIXIsAttachedForGpuCapture();
// pix3_win.h's PIXSetTargetWindow wraps this void export in an HRESULT
void WINAPI PIXSetTargetWindow_Export(HWND hwnd);
