from setuptools import setup, Extension

module = Extension('pydx12.api',
                   libraries=['dxgi', 'd3d12', 'd3dcompiler', 'user32'],
                   depends=['pydx12/pydx12.h'],
                   sources=['pydx12/' + source for source in ('pydx12.cpp',
                                                              'dxgi.cpp',
                                                              'adapter.cpp',
                                                              'luid.cpp',
                                                              'device.cpp',
                                                              'resource.cpp',
                                                              'signature.cpp',
                                                              'queue.cpp',
                                                              'message.cpp',
                                                              'swapchain.cpp',
                                                              'fence.cpp',
                                                              'descriptor.cpp',
                                                              'shader.cpp',
                                                              'pipeline.cpp')
                            ])

setup(name='pydx12',
      version='0.1',
      description='DirectX12 python wrapper',
      author='Roberto De Ioris',
      author_email='roberto.deioris@gmail.com',
      url='https://github.com/rdeioris/pydx12',
      long_description='''
Exposes DirectX12 features to python.
''',
      setup_requires=['wheel'],
      packages=['pydx12'],
      package_data={'pydx12': ['api.pyi']},
      ext_modules=[module],
      test_suite='tests')
